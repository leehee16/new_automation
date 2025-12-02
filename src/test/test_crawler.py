# src/test/test_crawler.py
import os
import logging
from dotenv import load_dotenv
load_dotenv()

import pytest
from playwright.async_api import async_playwright
from crawler.explr.login import AuthService
from crawler.explr.navigator import Navigation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.fixture
async def browser_context():
    """브라우저 컨텍스트 제공"""
    url = os.getenv("WEB_SITE_URL")
    username = os.getenv("ID")
    password = os.getenv("PW")
    
    assert url and username and password, "환경 변수 설정 필요"
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,  # 브라우저 보이기
            slow_mo=500,     # 천천히 실행 (500ms 지연)
        )
        page = await browser.new_page()
        
        yield {
            "browser": browser,
            "page": page,
            "url": url,
            "username": username,
            "password": password
        }
        
        await browser.close()

@pytest.mark.asyncio
async def test_complete_flow(browser_context):
    """전체 플로우: 로그인 → 팝업 제거 → Police 메뉴"""
    page = browser_context["page"]
    
    # 1. 로그인
    input("\n[1/4] 엔터를 누르면 로그인을 시작합니다...")
    print("로그인 중...")
    auth = AuthService(
        page,
        browser_context["url"],
        browser_context["username"],
        browser_context["password"]
    )
    await auth.login()
    print("✓ 로그인 완료")
    
    # 2. 팝업 
    input("\n[2/4] 엔터를 누르면 팝업종류를 반환합니다.")
    print("팝업 종류 확인...")
    navigation = Navigation(page)
    popup_list = await navigation.popup_handler.get_popup_types()
    print(f"✓ 팝업 종류: {popup_list}")

    
    # 3. Police 메뉴 접근
    input("\n[3/4] 엔터를 누르면 Police 메뉴 접근을 시작합니다...")
    print("Police 메뉴 접근 중...")
    success = await navigation.navigate_to_police_menu()
    assert success, "Police 메뉴 접근 실패"
    print("✓ Police 메뉴 접근 완료")
    
    # 4. 테이블 확인
    table_row = await page.query_selector('.police-table-row')
    assert table_row is not None, "Police 테이블을 찾을 수 없습니다"
    
    # 테이블 개수 확인
    table_count = await page.evaluate("""
        () => document.querySelectorAll('.police-table-row').length
    """)
    print(f"✓ 테이블 행 수: {table_count}")
    
    # 브라우저 종료
    input("\n[4/4] 엔터를 누르면 브라우저가 종료됩니다...")