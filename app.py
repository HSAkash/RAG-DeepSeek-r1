from typing import List
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from accord.file_loader import load_file
from accord.database import Database

import sys
import os

# print("Current working directory:", os.getcwd())  # Check current directory
# print("Python search paths:", sys.path)  # Print all paths Python searches

# sys.path.append(os.path.abspath("."))  # Adds the current directory to Python path

# database connection
db = Database()
db.create_table()


# Streamlit configuration
st.set_page_config(
    page_title="Accord",
    page_icon=":shark:",
    layout="centered",
    initial_sidebar_state="auto",
)

st.header("Accord RAG")
st.subheader("Get info from Documents")

@st.cache_resource(show_spinner=False)
def create_chatbot (files: List [UploadedFile]):
    files = [load_file(file) for file in files]
    return files

def show_upload_documents() -> List [UploadedFile]:
    holder = st.empty()
    with holder.container():
        uploaded_files = st.file_uploader(
            label="Upload files", type=["pdf", "docx", "md", "txt"], accept_multiple_files=True
        )
    if not uploaded_files:
        st.stop()
    with st.spinner ("Analyzing your document(s)..."):
        holder.empty()
        return uploaded_files
    
uploaded_files = show_upload_documents()
chatbot = create_chatbot (uploaded_files)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        'ai': 'welcome'
    }]

with st.sidebar:
    st.title("Your files")
    file_list_text = "\n".join([f"- {file.name}" for file in chatbot])
    st.markdown(file_list_text)


for message in st.session_state.messages:
    avatar = "🤖" 
    with st.chat_message("akash", avatar=avatar):
        st.markdown ("how are otu")