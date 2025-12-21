# src/main.py
import os
import logging
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

from scraper import login, close_all_popups, navigate_to_police_page, wait_for_table_loaded, get_filtered_data
from downloader import process_all_captures

load_dotenv()

# 로깅 설정
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f'logs/app_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """메인 실행 함수"""
    # 환경변수 검증
    url = os.getenv("WEB_SITE_URL")
    username = os.getenv("ID")
    password = os.getenv("PW")
    
    if not all([url, username, password]):
        logger.error("환경변수가 제대로 설정되지 않았습니다.")
        return
    
    # 브라우저 실행
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=500,
        )
        
        try:
            page = await browser.new_page()
            
            # 1. 로그인
            if not await login(page, url, username, password):
                logger.error("로그인에 실패하여 프로그램을 종료합니다.")
                return
            
            # 2. 팝업 제거
            await close_all_popups(page)
            
            # 3. Police 페이지로 이동
            if not await navigate_to_police_page(page):
                logger.error("Police 페이지 이동 실패")
                return
            
            # 4. 테이블 로딩 대기
            if not await wait_for_table_loaded(page):
                logger.error("테이블 로딩 실패")
                return
            
            # 5. 데이터 추출 및 필터링
            ## TODO : male조건 추가하기
            filtered_data = await get_filtered_data(page)
            logger.info(f"최종 필터링된 데이터: {len(filtered_data)}건")
            
            # 6. 캡처 페이지 다운로드
            ## TODO : 다운로더 날짜 인식 로직 고도화. 예를들어 날짜가 화요일 이렇게 해서 최종적인 날짜가 다 없으면 다음 페이지로가서 화면 확인해야함.
            stats = await process_all_captures(page, filtered_data, limit=10)
            
            logger.info(f"=== 최종 결과 ===")
            logger.info(f"처리 대상: {len(filtered_data)}건")
            logger.info(f"성공: {stats['success']}건")
            logger.info(f"실패: {stats['failed']}건")
            # 7. 캡처한 유저 관리하는 로직.
            ## TODO : 이거는 sqlite로 데이터를 저장하는게 나을듯.
            # 8. 머신러닝을 위한 로직 : 나이 예측, 클래스파이어 모듈. <- 프리트레인으로
            # 9. 캡처한 데이터 프로세싱하는 로직. 알맞게 저장하는 용도.
            # 10. 대시보드 로직.
            # 11. 분류기를 위한 모듈
            # 12.config yml로 관리

        except Exception as e:
            logger.error(f"실행 중 오류 발생: {e}")
            
        finally:
            await asyncio.to_thread(input, "종료하려면 Enter를 누르세요... ")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())