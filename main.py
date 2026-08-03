"""
전체 파이프라인 실행 데모 (원본 노트북 cell 18~21)

흐름: A(질문 생성) -> 녹음 -> B(STT) -> B(평가) -> A(다음 질문 생성)

주의: recorder.record_audio_manual()은 Colab 전용입니다.
로컬에서 돌리려면 recorder.py 하단 주석의 sounddevice 예시로 교체하세요.
"""
from IPython.display import display, Audio

from question_generator import get_next_question
from recorder import record_audio_manual
from transcriber import transcribe_audio
from evaluator import evaluate_answer


def main():
    resume = "백엔드 개발자"

    # 1턴: 질문 생성 + 재생
    q1 = get_next_question(resume, turn=0)
    print("Q1:", q1["question"])
    display(Audio(q1["audio_path"]))

    # 사용자 답변 녹음
    audio_file = record_audio_manual("user_answer1.wav")

    # STT + 평가
    answer1_text = transcribe_audio(audio_file)
    print("STT 결과:", answer1_text)

    result1 = evaluate_answer(q1["question"], answer1_text, q1["required_keywords"])
    print("평가 결과:", result1["feedback"])

    # 다음 턴 질문 생성 (B가 만든 꼬리질문 사용)
    q2 = get_next_question(resume, turn=1, tail_question_from_B=result1["tail_question"])
    print("Q2:", q2["question"])
    display(Audio(q2["audio_path"]))

    # 결과 상세 출력
    print("점수:", result1["score"])
    print("두괄식:", result1["feedback"]["두괄식"])
    print("논리구조:", result1["feedback"]["논리구조"])
    print("키워드:", result1["feedback"]["키워드"])
    print("분량:", result1["feedback"]["분량"])
    print("개선답변:", result1["improved_answer"])
    print("꼬리질문(tail_question):", result1["tail_question"])


if __name__ == "__main__":
    main()