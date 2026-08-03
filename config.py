"""
API 키 불러오기 & 클라이언트 초기화

원본(Colab)에서는 google.colab.userdata로 키를 불러왔지만,
로컬/VS Code 환경에는 google.colab 모듈이 없기 때문에
환경변수 방식으로 바꿨습니다.

사용법:
  1) 프로젝트 루트에 .env 파일 생성 (git에는 올리지 마세요! .gitignore에 추가)
     GEMINI_API_KEY=여기에_키_입력
  2) pip install python-dotenv
"""
import os
from google import genai

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 미설치 시 시스템 환경변수만 사용

API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY is None:
    raise ValueError(
        "GEMINI_API_KEY가 설정되지 않았습니다. "
        ".env 파일 또는 환경변수로 설정해주세요."
    )

client = genai.Client(api_key=API_KEY)