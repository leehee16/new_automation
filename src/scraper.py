# src/scraper.py
import logging
import re
from datetime import datetime, timezone, timedelta
from playwright.async_api import Page
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

# 한국 시간대
KST = timezone(timedelta(hours=9))

# 팝업 패턴
POPUP_PATTERNS = [
    {
        "type": "sweetalert2",
        "selectors": [
            "button.swal2-confirm",
            "button.swal2-cancel",
            "button.swal2-close",
        ]
    },
    {
        "type": "guide",
        "selectors": [
            ".guide-modal-close",
        ]
    },
    {
        "type": "bootstrap_modal",
        "selectors": [
            ".modal .btn-close",
            ".modal .close",
            '[data-dismiss="modal"]',
            "button:has-text('닫기')",
            "button:has-text('Close')",
        ]
    },
]


# ============================================================================
# 유틸리티 함수
# ============================================================================

def parse_last_login(raw: str) -> Optional[datetime]:
    """
    LastLogin 문자열을 datetime 객체로 파싱
    
    Args:
        raw: 날짜 문자열 (여러 형식 지원)
    
    Returns:
        파싱된 datetime 객체 (KST) 또는 None
    """
    if not raw:
        return None
    
    # 지원하는 날짜 형식들
    formats = [
        "%Y. %m. %d. %p %I:%M:%S",     # 2024. 12. 17. 오후 3:45:30
        "%m/%d/%Y, %I:%M:%S %p",       # 12/17/2025, 1:08:03 PM
    ]
    
    try:
        # 오전/오후를 AM/PM으로 변환
        processed = raw.replace("오전", "AM").replace("오후", "PM")
        processed = re.sub(r"\s+", " ", processed.strip())
        
        # 각 형식으로 시도
        for fmt in formats:
            try:
                parsed = datetime.strptime(processed, fmt)
                return parsed.replace(tzinfo=KST)
            except ValueError:
                continue
        
        # 모든 형식 실패
        logger.warning(f"날짜 파싱 실패 (지원하지 않는 형식): {raw}")
        return None
        
    except Exception as e:
        logger.warning(f"날짜 파싱 실패: {raw}, 에러: {e}")
        return None


# ============================================================================
# 팝업 처리
# ============================================================================

async def get_element_z_index(page: Page, element) -> int:
    """요소의 z-index를 가져옴"""
    try:
        z = await page.evaluate('(el) => getComputedStyle(el).zIndex', element)
        return int(z) if z != 'auto' else 0
    except (ValueError, TypeError):
        return 0


async def get_sorted_close_buttons(page: Page) -> List[str]:
    """화면의 모든 닫기 버튼을 z-index 순으로 정렬하여 반환"""
    found: List[Tuple[int, str]] = []

    for popup in POPUP_PATTERNS:
        for btn_selector in popup["selectors"]:
            try:
                btn_element = await page.query_selector(btn_selector)
                if btn_element and await btn_element.is_visible():
                    z_index = await get_element_z_index(page, btn_element)
                    found.append((z_index, btn_selector))
            except Exception as e:
                logger.debug(f"버튼 조회 중 에러: {btn_selector}, {e}")
                continue

    if not found:
        return []

    found.sort(key=lambda x: x[0], reverse=True)
    return [selector for _, selector in found]


async def close_all_popups(page: Page, max_attempts: int = 10) -> int:
    """
    화면의 모든 팝업을 순차적으로 닫음
    
    Args:
        page: Playwright Page 객체
        max_attempts: 최대 시도 횟수 (무한루프 방지)
    
    Returns:
        닫은 팝업의 개수
    """
    closed_count = 0
    
    for attempt in range(max_attempts):
        close_buttons = await get_sorted_close_buttons(page)
        
        if not close_buttons:
            logger.info("더 이상 닫을 팝업이 없습니다.")
            break
        
        first_button = close_buttons[0]
        
        try:
            button_element = await page.query_selector(first_button)
            if not button_element:
                logger.warning(f"버튼을 찾을 수 없음: {first_button}")
                break
            
            await button_element.click()
            closed_count += 1
            logger.info(f"팝업 닫기 성공 ({closed_count}): {first_button}")
            await page.wait_for_timeout(500)
                
        except Exception as e:
            logger.warning(f"팝업 닫기 실패: {first_button}, 에러: {e}")
            break
    
    logger.info(f"총 {closed_count}개의 팝업을 닫았습니다.")
    return closed_count


# ============================================================================
# 로그인 및 네비게이션
# ============================================================================

