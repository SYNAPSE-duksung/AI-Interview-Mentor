"""
[B파트] STT (Speech-to-Text) 모듈

Whisper 모델로 음성 파일을 텍스트로 변환합니다.

주의: whisper_model 로드는 이 모듈이 import되는 순간 실행됩니다.
      (원본 노트북과 동일한 동작 - 최초 1회 30초~1분 소요)
"""
import os
import whisper

print("Whisper 모델 메모리에 로드 중... (최초 1회 약 30초~1분 소요)")
whisper_model = whisper.load_model("small")
print("✅ Whisper 모델 로드 완료!")


def transcribe_audio(audio_path: str) -> str:
    """
    음성 파일 경로(audio_path)를 입력받아 Whisper 모델로 텍스트로 변환하고
    순수 문자열(str)을 반환하는 함수.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"❌ 오디오 파일을 찾을 수 없습니다: {audio_path}")

    result = whisper_model.transcribe(audio_path, language="ko", fp16=False)
    return result["text"].strip()