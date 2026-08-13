
import base64
from io import BytesIO

import streamlit as st
from google import genai
from gtts import gTTS




# 2. 대화 기록 초기화
# streamlit은 버튼을 누를 때마다 코드를 다시 실행함으로,
# session_state를 사용해 이전 대화를 유지함.
if "messages" not in st.session_state:
  st.session_state.messages = []


# 3. Gemini 클라이언트 생성
# streamlit cloud의 secrets에서 API키를 불러오기
try:
  api_key = st.secrets["GEMINI_API_KEY"]
  client = genai.Client(api_key = api_key)

except KeyError:
  st.error("Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요.")
  st.stop()


# 4. 음성을 텍스트로 변환하는 함수(STT)
def speech_to_text(audio_bytes, model):
    """녹음된 음성을 Gemini에 전달해 한국어 텍스트로 변환합니다."""

    # 바이너리 음성 데이터를 API에 전달할 수 있도록 Base64로 변환
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    interaction = client.interactions.create(
        model=model,
        input=[
            {
                "type": "text",
                "text": (
                    "다음 음성에서 사용자가 말한 내용을 정확한 한국어 문장으로 "
                    "전사하세요. 다른 설명은 하지 말고 전사 결과만 출력하세요."
                )
            },
            {
                "type": "audio",
                "data": audio_base64,
                "mime_type": "audio/wav"
            }
        ]
    )

    return interaction.output_text.strip()


# 5. Gemini 답변 생성 함수
def ask_gemini(question, model):
    """현재 질문과 이전 대화 내용을 바탕으로 답변을 생성합니다."""

    # 이전 대화 내용을 하나의 문자열로 정리
    conversation = "\n".join(
        f"{'사용자' if message['role'] == 'user' else '방바라방'}: "
        f"{message['content']}"
        for message in st.session_state.messages[:-1]
    )

    prompt = f"""
당신은 친절하고 유쾌한 한국어 AI 음성비서 '방바라방'입니다.
사용자의 질문에 이해하기 쉬운 한국어로 답변하세요.
답변은 음성으로 재생되므로 핵심 위주로 자연스럽고 간결하게 말하세요.

지금까지의 대화:
{conversation if conversation else "이전 대화 없음"}

사용자의 새로운 질문:
{question}
"""

    interaction = client.interactions.create(
        model=model,
        input=prompt
    )

    return interaction.output_text.strip()


# 6. 텍스트를 음성으로 변환하는 함수(TTS)
def text_to_speech(text):
    """Gemini의 텍스트 답변을 gTTS로 한국어 음성으로 변환합니다."""

    audio_buffer = BytesIO()

    tts = gTTS(
        text=text,
        lang="ko"
    )

    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)

    return audio_buffer.getvalue()


# 7. 제목과 프로그램 설명
st.title("🎙️ 방바라방에게 물어봐!")

st.caption(
    "음성으로 질문하면 방바라방이 Gemini를 활용해 "
    "질문을 이해하고 음성으로 답변합니다."
)

with st.expander("방바라방 프로그램에 관하여", expanded=True):
    st.markdown(
        """
        - **사용자 화면(UI):** Streamlit
        - **음성 인식(STT):** Gemini 오디오 이해 기능
        - **답변 생성:** Gemini Interactions API
        - **음성 출력(TTS):** Google Text-to-Speech(gTTS)
        """
    )


# 8. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 방바라방 설정")

    model = st.radio(
        "Gemini 모델 선택",
        options=[
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite"
        ],
        help=(
            "Gemini 3.6 Flash는 답변 품질에, "
            "Gemini 3.5 Flash-Lite는 속도와 효율에 적합합니다."
        )
    )

    st.markdown("---")

    if st.button(
        "🗑️ 대화 초기화",
        use_container_width=True
    ):
        st.session_state.messages = []
        st.rerun()


  # 9. 음성 입력 영역과 대화 출력 영역
left_column, right_column = st.columns([1, 1.3])

with left_column:
    st.subheader("🎤 방바라방에게 질문하기")

    # 브라우저의 마이크로 음성 녹음
    recorded_audio = st.audio_input(
        "마이크 버튼을 누르고 질문해주세요.",
        sample_rate=16000
    )

    # 녹음한 음성을 다시 들을 수 있도록 재생
    if recorded_audio:
        st.audio(recorded_audio)

    send_button = st.button(
        "방바라방에게 질문 보내기",
        type="primary",
        use_container_width=True,
        disabled=recorded_audio is None
    )


with right_column:
    st.subheader("💬 방바라방과의 대화")

    # session_state에 저장된 이전 질문과 답변 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


# 10. 음성 질문 처리
if send_button and recorded_audio:
    try:
        with st.spinner("방바라방이 질문을 듣고 답변을 생각하고 있어요..."):
            audio_bytes = recorded_audio.getvalue()

            # 1단계: 사용자 음성 → 질문 텍스트
            question = speech_to_text(
                audio_bytes,
                model
            )

            # 사용자 질문을 대화 기록에 저장
            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": question
                }
            )

            # 2단계: 질문 텍스트 → Gemini 답변
            answer = ask_gemini(
                question,
                model
            )

            # Gemini 답변을 대화 기록에 저장
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

            # 3단계: Gemini 답변 텍스트 → 음성
            answer_audio = text_to_speech(answer)

             # 새롭게 생성된 질문과 답변을 화면에 출력
        with right_column:
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                st.write(answer)

            # Gemini 답변을 음성으로 자동 재생
            st.audio(
                answer_audio,
                format="audio/mp3",
                autoplay=True
            )

    except Exception as error:
        st.error(f"처리 중 오류가 발생했습니다: {error}")
