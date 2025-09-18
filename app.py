import os
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
import PyPDF2
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
from io import BytesIO
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_pdf_question(question, context):
    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You answer questions based on PDF content."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
            temperature=1.0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to get AI response: {e}")
        return ""


# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Debug: Print loaded environment variables
st.sidebar.write("Debug: Loaded .env values")
st.sidebar.write("SERVICE_ACCOUNT_FILE:", SERVICE_ACCOUNT_FILE)
st.sidebar.write("FOLDER_ID:", FOLDER_ID)

# Validate environment variables
if not SERVICE_ACCOUNT_FILE or not FOLDER_ID:
    st.sidebar.error("Missing environment variables. Check your .env file.")
    st.stop()

# Initialize session state
if "selected_pdf" not in st.session_state:
    st.session_state.selected_pdf = None
if "pdf_content" not in st.session_state:
    st.session_state.pdf_content = ""

# Authenticate with Google Drive
@st.cache_resource
def get_drive_service():
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            st.sidebar.error(f"Service account file not found at: {SERVICE_ACCOUNT_FILE}")
            return None
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.sidebar.error(f"Failed to authenticate Google Drive: {e}")
        return None

# List PDFs in the folder
def list_pdfs(service, folder_id):
    try:
        query = f"'{folder_id}' in parents and mimeType='application/pdf'"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get("files", [])
        st.sidebar.write("Debug: Retrieved files:", files)
        return files
    except Exception as e:
        st.sidebar.error(f"Failed to list PDFs: {e}")
        return []

# Fetch PDF as in-memory stream
def fetch_pdf_stream(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        pdf_bytes = request.execute()
        return BytesIO(pdf_bytes)
    except Exception as e:
        st.error(f"Failed to fetch PDF stream: {e}")
        return None

# Extract text from PDF stream
def extract_text_from_stream(pdf_stream):
    try:
        text = ""
        reader = PyPDF2.PdfReader(pdf_stream)
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        return ""

# Streamlit UI
def main():
    st.set_page_config(page_title="Chat with PDFs", layout="wide")
    st.title("Chat with your Google Drive PDFs")

    drive_service = get_drive_service()
    if not drive_service:
        return

    pdf_files = list_pdfs(drive_service, FOLDER_ID)
    if not pdf_files:
        st.sidebar.warning("No PDFs found in the Google Drive folder.")
        return

    file_names = [file["name"] for file in pdf_files]

    # Sidebar search and selection
    st.sidebar.header("PDF Selector")
    search_term = st.sidebar.text_input("Search PDFs")
    filtered_files = [name for name in file_names if search_term.lower() in name.lower()]
    selected_name = st.sidebar.selectbox("Choose a PDF", filtered_files)

    if st.sidebar.button("Load PDF"):
        st.session_state.selected_pdf = selected_name
        file_id = next((f["id"] for f in pdf_files if f["name"] == selected_name), None)
        pdf_stream = fetch_pdf_stream(drive_service, file_id)
        if pdf_stream:
            st.session_state.pdf_content = extract_text_from_stream(pdf_stream)

    # Main content
    if st.session_state.selected_pdf:
        st.subheader(f"Extracted text from {st.session_state.selected_pdf}")
        st.text_area("Content", st.session_state.pdf_content[:2000], height=300)

        user_q = st.text_input("Ask a question about this PDF")
        if user_q:
            answer = ask_pdf_question(user_q, st.session_state.pdf_content)
            st.success(answer)

if __name__ == "__main__":
    main()
