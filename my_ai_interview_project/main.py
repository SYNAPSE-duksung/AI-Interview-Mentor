import streamlit as st
import os
from models.gemini_interviewer import generate_questions
from audio.stt import transcribe_audio
from evaluation.evaluator import evaluate_answer

# 페이지 기본 설정
st.set_page_config(page_title="AI 면접 시스템", page_icon="👔", layout="wide")

with st.sidebar:
    api_key = st.text_input("🔑 Gemini API Key", type="password")
    st.caption(
        "이 키는 질문 생성(Gemini)에만 사용됩니다. "
        "답변 평가(EXAONE)는 별도 API 키가 필요 없습니다."
    )

# --- 1. Session State 초기화 (상태 및 기억 관리) ---
if 'step' not in st.session_state: st.session_state.step = "입력화면"
if 'turn' not in st.session_state: st.session_state.turn = 1
if 'history' not in st.session_state: st.session_state.history = []  # 주고받은 Q&A + 평가 기록 저장
if 'current_question' not in st.session_state: st.session_state.current_question = ""


# --- 2. 입력 화면 ---
if st.session_state.step == "입력화면":
    st.title("💼 AI 모의 면접 설정")
    st.write("지원하실 회사와 직무를 입력해 주세요.")

    company_input = st.text_input("지원 회사 (예: 네이버)")
    job_input = st.text_input("지원 직무 (예: 데이터 분석가)")

    if st.button("🚀 면접 시작하기", type="primary"):
        if not api_key:
            st.error("왼쪽 사이드바에 API 키를 입력해주세요.")
        elif company_input and job_input:
            with st.spinner("1턴 질문(인성/조직적응력)을 생성하고 있습니다..."):
                st.session_state.current_question = generate_questions(company_input, job_input, "personality", api_key)
                st.session_state.company = company_input
                st.session_state.job = job_input
                st.session_state.turn = 1
                st.session_state.history = []
                st.session_state.step = "면접화면"
                st.rerun()
        else:
            st.warning("정보를 모두 입력하세요.")


# --- 3. 면접 화면 (1~3턴 흐름 제어) ---
elif st.session_state.step == "면접화면":
    st.title(f"🎙️ {st.session_state.company} - {st.session_state.job} 면접")

    turn_titles = {1: "1턴: 인성 및 조직적응력 질문", 2: "2턴: 직무 역량 질문", 3: "3턴: 심층 꼬리질문"}
    st.subheader(f"[{turn_titles[st.session_state.turn]}]")

    st.info(f"**면접관:** {st.session_state.current_question}")

    audio_value = st.audio_input("답변 녹음하기", key=f"audio_{st.session_state.turn}")

    if audio_value is not None:
        with st.spinner("STT 변환 중..."):
            with open("temp_answer.wav", "wb") as f:
                f.write(audio_value.getbuffer())
            stt_text = transcribe_audio("temp_answer.wav")

            st.success("답변이 정상적으로 인식되었습니다!")
            st.write(f"📝 **내 답변:** {stt_text}")

            button_label = "다음 질문으로 넘어가기 ➡️" if st.session_state.turn < 3 else "📊 종합 결과 확인하기"

            if st.button(button_label):
                st.session_state.history.append({
                    "turn": st.session_state.turn,
                    "question": st.session_state.current_question,
                    "answer": stt_text
                })

                if st.session_state.turn == 1:
                    with st.spinner("2턴 질문(직무 역량)을 생성하고 있습니다..."):
                        st.session_state.current_question = generate_questions(st.session_state.company, st.session_state.job, "job", api_key)
                        st.session_state.turn = 2
                        st.rerun()

                elif st.session_state.turn == 2:
                    with st.spinner("답변을 분석하여 꼬리질문을 준비하고 있습니다..."):
                        eval_result = evaluate_answer(
                            question=st.session_state.current_question,
                            answer=stt_text,
                        )
                        st.session_state.history[-1]["evaluation"] = eval_result

                        st.session_state.current_question = eval_result["tail_question"]
                        st.session_state.turn = 3
                        st.rerun()

                elif st.session_state.turn == 3:
                    st.session_state.step = "결과화면"
                    st.rerun()


# --- 4. 결과 화면 (종합 피드백 대시보드) ---
elif st.session_state.step == "결과화면":
    st.title("📊 AI 면접 종합 결과 리포트")
    st.write("3턴의 면접이 모두 종료되었습니다. 아래에서 피드백을 확인하세요.")

    with st.spinner("최종 리포트를 계산하고 있습니다..."):
        for item in st.session_state.history:
            if "evaluation" not in item:
                item["evaluation"] = evaluate_answer(item["question"], item["answer"])

    scores = [item["evaluation"]["score"] for item in st.session_state.history]
    total_score = round(sum(scores) / len(scores)) if scores else 0

    st.subheader("🏆 총점")
    st.metric(label="AI 면접관의 종합 평가 점수 (3턴 평균)", value=f"{total_score}점")

    st.subheader("🔍 턴별 상세 피드백")
    turn_titles = {1: "1턴 (인성)", 2: "2턴 (직무 역량)", 3: "3턴 (꼬리질문)"}

    for item in st.session_state.history:
        ev = item["evaluation"]
        turn_label = turn_titles.get(item["turn"], f"{item['turn']}턴")
        with st.expander(f"📌 {turn_label} — {ev['score']}점"):
            st.write(f"**🗣️ 면접관:** {item['question']}")
            st.write(f"**👤 내 답변:** {item['answer']}")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**두괄식**\n\n{ev['feedback']['두괄식']}")
            with col2:
                st.warning(f"**키워드 활용**\n\n{ev['feedback']['키워드']}")
            with col3:
                st.success(f"**분량**\n\n{ev['feedback']['분량']}")

            st.write(f"**논리구조:** {ev['feedback']['논리구조']}")
            st.write("**✨ 이렇게 답변했다면 더 좋았을 거예요 (모범 답변):**")
            st.code(ev["improved_answer"], language="text")

    st.write("")
    if st.button("🔄 처음으로 돌아가기 (다시하기)"):
        st.session_state.step = "입력화면"
        st.session_state.turn = 1
        st.session_state.history = []
        st.rerun()