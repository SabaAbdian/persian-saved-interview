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
    """Returns 'True' if the user has entered a correct password."""

    def login_form():
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        if st.session_state.username in st.secrets.passwords and hmac.compare_digest(
            st.session_state.password,
            st.secrets.passwords[st.session_state.username],
        ):
            st.session_state.password_correct = True
        else:
            st.session_state.password_correct = False
        del st.session_state.password  # Never store the password

    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.username

# -----------------------
# CHECK IF INTERVIEW COMPLETE
# -----------------------
def check_if_interview_completed(directory, username):
    """Check if interview transcript/time file exists which signals that interview was completed."""
    if username != "testaccount":
        try:
            with open(os.path.join(directory, f"{username}.txt"), "r") as _:
                return True
        except FileNotFoundError:
            return False
    return False

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
    """Write interview transcript and time to disk."""
    with open(
        os.path.join(
            transcripts_directory, f"{username}{file_name_addition_transcript}.txt"
        ),
        "w",
        encoding="utf-8"
    ) as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    with open(
        os.path.join(times_directory, f"{username}{file_name_addition_time}.txt"),
        "w",
        encoding="utf-8"
    ) as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(
            f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n"
            f"Interview duration (minutes): {duration:.2f}"
        )

# -----------------------
# UPLOAD CSV TO GOOGLE DRIVE
# -----------------------
def upload_csv_to_drive(dataframe, filename, folder_id):
    """Uploads a Pandas DataFrame as a CSV file to a Google Drive folder."""
    service_account_info = json.loads(st.secrets["GDRIVE_SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(service_account_info)

    service = build("drive", "v3", credentials=credentials)

    csv_buffer = io.StringIO()
    dataframe.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(csv_buffer, mimetype="text/csv")

    uploaded
