import whisper
import streamlit as st

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("small")

def transcribe_audio(audio_file_path: str) -> str:
    model = load_whisper_model()
    result = model.transcribe(audio_file_path, language="ko", fp16=False)
    return result["text"].strip()
