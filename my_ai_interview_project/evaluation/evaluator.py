"""
[평가 모듈] Streamlit 앱용

원본(루트의 evaluator.py, Colab/로컬 스크립트용)에서 아래 2가지를 수정함.

1. EXAONE 모델 로딩을 함수로 감싸고 @st.cache_resource를 추가.
   -> Streamlit은 사용자가 버튼 하나 누를 때마다 main.py 전체를 다시 실행(rerun)하는데,
      원본처럼 모듈 최상단에서 모델을 로드하면 세션마다 반복 로드될 위험 존재.
      st.cache_resource를 쓰면 앱이 켜져 있는 동안 딱 한 번만 로드되고 재사용.
      (audio/stt.py의 whisper 모델 로딩과 동일한 패턴입니다)

2. Gemini API 키는 필요 X
   -> evaluate_answer()는 규칙기반 채점(순수 파이썬)과 EXAONE(로컬 모델)만 사용하고,
      Gemini API를 호출하지 않음. 그래서 이 파일에는 api_key 파라미터가 존재 X.
"""
import json
import re

import streamlit as st
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# ===== Rule-based 평가 함수 =====

def evaluate_rules(answer: str, required_keywords: list) -> dict:
    """
    LLM 없이 파이썬 코드로만 답변의 분량, 키워드, 두괄식 여부를 1차 채점하는 함수.
    """
    evaluation_result = {}

    # 1. 분량 평가 (150자 ~ 400자 권장)
    char_count = len(answer)
    if char_count < 150:
        volume_status = "❌ 부족"
        volume_desc = f"현재 {char_count}자입니다. 답변이 너무 짧으면 경험의 구체성과 논리성이 떨어져 보입니다. 150자 이상으로 배경과 성과를 더 보강해 보세요."
    elif 150 <= char_count <= 400:
        volume_status = "✅ 적정"
        volume_desc = f"현재 {char_count}자입니다. 면접관이 집중해서 듣기 가장 좋은 알맞은 분량입니다."
    else:
        volume_status = "⚠️ 과다"
        volume_desc = f"현재 {char_count}자입니다. 답변이 400자를 넘어가면 핵심이 흐려지고 지루해질 수 있으니 곁가지 내용을 덜어내 보세요."

    evaluation_result["분량"] = {"상태": volume_status, "설명": volume_desc, "글자수": char_count}

    # 2. 키워드 포함 여부 평가
    found_keywords = [kw for kw in required_keywords if kw in answer]
    missing_keywords = [kw for kw in required_keywords if kw not in answer]

    if not required_keywords:
        keyword_status = "➖ 해당없음"
        keyword_desc = "이 질문에는 별도로 지정된 핵심 키워드가 없습니다."
    elif not missing_keywords:
        keyword_status = "✅ 만족"
        keyword_desc = f"직무 핵심 키워드({', '.join(found_keywords)})가 문장에 아주 잘 녹아있습니다."
    else:
        keyword_status = "⚠️ 보완 필요"
        keyword_desc = f"핵심 역량을 드러내는 키워드 '{', '.join(missing_keywords)}'(이)가 빠져있습니다. 해당 단어들을 사용하여 답변을 구체화해 보세요."

    evaluation_result["키워드"] = {
        "상태": keyword_status, "설명": keyword_desc,
        "포함된키워드": found_keywords, "누락된키워드": missing_keywords
    }

    # 3. 두괄식 여부 1차 평가
    sentences = [s.strip() for s in re.split(r'[.!?]', answer) if s.strip()]
    first_sentence = sentences[0] if sentences else ""

    conclusion_markers = ["강점", "역량", "이유", "경험", "핵심", "성과", "역할", "배웠", "능력", "장점"]
    is_conclusion_style = any(marker in first_sentence for marker in conclusion_markers)

    if is_conclusion_style:
        conclusion_status = "✅ 두괄식 구성 (1차 합격)"
        conclusion_desc = f"첫 문장('{first_sentence}')에서 핵심 역량을 먼저 제시하여 면접관의 주의를 끄는 좋은 시작입니다."
    else:
        conclusion_status = "❌ 미흡 (1차 불합격)"
        conclusion_desc = "첫 문장에 결론이나 핵심 강점을 나타내는 표현이 부족합니다. '저의 강점은 ~입니다' 혹은 '저는 ~한 경험이 있습니다'처럼 결론부터 앞세워 시작해 보세요."

    evaluation_result["두괄식_기초"] = {"상태": conclusion_status, "설명": conclusion_desc, "첫문장": first_sentence}

    return evaluation_result


