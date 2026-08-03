import streamlit as st
import os
from models.gemini_interviewer import generate_questions
from audio.stt import transcribe_audio

st.set_page_config(page_title="AI 면접 시스템", page_icon="👔")

with st.sidebar:
    api_key = st.text_input("🔑 Gemini API Key", type="password")

if 'step' not in st.session_state: st.session_state.step = "입력화면"
if 'current_question' not in st.session_state: st.session_state.current_question = ""

if st.session_state.step == "입력화면":
    st.title("💼 면접 설정")
    company_input = st.text_input("지원 회사 (예: 네이버)")
    job_input = st.text_input("지원 직무 (예: 데이터 분석가)")
    
    if st.button("면접 시작하기"):
        if not api_key: st.error("API 키를 입력해주세요.")
        elif company_input and job_input:
            with st.spinner("질문 생성 중..."):
                st.session_state.current_question = generate_questions(company_input, job_input, "personality", api_key)
                st.session_state.company = company_input
                st.session_state.job = job_input
                st.session_state.step = "면접화면"
                st.rerun()
        else: st.warning("정보를 입력하세요.")

elif st.session_state.step == "면접화면":
    st.title(f"🎙️ {st.session_state.company} - {st.session_state.job} 면접")
    st.info(f"**면접관:** {st.session_state.current_question}")
    
    audio_value = st.audio_input("답변 녹음하기")
    
    if audio_value is not None:
        with st.spinner("STT 변환 중..."):
            with open("temp_answer.wav", "wb") as f:
                f.write(audio_value.getbuffer())
            stt_text = transcribe_audio("temp_answer.wav")
            st.success("변환 완료!")
            st.write(f"📝 **내 답변:** {stt_text}")
    
    if st.button("처음으로"):
        st.session_state.step = "입력화면"
        st.rerun()



