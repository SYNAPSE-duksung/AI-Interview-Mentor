from google import genai


def generate_questions(company: str, job: str, q_type: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)

    if q_type == "personality":
        prompt = f'''당신은 면접관입니다.
지원 회사:{company} / 지원 직무:{job}
{company}의 기업 문화나 팀워크에 관한 '인성/조직적응력' 질문 1개만 물음표로 끝나게 작성하세요.'''
    else:
        prompt = f'''당신은 면접관입니다.
지원 회사:{company} / 지원 직무:{job}
{company}에서{job} 업무를 수행할 때 필요한 '직무 역량' 질문 1개만 물음표로 끝나게 작성하세요.'''
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt
    )
    return response.text.strip()


# ===== 여기부터 새로 추가 =====
def generate_keywords_for_question(job: str, question: str, api_key: str) -> list[str]:
    """
    입력: 직무, 질문 텍스트, API 키
    출력: 이 질문에 대한 좋은 답변이라면 포함되어야 할 키워드 리스트
    """
    client = genai.Client(api_key=api_key)
    prompt = f"""당신은 채용 담당 면접관입니다. 아래 직무와 면접 질문을 보고,
이 질문에 대한 좋은 답변이라면 반드시 포함되어야 할 핵심 키워드를
3~5개 뽑아주세요.

[지원 직무]
{job}

[면접 질문]
{question}

[출력 형식 - 반드시 준수]
- 키워드만 쉼표로 구분해서 한 줄로 출력
- 설명, 번호, 부가 텍스트 절대 포함 금지
- 예시 형식: 데이터 분석, 협업, 트러블슈팅
"""
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt
    )
    return [kw.strip() for kw in response.text.strip().split(",") if kw.strip()]