# ===== EXAONE 4.0 모델 로드 (Streamlit 캐싱) =====

@st.cache_resource(show_spinner="평가 모델(EXAONE)을 불러오는 중입니다... (최초 1회, 다소 시간이 걸려요)")
def load_exaone_model():
    model_id = "LGAI-EXAONE/EXAONE-4.0-1.2B"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    return tokenizer, model


# ===== EXAONE 기반 논리구조 평가 + 개선답변 + 꼬리질문 생성 =====

def evaluate_logical_structure(question: str, answer: str) -> dict:
    """
    EXAONE 4.0 모델을 이용해 답변의 논리구조를 평가하고, 개선 답변과 꼬리질문을 생성하는 함수.
    """
    tokenizer, model = load_exaone_model()

    system_prompt = (
        "너는 대기업 전문 채용 면접관이자 AI 취업 코치이다.\n"
        "제시된 [면접 질문]과 [사용자 답변]을 분석하여 아래 3가지 항목을 수행하라.\n\n"
        "1. 논리구조: 답변이 '결론 -> 근거 -> 마무리'의 논리적 흐름을 잘 갖추고 있는지 구체적인 이유를 들어 2~3문장으로 평가하라.\n"
        "2. 개선된답변: 사용자의 답변 소재를 살리되, 직무 역량이 더 돋보이도록 두괄식과 논리적 구조를 갖춘 모범 답변을 작성하라.\n"
        "3. 꼬리질문: 답변 내용 중 모호하거나 구체적인 검증이 더 필요한 부분을 파고드는 날카로운 면접관의 꼬리질문 1개를 작성하라.\n\n"
        "반드시 아래의 JSON 포맷으로만 응답하며, JSON 외의 서론이나 설명은 절대 추가하지 마라.\n"
        "{\n"
        '  "논리구조": "이곳에 논리구조 평가 내용을 작성",\n'
        '  "개선된답변": "이곳에 개선된 모범 답변을 작성",\n'
        '  "꼬리질문": "이곳에 꼬리질문 작성"\n'
        "}"
    )
    user_message = f"[면접 질문]: {question}\n[사용자 답변]: {answer}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        enable_thinking=False,
        return_dict=True,
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=600,
            do_sample=True,
            temperature=0.3,
            top_p=0.9,
        )

    generated_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    try:
        start_idx = generated_text.find("{")
        end_idx = generated_text.rfind("}") + 1
        json_string = generated_text[start_idx:end_idx]
        result_dict = json.loads(json_string)
    except Exception as e:
        result_dict = {
            "논리구조": "LLM 평가 도중 오류가 발생했습니다. 답변의 흐름을 다시 점검해 주세요.",
            "개선된답변": answer,
            "꼬리질문": "방금 답변하신 내용 중 가장 보람찼던 점은 무엇인가요?"
        }
        print(f"⚠️ JSON 파싱 실패로 기본값 대체 (에러 원인: {e})")
        print(f"원본 모델 출력 내용:\n{generated_text}")

    return result_dict


# ===== 최종 통합 함수 =====

def evaluate_answer(question: str, answer: str, required_keywords: list = None) -> dict:
    """
    [최종 API 인터페이스 함수]
    인풋: 면접 질문(str), STT 변환 텍스트(str), 필수 키워드 리스트(선택)
    아웃풋: Streamlit 화면에 바로 뿌릴 수 있는 표준 리포트 딕셔너리(dict)
    """
    if required_keywords is None:
        required_keywords = []

    rules = evaluate_rules(answer, required_keywords)
    llm_result = evaluate_logical_structure(question, answer)

    total_score = 100
    if "❌" in rules["분량"]["상태"]:
        total_score -= 15
    elif "⚠️" in rules["분량"]["상태"]:
        total_score -= 5

    if "❌" in rules["두괄식_기초"]["상태"]:
        total_score -= 15

    if "⚠️" in rules["키워드"]["상태"]:
        total_score -= len(rules["키워드"]["누락된키워드"]) * 10

    total_score = max(total_score, 40)

    final_report = {
        "score": total_score,
        "feedback": {
            "두괄식": f"{rules['두괄식_기초']['상태']} | {rules['두괄식_기초']['설명']}",
            "논리구조": llm_result["논리구조"],
            "키워드": f"{rules['키워드']['상태']} | {rules['키워드']['설명']}",
            "분량": f"{rules['분량']['상태']} | {rules['분량']['설명']}"
        },
        "improved_answer": llm_result["개선된답변"],
        "tail_question": llm_result["꼬리질문"]
    }

    return final_report