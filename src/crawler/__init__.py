from .login import Login
from .popup_handler import PopupHandler
from .navigator import Navigator
from .tubular import Tubular

import os
from dotenv import load_dotenv
load_dotenv()


class Crawler:
    def __init__(self, page):
        self.page = page
        # .env 값 로드
        self.url = os.getenv("WEB_SITE_URL","")
        self.id = os.getenv("ID","")
        self.pw = os.getenv("PW","")
        # 하위 모듈 인스턴스
        self.login = Login(page, self.url, self.id, self.pw)
        self.popup = PopupHandler(page)
        self.nav = Navigator(page)
        self.filter = Tubular(page)