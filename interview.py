import config
import streamlit as st
# Page config
st.set_page_config(page_title="Interview", page_icon=config.AVATAR_INTERVIEWER)
import time
import os
import pandas as pd
from utils import (
    check_password,
    check_if_interview_completed,
    save_interview_data,
)

# Load API library
if "gpt" in config.MODEL.lower():
    api = "openai"
    import openai
    # DEBUG: Check if key is loaded
    st.write("✅ API key loaded:", "API_KEY_OPENAI" in st.secrets)
    openai.api_key = st.secrets["API_KEY_OPENAI"]
elif "claude" in config.MODEL.lower():
    api = "anthropic"
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["API_KEY_ANTHROPIC"])
else:
    raise ValueError("Model must contain 'gpt' or 'claude'.")



# RTL styling
st.markdown("""
<style>
body { direction: rtl; text-align: right; font-family: "Vazir", sans-serif; }
.stChatMessage { direction: rtl !important; text-align: right !important; }
</style>
""", unsafe_allow_html=True)

# Auth
if config.LOGINS:
    pwd_correct, username = check_password()
    if not pwd_correct:
        st.stop()
    else:
        st.session_state.username = username
else:
    st.session_state.username = "testaccount"

# Directory setup
for dir_path in [config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY, config.BACKUPS_DIRECTORY]:
    os.makedirs(dir_path, exist_ok=True)

# Session state setup
st.session_state.setdefault("interview_active", True)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("start_time", time.time())
st.session_state.setdefault("start_time_file_names", time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(st.session_state.start_time)))

# Check for completed interview
if check_if_interview_completed(config.TIMES_DIRECTORY, st.session_state.username) and not st.session_state.messages:
    st.session_state.interview_active = False
    st.markdown("Interview already completed.")

# Quit button
col1, col2 = st.columns([0.85, 0.15])
with col2:
    if st.session_state.interview_active and st.button("Quit", help="End the interview."):
        st.session_state.interview_active = False
        quit_message = "You have cancelled the interview."
        st.session_state.messages.append({"role": "assistant", "content": quit_message})
        save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY)

# Replay chat history
for message in st.session_state.messages[1:]:
    if not any(code in message["content"] for code in config.CLOSING_MESSAGES):
        with st.chat_message(message["role"], avatar=config.AVATAR_INTERVIEWER if message["role"] == "assistant" else config.AVATAR_RESPONDENT):
            st.markdown(message["content"])

# Load model parameters
api_kwargs = {
    "messages": st.session_state.messages,
    "model": config.MODEL,
    "max_tokens": config.MAX_OUTPUT_TOKENS,
}
if config.TEMPERATURE is not None:
    api_kwargs["temperature"] = config.TEMPERATURE
if api == "openai":
    api_kwargs["stream"] = True
else:
    api_kwargs["system"] = config.SYSTEM_PROMPT

# System message
if not st.session_state.messages:
    if api == "openai":
        st.session_state.messages.append({"role": "system", "content": config.SYSTEM_PROMPT})
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            stream = openai.chat.completions.create(**api_kwargs)
            message_interviewer = st.write_stream(stream)
    else:
        st.session_state.messages.append({"role": "user", "content": "Hi"})
        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            message_placeholder = st.empty()
            message_interviewer = ""
            with client.messages.stream(**api_kwargs) as stream:
                for text_delta in stream.text_stream:
                    if text_delta:
                        message_interviewer += text_delta
                        message_placeholder.markdown(
                            f'<div style="direction: rtl; text-align: right;">{message_interviewer}▌</div>',
                            unsafe_allow_html=True
                        )
            message_placeholder.markdown(
                f'<div style="direction: rtl; text-align: right;">{message_interviewer}</div>',
                unsafe_allow_html=True
            )
    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
    save_interview_data(
        username=st.session_state.username,
        transcripts_directory=config.BACKUPS_DIRECTORY,
        times_directory=config.BACKUPS_DIRECTORY,
        file_name_addition_transcript=f"_transcript_started_{st.session_state.start_time_file_names}",
        file_name_addition_time=f"_time_started_{st.session_state.start_time_file_names}"
    )

# Main chat
if st.session_state.interview_active:
    if message_respondent := st.chat_input("Your message here"):
        st.session_state.messages.append({"role": "user", "content": message_respondent})
        with st.chat_message("user", avatar=config.AVATAR_RESPONDENT):
            st.markdown(message_respondent)

        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            message_placeholder = st.empty()
            message_interviewer = ""

            if api == "openai":
                stream = openai.chat.completions.create(**api_kwargs)
                for message in stream:
                    text_delta = message.choices[0].delta.content
                    if text_delta:
                        message_interviewer += text_delta
                        if len(message_interviewer) > 5:
                            message_placeholder.markdown(message_interviewer + "▌")
                        if any(code in message_interviewer for code in config.CLOSING_MESSAGES):
                            message_placeholder.empty()
                            break
            else:
                with client.messages.stream(**api_kwargs) as stream:
                    for text_delta in stream.text_stream:
                        if text_delta:
                            message_interviewer += text_delta
                            if len(message_interviewer) > 5:
                                message_placeholder.markdown(message_interviewer + "▌")
                            if any(code in message_interviewer for code in config.CLOSING_MESSAGES):
                                message_placeholder.empty()
                                break

            if not any(code in message_interviewer for code in config.CLOSING_MESSAGES):
                message_placeholder.markdown(message_interviewer)
                st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
                try:
                    save_interview_data(
                        username=st.session_state.username,
                        transcripts_directory=config.BACKUPS_DIRECTORY,
                        times_directory=config.BACKUPS_DIRECTORY,
                        file_name_addition_transcript=f"_transcript_started_{st.session_state.start_time_file_names}",
                        file_name_addition_time=f"_time_started_{st.session_state.start_time_file_names}",
                    )
                except:
                    pass
            else:
                st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
                st.session_state.interview_active = False
                for code in config.CLOSING_MESSAGES:
                    if code in message_interviewer:
                        closing_message = config.CLOSING_MESSAGES[code]
                        st.markdown(closing_message)
                        st.session_state.messages.append({"role": "assistant", "content": closing_message})
                        break
                final_transcript_stored = False
                while not final_transcript_stored:
                    save_interview_data(
                        username=st.session_state.username,
                        transcripts_directory=config.TRANSCRIPTS_DIRECTORY,
                        times_directory=config.TIMES_DIRECTORY,
                    )
                    final_transcript_stored = check_if_interview_completed(
                        config.TRANSCRIPTS_DIRECTORY, st.session_state.username
                    )
                    time.sleep(0.1)


