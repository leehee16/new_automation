#src/image_processor.py

# 이미지 경로랑 받아서 하루에 하나의 파일로 랜더링해야함.
# 저장방식 최적화. 이전에는 20250901-20250907 같이 폴더를 만들고 일주일마다 여기에 파일을 쌓았음. 사람별 폴더이름도 그냥 폴더명으로만. 
#프로세서가 미리 렌더링하지말고, 분류후에 렌더링하는건 어때? 여러 flag를 받아서 동적으로 생성할 수 있도록. 근데 지금은 일단 타켓함수만 작성

from pathlib import Path

root = Path(__file__).parent.parent
test_path = root / 'src' / 'test' / 'image'

# 타겟 path에서 폴더명 받아서 리스트로
folder_names = [item.name for item in test_path.iterdir() if item.is_dir()]
# jpg 이미지 개수 세기
image_counts = {}
for folder_name in folder_names:
    folder_path = test_path / folder_name  # Path 객체로 변환
    image_counts[folder_name] = len(list(folder_path.glob('*.jpg')))

print(image_counts)

# 총 이미지 개수
print(f"전체: {sum(image_counts.values())}개")