"""
[공통] 사용자 음성 녹음 모듈

⚠️ 중요: 이 파일의 record_audio_manual()은 Google Colab 노트북 환경 전용입니다.
브라우저 JS(navigator.mediaDevices)를 google.colab.output.eval_js로 호출하는
방식이라, 일반 .py 스크립트로 VS Code/터미널에서 실행하면 동작하지 않습니다
(google.colab 모듈 자체가 없어서 import 단계에서 에러가 납니다).

- Colab 노트북에서 계속 쓸 거라면: 이 파일을 그대로 .ipynb 셀에 넣어 쓰세요.
- 로컬(VS Code) 파이프라인에 넣고 싶다면: sounddevice, PyAudio 같은
  로컬 마이크 녹음 라이브러리로 교체해야 합니다. (예시는 파일 하단 주석 참고)
"""
from IPython.display import display, HTML, Javascript
from google.colab import output
from base64 import b64decode

RECORD_JS = """
function waitForRecording() {
  return new Promise((resolve) => {
    let recorder, chunks = [], stream, startTime, timerInterval;

    document.getElementById('startBtn').onclick = async () => {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recorder = new MediaRecorder(stream);
      chunks = [];
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.start();

      startTime = Date.now();
      document.getElementById('status').innerText = "🔴 녹음 중...";
      document.getElementById('startBtn').disabled = true;
      document.getElementById('stopBtn').disabled = false;

      timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const min = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const sec = String(elapsed % 60).padStart(2, '0');
        document.getElementById('timer').innerText = `${min}:${sec}`;
      }, 200);
    };

    document.getElementById('stopBtn').onclick = () => {
      clearInterval(timerInterval);
      document.getElementById('status').innerText = "⏳ 처리 중...";
      document.getElementById('stopBtn').disabled = true;

      recorder.onstop = async () => {
        const blob = new Blob(chunks);
        const reader = new FileReader();
        reader.onloadend = () => {
          stream.getTracks().forEach(t => t.stop());
          document.getElementById('status').innerText = "✅ 녹음 완료!";
          resolve(reader.result);
        };
        reader.readAsDataURL(blob);
      };
      recorder.stop();
    };
  });
}
"""

RECORD_HTML = """
<div style="font-family: sans-serif; padding: 10px; border: 1px solid #ccc; border-radius: 8px; width: 300px;">
  <div id="status" style="font-size: 16px; margin-bottom: 8px;">대기 중</div>
  <div id="timer" style="font-size: 28px; font-weight: bold; margin-bottom: 12px;">00:00</div>
  <button id="startBtn" style="padding: 8px 16px; margin-right: 8px;">🎤 녹음 시작</button>
  <button id="stopBtn" disabled style="padding: 8px 16px;">⏹ 녹음 종료</button>
</div>
"""


def record_audio_manual(filename="user_answer.wav"):
    """
    버튼으로 직접 녹음 시작/종료하고, 경과 시간이 실시간으로 표시되는 녹음 함수.
    '녹음 종료' 버튼을 누르면 자동으로 파일 저장까지 완료됨.
    (Colab 노트북 환경 전용)
    """
    display(Javascript(RECORD_JS))
    display(HTML(RECORD_HTML))

    # waitForRecording()은 버튼 클릭 이벤트를 등록만 하고,
    # 실제로는 사용자가 '종료' 버튼을 눌러 resolve()가 호출될 때까지 여기서 대기함
    s = output.eval_js('waitForRecording()')

    b = b64decode(s.split(',')[1])
    with open(filename, "wb") as f:
        f.write(b)
    print(f"파일 저장 완료: {filename}")
    return filename


# ---------------------------------------------------------------------------
# 로컬(VS Code/터미널) 대안 예시 - 필요하면 아래처럼 sounddevice로 교체하세요.
# pip install sounddevice scipy
#
# import sounddevice as sd
# from scipy.io.wavfile import write
#
# def record_audio_local(filename="user_answer.wav", seconds=15, samplerate=16000):
#     print("🎤 녹음 시작...")
#     audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1)
#     sd.wait()
#     write(filename, samplerate, audio)
#     print(f"파일 저장 완료: {filename}")
#     return filename
# ---------------------------------------------------------------------------