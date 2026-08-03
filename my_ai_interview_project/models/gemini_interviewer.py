from google import genai

def generate_questions(company: str, job: str, q_type: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    
    if q_type == "personality":
        prompt = f'''당신은 면접관입니다. 
지원 회사: {company} / 지원 직무: {job}
{company}의 기업 문화나 팀워크에 관한 '인성/조직적응력' 질문 1개만 물음표로 끝나게 작성하세요.'''
    else:
        prompt = f'''당신은 면접관입니다. 
지원 회사: {company} / 지원 직무: {job}
{company}에서 {job} 업무를 수행할 때 필요한 '직무 역량' 질문 1개만 물음표로 끝나게 작성하세요.'''

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt
    )
    return response.text.strip()
