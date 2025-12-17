# 필터 적용 + 목록(URL) 추출
from datetime import datetime, timedelta, timezone
from playwright.async_api import Page
import re
from datetime import datetime, timezone, timedelta

class Tubular:
    def __init__(self, page:Page):
        self.page = page

    async def filtered(self):
        await self.page.wait_for_selector('.police-table-row', state='visible')

        table_data = await self.page.evaluate("""
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

        # 한국 시간 기준 (UTC+9)
        KST = timezone(timedelta(hours=9))
        now = datetime.now(timezone.utc).astimezone(KST)

        # 이번 주 월요일 (00:00:00)
        this_week_monday = now - timedelta(days=now.weekday())
        this_week_monday = this_week_monday.replace(hour=0, minute=0, second=0, microsecond=0)

        # 지난 주 월요일 (00:00:00)
        start_of_week = this_week_monday - timedelta(days=7)

        # 날짜 파싱 함수
        def parse_last_login(raw):
            if not raw:
                return None
            raw = raw.replace("오전", "AM").replace("오후", "PM")
            raw = re.sub(r"\s+", " ", raw)
            try:
                return datetime.strptime(raw, "%Y. %m. %d. %p %I:%M:%S").replace(tzinfo=KST)
            except:
                return None

        filtered_data = []

        for row in table_data:
            if row["id"].lower() == "id":
                continue

            parsed_date = parse_last_login(row["lastLogin"])
            if not parsed_date:
                continue

            if row["country"] == "PH":
                continue

            if parsed_date < start_of_week:
                continue

            # lastLogin을 datetime 객체로 교체
            row["lastLogin"] = parsed_date
            filtered_data.append(row)

        return filtered_data
