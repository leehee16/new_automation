-- 1. 스크래핑 실행 로그
scraping_runs:
- id (PK)
- run_date (datetime)
- total_rows (int)           # 테이블 전체 행
- filtered_count (int)       # 필터링 후
- success_count (int)        # 다운로드 성공
- failed_count (int)         # 다운로드 실패
- total_images (int)         # 다운로드한 이미지 수
- duration_seconds (float)
- created_at

-- 2. 유저 정보
users:
- fb_uid (PK)
- nick
- country
- gender
- last_login
- first_seen
- created_at

-- 3. 캡처 기록
captures:
- id (PK)
- fb_uid (FK)
- capture_date (datetime)
- image_count (int)
- folder_path
- created_at

-- 4. 이미지
images:
- id (PK)
- capture_id (FK)
- image_path
- date_taken (nullable)
- created_at

-- 5. 분류 결과 (통합)
classifications:
- id (PK)
- image_id (FK)
- source ('manual' or 'ml')
- category
- risk_level (int)
- confidence (float, nullable)
- notes (text, nullable)
- classified_at