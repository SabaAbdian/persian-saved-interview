import streamlit as st 
import hmac
import time
import os
import json
import io
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# -----------------------
# AUTHENTICATION FUNCTION
# -----------------------
def check_password():
    def login_form():
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        if (
            st.session_state.username in st.secrets["passwords"]
            and hmac.compare_digest(
                st.session_state["password"],
                st.secrets["passwords"][st.session_state.username],
            )
        ):
            st.session_state.password_correct = True
        else:
            st.session_state.password_correct = False
        del st.session_state["password"]  # Don't keep password in memory

    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.get("username", "")

# -----------------------
# CHECK IF INTERVIEW COMPLETE
# -----------------------
def check_if_interview_completed(directory, username):
    if username != "testaccount":
        try:
            with open(os.path.join(directory, f"{username}.txt"), "r"):
                return True
        except FileNotFoundError:
            return False
    return False

# -----------------------
# UPLOAD FILE TO GOOGLE DRIVE
# -----------------------
def upload_to_gdrive(content, filename, mimetype="text/plain", folder_id=None):
    credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gdrive_service_account"]
)
    service = build("drive", "v3", credentials=credentials)

    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(content.encode("utf-8")), mimetype=mimetype)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")

# -----------------------
# SAVE TRANSCRIPT AND TIME FILE
# -----------------------
def save_interview_data(
    username,
    transcripts_directory,
    times_directory,
    file_name_addition_transcript="",
    file_name_addition_time="",
):
    os.makedirs(transcripts_directory, exist_ok=True)
    os.makedirs(times_directory, exist_ok=True)

    transcript_path = os.path.join(transcripts_directory, f"{username}{file_name_addition_transcript}.txt")
    with open(transcript_path, "w", encoding="utf-8") as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    time_path = os.path.join(times_directory, f"{username}{file_name_addition_time}.txt")
    with open(time_path, "w", encoding="utf-8") as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(
            f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n"
            f"Interview duration (minutes): {duration:.2f}"
        )

    # ✅ Upload to Google Drive
    with open(transcript_path, "r", encoding="utf-8") as tf:
        upload_to_gdrive(tf.read(), f"{username}{file_name_addition_transcript}.txt")

    with open(time_path, "r", encoding="utf-8") as df:
        upload_to_gdrive(df.read(), f"{username}{file_name_addition_time}.txt")
