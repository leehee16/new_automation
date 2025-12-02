from playwright.async_api import Page
from typing import List

"""
팝업 처리를 담당하는 모듈
"""
import logging

logger = logging.getLogger(__name__)


class PopupHandler:
    """팝업 관련 처리를 담당하는 클래스"""
    
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

    
    def __init__(self, page: Page):
        """
        Args:
            page: Playwright page 객체
        """
        self.page = page
    
    async def get_sorted_close_buttons(self) -> List[str]:
        found = []

        # 모든 패턴의 버튼들을 직접 조사
        for popup in self.POPUP_PATTERNS:
            for btn_selector in popup["selectors"]:
                btn_element = await self.page.query_selector(btn_selector)
                if btn_element and await btn_element.is_visible():
                    # 버튼의 z-index 추출
                    z = await self.page.evaluate(
                        '(el) => getComputedStyle(el).zIndex',
                        btn_element
                    )
                    try:
                        z = int(z)
                    except:
                        z = 0
                    
                    found.append((z, btn_selector))

        if not found:
            return []

        # z-index 높은 순으로 정렬
        found.sort(key=lambda x: x[0], reverse=True)

        # 셀렉터만 추출
        return [selector for _, selector in found]


    async def close_all_popups(self) -> int:
        """
        화면의 모든 팝업을 순차적으로 닫음
        
        Returns:
            닫은 팝업의 개수
        """
        closed_count = 0
        
        while True:
            # 현재 보이는 닫기 버튼들 조사
            close_buttons = await self.get_sorted_close_buttons()
            
            if not close_buttons:
                # 더 이상 닫을 팝업이 없음
                break
            
            # 최상단 팝업의 첫 번째 버튼 클릭
            first_button = close_buttons[0]
            
            try:
                button_element = await self.page.query_selector(first_button)
                if button_element:
                    await button_element.click()
                    closed_count += 1
                    logger.info(f"팝업 닫기 성공: {first_button}")
                    
                    # 팝업이 사라질 시간 대기
                    await self.page.wait_for_timeout(500)
                else:
                    # 버튼을 찾을 수 없으면 무한 루프 방지
                    break
                    
            except Exception as e:
                logger.warning(f"팝업 닫기 실패: {first_button}, 에러: {e}")
                break
        
        logger.info(f"총 {closed_count}개의 팝업을 닫았습니다.")
        return closed_count