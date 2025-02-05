from typing import List
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from accord.file_loader import load_file
from accord.database import Database
from accord.chatbot import Chatbot
from accord.data_ingestor import DataIngestor
from accord.entity import (
    File,
    Role,
    Message,
    ChunkEvent,
    SourcesEvent,
    FinalAnswerEvent,
    State,
)

from accord.utils import get_config, create_history

import sys
import os

config = get_config()
# database connection
database = Database()
database.create_table()

chatbot = Chatbot(database)
data_ingestor = DataIngestor(database)

os.makedirs(config.vector_store.VECTOR_STORE_DIR, exist_ok=True)
os.makedirs(config.vector_store.DOCUMENT_STORE_DIR, exist_ok=True)


# sys.path.append(os.path.abspath("."))  # Adds the current directory to Python path


WELCOME_MESSAGE = Message(role=Role.ASSISTANT, content="Hello, I'm accord. How can I help you today?")

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
    if files:
        # data_ingestor.create_vector_store(files)
        return database.get_data()
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
files = create_chatbot (uploaded_files)

if files:
    chatbot.set_retriever(files[0]["document_path"], files[0]["vector_path"])


if "messages" not in st.session_state:
    st.session_state.messages = create_history(WELCOME_MESSAGE)

with st.sidebar:
    st.title("Your files")
    file_list_text = "\n".join([f"- {file['name']}" for file in files])
    st.markdown(file_list_text)


for message in st.session_state.messages:
    avatar = "🤖" if message.role == Role.ASSISTANT else "👤"
    with st.chat_message(message.role.value, avatar=avatar):
        st.markdown (message.content)


if prompt := st.chat_input("Type your message..."):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        full_response = ""
        message_placeholder = st.empty()
        message_placeholder.status("Analysing", state="running")
        for event in chatbot.ask(prompt, st.session_state.messages):
            if isinstance (event, SourcesEvent):
                for i, doc in enumerate(event.content):
                    with st.expander (f"Source #{i + 1}"):
                        st.markdown(doc.page_content)
            if isinstance (event, ChunkEvent):
                chunk = event.content
                full_response += chunk
                message_placeholder.markdown(full_response)