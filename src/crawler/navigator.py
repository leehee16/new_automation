# src/crawler/services/navigation.py
from playwright.async_api import Page

class Navigator:
    def __init__(self, page: Page):
        self.page = page

    async def open_sidebar(self):
        await self.page.click('.bermuda-menu')
        
    async def click_police_button(self):
        await self.page.click('#aside-police')
