# src/downloader.py
import os
import re
import logging
import aiohttp
from datetime import datetime
from playwright.async_api import Page
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# 유틸리티 함수
# ============================================================================

def sanitize_folder_name(name: str) -> str:
    """폴더명에서 특수문자 제거"""
    return re.sub(r'[^a-zA-Z0-9가-힣_]', '', name)


def parse_date_folder(date_id: str) -> str:
    """날짜 ID를 폴더명 형식으로 변환"""
    try:
        return datetime.strptime(date_id, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return date_id


# ============================================================================
# 이미지 다운로드
# ============================================================================

async def download_image(session: aiohttp.ClientSession, src: str, file_path: str) -> bool:
    """
    이미지 다운로드
    
    Returns:
        성공 여부
    """
    try:
        async with session.get(src) as res:
            if res.status != 200:
                logger.warning(f"다운로드 실패 (HTTP {res.status}): {src}")
                return False
            
            content = await res.read()
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.debug(f"저장 완료: {file_path}")
            return True
            
    except Exception as e:
        logger.error(f"이미지 다운로드 에러: {src}, {e}")
        return False


async def save_all_images_flat(page: Page, folder_name: str, base_dir: str = "src/test/image") -> int:
    """
    페이지의 모든 이미지를 한 폴더에 저장
    
    Returns:
        저장된 이미지 개수
    """
    save_dir = Path(base_dir) / folder_name
    save_dir.mkdir(parents=True, exist_ok=True)

    imgs = page.locator("img")
    count = await imgs.count()
    logger.info(f"전체 이미지: {count}장")

    saved_count = 0
    async with aiohttp.ClientSession() as session:
        for i in range(count):
            src = await imgs.nth(i).get_attribute("src")
            if not src:
                continue

            file_path = save_dir / f"img_{i+1}.jpg"
            
            if await download_image(session, src, str(file_path)):
                saved_count += 1

    logger.info(f"저장 완료: {saved_count}/{count}장")
    return saved_count


async def save_images_by_date_section(
    page: Page, 
    folder_name: str, 
    base_dir: str = "src/test/image"
) -> int:
    """
    날짜 섹션별로 이미지 저장
    
    Returns:
        저장된 이미지 개수
    """
    sections = page.locator(".date-photo-data")
    section_count = await sections.count()
    
    logger.info(f"날짜 섹션: {section_count}개")
    
    if section_count == 0:
        return 0

    total_saved = 0
    async with aiohttp.ClientSession() as session:
        for i in range(section_count):
            section = sections.nth(i)
            date_id = await section.get_attribute("id")
            
            if not date_id:
                continue
            
            date_folder = parse_date_folder(date_id)
            
            # 이미지 찾기
            imgs = section.locator("img")
            img_count = await imgs.count()
            
            if img_count == 0:
                logger.debug(f"{date_folder}: 이미지 없음, 스킵")
                continue
            
            logger.info(f"{date_folder}: {img_count}장")
            
            save_dir = Path(base_dir) / folder_name / date_folder
            save_dir.mkdir(parents=True, exist_ok=True)

            # 다운로드
            for n in range(img_count):
                src = await imgs.nth(n).get_attribute("src")
                if not src:
                    continue

                file_path = save_dir / f"img_{n+1}.jpg"
                
                if await download_image(session, src, str(file_path)):
                    total_saved += 1

    return total_saved


# ============================================================================
# 캡처 페이지 처리
# ============================================================================

async def process_user_capture(page: Page, row: Dict, base_dir: str = "src/test/image") -> bool:
    """
    사용자 캡처 페이지 처리 및 이미지 저장
    
    Args:
        page: 현재 페이지 (목록 페이지)
        row: filtered_data의 한 행
        base_dir: 이미지 저장 기본 경로
    
    Returns:
        처리 성공 여부
    """
    fb_uid = row["fbUid"]
    nick = row["nick"]
    country = row["country"]
    gender = row["gender"]

    folder_name = sanitize_folder_name(f"{fb_uid}_{nick}_{country}_{gender}")
    
    logger.info(f"=== [{fb_uid}] {nick} 캡처 시작 ===")

    try:
        # 새 탭 열기
        async with page.context.expect_page() as popup:
            await page.click(f"a[href*='{fb_uid}']")

        new_page = await popup.value
        await new_page.wait_for_load_state("networkidle")

        # 날짜 섹션 확인
        sections = new_page.locator(".date-photo-data")
        section_count = await sections.count()

        if section_count == 0:
            # 날짜 정보 없음 - 전체 저장
            logger.info("날짜 정보 없음 → 전체 이미지 저장")
            saved = await save_all_images_flat(new_page, folder_name, base_dir)
        else:
            # 날짜별 저장
            saved = await save_images_by_date_section(new_page, folder_name, base_dir)

        await new_page.close()
        
        logger.info(f"=== [{fb_uid}] 완료: {saved}장 저장 ===")
        return True

    except Exception as e:
        logger.error(f"[{fb_uid}] 처리 실패: {e}")
        return False


async def process_all_captures(
    page: Page, 
    filtered_data: list, 
    batch_size: int = 3,
    limit: Optional[int] = None
) -> Dict[str, int]:
    """
    모든 사용자 캡처 처리
    
    Args:
        page: Page 객체
        filtered_data: 처리할 데이터 리스트
        batch_size: 한 번에 처리할 개수 (기본값: 10)
        limit: 처리할 최대 개수 (None이면 전체 처리, 테스트용)
    
    Returns:
        {'success': 성공 수, 'failed': 실패 수}
    """
    stats = {'success': 0, 'failed': 0}
    
    # limit 적용
    data_to_process = filtered_data[:limit] if limit else filtered_data
    total = len(data_to_process)
    
    logger.info(f"총 {total}건을 {batch_size}개씩 배치 처리 시작" + 
                (f" (전체 {len(filtered_data)}건 중 {limit}건만 처리)" if limit else ""))
    
    for idx, row in enumerate(data_to_process, 1):
        logger.info(f"진행: {idx}/{total}")
        
        if await process_user_capture(page, row):
            stats['success'] += 1
        else:
            stats['failed'] += 1
        
        # 배치 단위로 완료될 때마다 로그
        if idx % batch_size == 0:
            logger.info(f"배치 완료: {idx}/{total} - 성공: {stats['success']}, 실패: {stats['failed']}")
    
    logger.info(f"전체 완료 - 성공: {stats['success']}, 실패: {stats['failed']}")
    return stats