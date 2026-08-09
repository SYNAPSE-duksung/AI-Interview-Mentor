import streamlit as st
import os
from models.gemini_interviewer import generate_questions
from audio.stt import transcribe_audio

# 페이지 기본 설정
st.set_page_config(page_title="AI 면접 시스템", page_icon="👔", layout="wide")

with st.sidebar:
    api_key = st.text_input("🔑 Gemini API Key", type="password")

# --- 1. Session State 초기화 (상태 및 기억 관리) ---
if 'step' not in st.session_state: st.session_state.step = "입력화면"
if 'turn' not in st.session_state: st.session_state.turn = 1
if 'history' not in st.session_state: st.session_state.history = [] # 주고받은 Q&A 기록 저장
if 'current_question' not in st.session_state: st.session_state.current_question = ""


# --- 2. 입력 화면 ---
if st.session_state.step == "입력화면":
    st.title("💼 AI 모의 면접 설정")
    st.write("지원하실 회사와 직무를 입력해 주세요.")
    
    company_input = st.text_input("지원 회사 (예: 네이버)")
    job_input = st.text_input("지원 직무 (예: 데이터 분석가)")
    
    if st.button("🚀 면접 시작하기", type="primary"):
        if not api_key: st.error("왼쪽 사이드바에 API 키를 입력해주세요.")
        elif company_input and job_input:
            with st.spinner("1턴 질문(인성/조직적응력)을 생성하고 있습니다..."):
                st.session_state.current_question = generate_questions(company_input, job_input, "personality", api_key)
                st.session_state.company = company_input
                st.session_state.job = job_input
                # 변수 초기화
                st.session_state.turn = 1
                st.session_state.history = [] 
                st.session_state.step = "면접화면"
                st.rerun()
        else: 
            st.warning("정보를 모두 입력하세요.")


# --- 3. 면접 화면 (1~3턴 흐름 제어) ---
elif st.session_state.step == "면접화면":
    st.title(f"🎙️ {st.session_state.company} - {st.session_state.job} 면접")
    
    #현재 몇 턴인지 표시
    turn_titles = {1: "1턴: 인성 및 조직적응력 질문", 2: "2턴: 직무 역량 질문", 3: "3턴: 심층 꼬리질문"}
    st.subheader(f"[{turn_titles[st.session_state.turn]}]")
    
    st.info(f"**면접관:** {st.session_state.current_question}")
    
    #턴마다 오디오 키값을 다르게 주어 녹음기가 매번 초기화되도록 함
    audio_value = st.audio_input("답변 녹음하기", key=f"audio_{st.session_state.turn}")
    
    if audio_value is not None:
        with st.spinner("STT 변환 중..."):
            with open("temp_answer.wav", "wb") as f:
                f.write(audio_value.getbuffer())
            stt_text = transcribe_audio("temp_answer.wav")
            
            st.success("답변이 정상적으로 인식되었습니다!")
            st.write(f"📝 **내 답변:** {stt_text}")
            
            # 다음 단계로 넘어가기 버튼 (3턴일 때는 결과 확인 버튼으로 텍스트 변경)
            button_label = "다음 질문으로 넘어가기 ➡️" if st.session_state.turn < 3 else "📊 종합 결과 확인하기"
            
            if st.button(button_label):
                # 1. 히스토리에 현재 턴의 질문과 답변 저장
                st.session_state.history.append({
                    "turn": st.session_state.turn,
                    "question": st.session_state.current_question,
                    "answer": stt_text
                })
                
                # 2. 턴에 따른 분기 처리 (라우팅)
                if st.session_state.turn == 1:
                    with st.spinner("2턴 질문(직무 역량)을 생성하고 있습니다..."):
                        st.session_state.current_question = generate_questions(st.session_state.company, st.session_state.job, "job", api_key)
                        st.session_state.turn = 2
                        st.rerun()
                        
                elif st.session_state.turn == 2:
                    with st.spinner("3턴 질문(꼬리질문)을 준비하고 있습니다..."):
                        # 2팀 평가 모델이 아직 없으므로, 임시 더미(Mock) 꼬리질문 배정
                        st.session_state.current_question = "방금 말씀하신 답변에서 구체적으로 본인은 어떤 역할을 수행하셨는지, 그리고 그 결과는 어떠했는지 조금 더 자세히 설명해 주시겠어요?"
                        st.session_state.turn = 3
                        st.rerun()
                        
                elif st.session_state.turn == 3:
                    # 3턴이 끝나면 결과 화면으로 이동
                    st.session_state.step = "결과화면"
                    st.rerun()


# --- 4. 결과 화면 (종합 피드백 대시보드) ---
elif st.session_state.step == "결과화면":
    st.title("📊 AI 면접 종합 결과 리포트")
    
    st.write("3턴의 면접이 모두 종료되었습니다. 아래에서 피드백을 확인하세요.")
    
    # 2팀 평가 모델 연동 전, 프론트엔드 구성을 위한 임시(Mock) 피드백 데이터
    dummy_result = {
        "score": 85,
        "feedback_logic": "우수 (두괄식으로 결론을 먼저 제시하여 논리구조가 명확합니다.)",
        "feedback_keyword": "보통 (직무 관련 전문 용어 사용이 다소 부족합니다.)",
        "feedback_length": "적절 (답변 분량이 300~500자로 아주 적당합니다.)",
        "improved_answer": "저는 해당 직무에서 [핵심 성과]를 달성한 경험이 있습니다. 구체적인 사례를 말씀드리자면..."
    }
    
    # 성적표 UI
    st.subheader("🏆 총점")
    st.metric(label="AI 면접관의 종합 평가 점수", value=f"{dummy_result['score']}점")
    
    st.subheader("🔍 항목별 상세 피드백")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**논리구조**\n\n{dummy_result['feedback_logic']}")
    with col2:
        st.warning(f"**키워드 활용**\n\n{dummy_result['feedback_keyword']}")
    with col3:
        st.success(f"**분량**\n\n{dummy_result['feedback_length']}")
        
    st.subheader("✨ 이렇게 답변했다면 더 좋았을 거예요 (모범 답변)")
    st.code(dummy_result['improved_answer'], language="text")
    
    st.divider()
    
    # Q&A 히스토리 아코디언 UI로 표시
    st.subheader("📝 나의 면접 기록 (Q&A 히스토리)")
    for item in st.session_state.history:
        with st.expander(f"📌 {item['turn']}턴 질문 및 답변 내용 보기"):
            st.write(f"**🗣️ 면접관:** {item['question']}")
            st.write(f"**👤 내 답변:** {item['answer']}")
            
    # 다시하기 버튼
    st.write("")
    if st.button("🔄 처음으로 돌아가기 (다시하기)"):
        st.session_state.step = "입력화면"
        st.session_state.turn = 1
        st.session_state.history = []
        st.rerun()