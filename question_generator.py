"""
[A파트] 질문 생성 모듈

- generate_questions: Gemini로 직무역량 질문 1개 생성
- generate_keywords_for_question: 해당 질문의 핵심 키워드 추출 (B파트 evaluate_answer에 전달됨)
- text_to_speech: 텍스트 → mp3
- get_next_question: 위 함수들을 묶어 턴(turn)에 맞는 질문+음성+키워드를 반환하는 컨트롤 함수
"""
from gtts import gTTS

from config import client


def generate_questions(resume: str) -> str:
    """
    입력: 직무 텍스트
    출력: 직무역량 질문 1개 (문자열)
    turn=0 (최초 질문)에서만 사용됨. 이후 턴은 B(EXAONE)가 만든 tail_question 사용.
    """
    prompt = f"""당신은 15년 경력의 면접관입니다. 아래 직무를 지원한 지원자에게
실제 면접에서 나올 법한 자연스러운 한국어 직무역량 질문 1개를 만들어주세요.

[지원 정보]
- 직무: {resume}

[질문 조건]
- {resume}에 실제로 필요한 전문 지식, 기술, 경험을 확인하는 질문일 것
- 막연한 질문 금지, 실제 업무 상황을 구체적으로 반영할 것

[좋은 질문 예시 - 이런 톤과 구체성으로 작성]
- "대용량 트래픽 상황에서 시스템 장애를 경험한 적이 있다면, 어떻게 대응하셨나요?"
- "여러 이해관계자와 협업하며 기술적 의사결정을 내려야 했던 경험이 있다면 말씀해주세요."

[피해야 할 것]
- "본인의 강점은 무엇인가요?" 같은 지나치게 뻔하고 일반적인 질문
- 직무와 무관한 인성/가치관 질문
- 존댓말이 아닌 반말이나 명령형 문장

[출력 형식 - 반드시 준수]
- 질문 1개만 출력
- 질문은 한 문장, 최대 40자 내외로 간결하게 작성
- 번호, 설명, 부가 텍스트 절대 포함 금지
- 물음표로 끝나는 질문 문장 하나만 출력

이제 질문을 생성하세요.
"""
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt
    )
    return response.text.strip()


def generate_keywords_for_question(resume: str, question: str) -> list[str]:
    """
    입력: 직무, 질문 텍스트
    출력: B의 evaluate_answer(required_keywords=...) 파라미터로 전달될 키워드 리스트
    """
    prompt = f"""당신은 채용 담당 면접관입니다. 아래 직무와 면접 질문을 보고,
이 질문에 대한 좋은 답변이라면 반드시 포함되어야 할 직무 핵심 키워드를
3~5개 뽑아주세요.

[지원 직무]
{resume}

[면접 질문]
{question}

[키워드 선정 기준]
- 질문의 의도와 직접 관련된 기술/역량 키워드일 것
- 지나치게 일반적인 단어(예: "노력", "성실") 대신 구체적인 직무 용어를 우선할 것

[출력 형식 - 반드시 준수]
- 키워드만 쉼표로 구분해서 한 줄로 출력
- 설명, 번호, 부가 텍스트 절대 포함 금지
- 예시 형식: 데이터 분석, 협업, 트러블슈팅, API 설계

이제 키워드를 생성하세요.
"""
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite", contents=prompt
    )
    return [kw.strip() for kw in response.text.strip().split(",") if kw.strip()]


def text_to_speech(text: str, filename: str = "question.mp3") -> str:
    """텍스트 → 음성 파일 경로 반환"""
    tts = gTTS(text=text, lang="ko")
    tts.save(filename)
    return filename


def get_next_question(resume: str, turn: int = 0, tail_question_from_B: str = None) -> dict:
    """
    turn 0: 직무역량 메인 질문 생성 (Gemini, generate_questions)
    turn 1~2: B의 evaluate_answer()가 반환한 result["tail_question"] 값을
              그대로 받아서 음성만 입혀줌 (A는 자체 꼬리질문을 만들지 않음)

    입력:
      - resume: 지원 직무
      - turn: 현재 턴 번호 (0, 1, 2)
      - tail_question_from_B: turn>=1일 때 B의 evaluate_answer()["tail_question"] 값
    출력:
      {"question": str, "audio_path": str, "required_keywords": list[str]}
    """
    if turn == 0:
        question = generate_questions(resume)
    else:
        if tail_question_from_B is None:
            raise ValueError("turn >= 1 이면 B가 만든 tail_question이 반드시 필요합니다.")
        question = tail_question_from_B

    keywords = generate_keywords_for_question(resume, question)
    filename = f"question_turn{turn}.mp3"
    audio_path = text_to_speech(question, filename)

    return {"question": question, "audio_path": audio_path, "required_keywords": keywords}