from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

class Login:
    def __init__(self, page: Page, url: str, username: str, password: str):
        self.page = page
        self.url = url
        self.username = username
        self.password = password

    async def login(self):
        await self.page.goto(self.url)
        logger.info("로그인 시작")
        if await self.page.query_selector('.fa-bars'):
            logger.info("이미 로그인됨")
            return

        await self.page.fill('input[placeholder="username"]', self.username)
        await self.page.fill('input[placeholder="password"]', self.password)
        await self.page.click('input[type="submit"][value="LogIn"]')
        await self.page.wait_for_selector('.fa-bars', timeout=30000)
        logger.info("로그인 성공")