async def login(page: Page, url: str, username: str, password: str) -> bool:
    """
    로그인 수행
    
    Returns:
        로그인 성공 여부
    """
    try:
        await page.goto(url)
        await page.fill('input[placeholder="username"]', username)
        await page.fill('input[placeholder="password"]', password)
        await page.click('input[type="submit"][value="LogIn"]')
        
        await page.wait_for_load_state("networkidle")
        logger.info("로그인 성공")
        return True
        
    except Exception as e:
        logger.error(f"로그인 실패: {e}")
        return False


async def navigate_to_police_page(page: Page) -> bool:
    """
    Police 페이지로 이동
    
    Returns:
        이동 성공 여부
    """
    try:
        await page.click('.bermuda-menu')
        await page.wait_for_timeout(300)
        
        await page.click('#aside-police')
        await page.wait_for_load_state("networkidle")
        
        logger.info("Police 페이지로 이동 성공")
        return True
        
    except Exception as e:
        logger.error(f"Police 페이지 이동 실패: {e}")
        return False


async def wait_for_table_loaded(page: Page, min_rows: int = 10, max_wait: int = 120) -> bool:
    """
    테이블 로딩 완료 대기
    
    Args:
        page: Page 객체
        min_rows: 최소 행 개수
        max_wait: 최대 대기 시간(초)
    
    Returns:
        로딩 성공 여부
    """
    logger.info(f"테이블 로딩 대기 시작 ({min_rows}행 인식시)")
    
    for i in range(max_wait):
        row_count = await page.locator('.police-table-row').count()
        
        if row_count >= min_rows:
            logger.info(f"{i}초 로딩. 테이블 로딩 완료: {row_count}개 행")
            return True
        
        await page.wait_for_timeout(1000)
    
    logger.warning("⚠️ 테이블 로딩 타임아웃")
    return False


# ============================================================================
# 데이터 추출 및 필터링
# ============================================================================

async def get_table_data(page: Page) -> List[Dict[str, Any]]:
    """
    테이블에서 모든 데이터 추출
    
    Returns:
        테이블 행 데이터 리스트
    """
    try:
        await page.wait_for_selector('.police-table-row', state='visible')
        
        table_data = await page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll('.police-table-row'));
            return rows.map(row => ({
                id: row.querySelector('.police-table-no')?.textContent?.trim() || '',
                type: row.querySelector('.police-table-type')?.textContent?.trim() || '',
                fbUid: row.querySelector('.police-table-uid')?.textContent?.trim() || '',
                nick: row.querySelector('.police-table-nick')?.textContent?.trim() || '',
                country: row.querySelector('.police-table-country')?.textContent?.trim() || '',
                gender: row.querySelector('.police-table-gender')?.textContent?.trim() || '',
                lastLogin: row.querySelector('.police-table-login')?.textContent?.trim() || '',
                captureLink: row.querySelector('.police-table-clink a')?.href || null
            }));
        }
        """)
        
        logger.info(f"테이블 데이터 추출 완료: {len(table_data)}개 행")
        return table_data
        
    except Exception as e:
        logger.error(f"테이블 데이터 추출 실패: {e}")
        return []


async def get_filtered_data(page: Page) -> List[Dict[str, Any]]:
    """
    필터링된 데이터 반환
    - 지난 주 월요일 이후 로그인
    - 필리핀(PH) 제외
    - 헤더 행 제외
    
    Returns:
        필터링된 데이터 리스트
    """
    table_data = await get_table_data(page)
    
    if not table_data:
        return []
    
    # 현재 시간 (KST)
    now = datetime.now(timezone.utc).astimezone(KST)
    
    # 이번 주 월요일 00:00:00
    this_week_monday = now - timedelta(days=now.weekday())
    this_week_monday = this_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 지난 주 월요일 00:00:00
    start_of_week = this_week_monday - timedelta(days=7)
    
    logger.info(f"필터링 기준일: {start_of_week.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    
    filtered_data = []
    
    for row in table_data:
        # 헤더 행 제외
        if row["id"].lower() == "id":
            continue
        
        # 날짜 파싱
        parsed_date = parse_last_login(row["lastLogin"])
        if not parsed_date:
            continue
        
        # 필리핀 제외
        if row["country"] == "PH":
            continue
        
        # 지난 주 월요일 이전 제외
        if parsed_date < start_of_week:
            continue
        
        # lastLogin을 datetime 객체로 교체
        row["lastLogin"] = parsed_date
        filtered_data.append(row)
    
    logger.info(f"필터링 완료: {len(filtered_data)}개 행")
    return filtered_data