import os
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
import PyPDF2

# Path për Service Account Key
SERVICE_ACCOUNT_FILE = "./keys/esg-agent-key.json"
FOLDER_ID = "1WoKxRCPNVIdLQfzmITZFnSqyVTJCybkr"

# Initialize session_state
if "selected_pdf" not in st.session_state:
    st.session_state.selected_pdf = None
if "pdf_content" not in st.session_state:
    st.session_state.pdf_content = ""

# Authenticate with Google Drive
@st.cache_resource
def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Failed to authenticate Google Drive: {e}")
        return None

def list_pdfs(service, folder_id):
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()
        return results.get("files", [])
    except Exception as e:
        st.error(f"Failed to list PDFs: {e}")
        return []

def download_pdf(service, file_id, file_name="temp.pdf"):
    try:
        request = service.files().get_media(fileId=file_id)
        file_path = os.path.join("./", file_name)
        with open(file_path, "wb") as f:
            downloader = request.execute()
            f.write(downloader)
        return file_path
    except Exception as e:
        st.error(f"Failed to download PDF: {e}")
        return None

def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        return ""

# Streamlit UI
def main():
    st.set_page_config(page_title="Chat with PDFs", page_icon="📚", layout="wide")
    st.title("📚 Chat with your Google Drive PDFs")

    drive_service = get_drive_service()
    if not drive_service:
        return

    pdf_files = list_pdfs(drive_service, FOLDER_ID)
    if not pdf_files:
        st.warning("No PDFs found in the Google Drive folder.")
        return

    file_names = [file["name"] for file in pdf_files]
    choice = st.selectbox("Select a PDF to chat with:", file_names)

    if st.button("Load PDF"):
        st.session_state.selected_pdf = choice
        file_id = [f["id"] for f in pdf_files if f["name"] == choice][0]
        pdf_path = download_pdf(drive_service, file_id, "selected.pdf")
        if pdf_path:
            st.session_state.pdf_content = extract_text_from_pdf(pdf_path)

    if st.session_state.selected_pdf:
        st.subheader(f"Extracted text from {st.session_state.selected_pdf}:")
        st.text_area("Content", st.session_state.pdf_content[:2000], height=300)

        # Placeholder për AI integration
        user_q = st.text_input("Ask a question about this PDF")
        if user_q:
            st.info("🤖 AI response will appear here (integration needed)")

if __name__ == "__main__":
    main()
