"""
[평가 모듈] Streamlit 앱용 - 2팀 파인튜닝 서버 API 호출 버전

EXAONE을 로컬에서 직접 실행하지 않고,
2팀이 Colab에서 띄운 FastAPI 서버(파인튜닝된 모델)로 요청을 보내 결과를 받아옵니다.
"""
import re
import requests
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

# 2팀이 서버 띄울 때마다 바뀌는 ngrok 주소 (매번 최신으로 업데이트 필요)
EVAL_SERVER_URL = os.environ.get("EVAL_SERVER_URL")


def evaluate_rules(answer: str, required_keywords: list) -> dict:
    """LLM 없이 파이썬 코드로만 답변의 분량, 키워드, 두괄식 여부를 1차 채점 (기존 로직 그대로 유지)"""
    evaluation_result = {}

    char_count = len(answer)
    if char_count < 150:
        volume_status = "❌ 부족"
        volume_desc = f"현재 {char_count}자입니다. 답변이 너무 짧으면 경험의 구체성과 논리성이 떨어져 보입니다."
    elif 150 <= char_count <= 400:
        volume_status = "✅ 적정"
        volume_desc = f"현재 {char_count}자입니다. 알맞은 분량입니다."
    else:
        volume_status = "⚠️ 과다"
        volume_desc = f"현재 {char_count}자입니다. 400자를 넘으면 핵심이 흐려질 수 있습니다."

    evaluation_result["분량"] = {"상태": volume_status, "설명": volume_desc, "글자수": char_count}

    found_keywords = [kw for kw in required_keywords if kw in answer]
    missing_keywords = [kw for kw in required_keywords if kw not in answer]

    if not required_keywords:
        keyword_status = "➖ 해당없음"
        keyword_desc = "이 질문에는 별도로 지정된 핵심 키워드가 없습니다."
    elif not missing_keywords:
        keyword_status = "✅ 만족"
        keyword_desc = f"직무 핵심 키워드({', '.join(found_keywords)})가 잘 녹아있습니다."
    else:
        keyword_status = "⚠️ 보완 필요"
        keyword_desc = f"키워드 '{', '.join(missing_keywords)}'가 빠져있습니다."

    evaluation_result["키워드"] = {
        "상태": keyword_status, "설명": keyword_desc,
        "포함된키워드": found_keywords, "누락된키워드": missing_keywords
    }

    sentences = [s.strip() for s in re.split(r'[.!?]', answer) if s.strip()]
    first_sentence = sentences[0] if sentences else ""
    conclusion_markers = ["강점", "역량", "이유", "경험", "핵심", "성과", "역할", "배웠", "능력", "장점"]
    is_conclusion_style = any(marker in first_sentence for marker in conclusion_markers)

    conclusion_status = "✅ 두괄식 구성 (1차 합격)" if is_conclusion_style else "❌ 미흡 (1차 불합격)"
    conclusion_desc = (
        f"첫 문장('{first_sentence}')에서 핵심을 먼저 제시했습니다."
        if is_conclusion_style else
        "첫 문장에 결론이 부족합니다."
    )
    evaluation_result["두괄식_기초"] = {"상태": conclusion_status, "설명": conclusion_desc, "첫문장": first_sentence}

    return evaluation_result


def call_exaone_server(question: str, answer: str) -> dict:
    """2팀 Colab 서버(파인튜닝된 EXAONE, FastAPI)에 요청을 보내 평가 결과를 받아옴"""
    try:
        response = requests.post(
            EVAL_SERVER_URL,
            json={"question": question, "answer": answer},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ EXAONE 평가 서버 연결에 실패했습니다. 2팀 Colab 서버가 켜져 있는지 확인해주세요. ({e})")
        return {
            "score": 60,
            "feedback": {
                "두괄식": "서버 연결 실패", "논리구조": "서버 연결 실패로 평가할 수 없습니다.",
                "키워드": "서버 연결 실패", "분량": "서버 연결 실패"
            },
            "improved_answer": answer,
            "tail_question": "구체적으로 어떤 부분에서 그렇게 판단하셨나요?"
        }


def evaluate_answer(question: str, answer: str, required_keywords: list = None) -> dict:
    """
    [최종 API 인터페이스 함수]
    Rule-based 평가는 로컬(Streamlit)에서, LLM 평가(파인튜닝 EXAONE)는 2팀 서버 호출로 처리
    """
    if required_keywords is None:
        required_keywords = []

    rules = evaluate_rules(answer, required_keywords)
    server_result = call_exaone_server(question, answer)

    total_score = server_result.get("score", 70)

    final_report = {
        "score": total_score,
        "feedback": {
            "두괄식": f"{rules['두괄식_기초']['상태']} | {rules['두괄식_기초']['설명']}",
            "논리구조": server_result.get("feedback", {}).get("논리구조", "정보 없음"),
            "키워드": f"{rules['키워드']['상태']} | {rules['키워드']['설명']}",
            "분량": f"{rules['분량']['상태']} | {rules['분량']['설명']}"
        },
        "improved_answer": server_result.get("improved_answer", answer),
        "tail_question": server_result.get("tail_question", "구체적으로 어떤 부분에서 그렇게 판단하셨나요?")
    }

    return final_report