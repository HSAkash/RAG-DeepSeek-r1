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
def create_vector_db(files: List[UploadedFile]):
    files = [load_file(file) for file in files]
    if files:
        data_ingestor.create_vector_store(files)


# Display chat history at the top
if "messages" not in st.session_state:
    st.session_state.messages = create_history(WELCOME_MESSAGE)

for message in st.session_state.messages:
    avatar = "🤖" if message.role == Role.ASSISTANT else "👤"
    with st.chat_message(message.role.value, avatar=avatar):
        st.markdown(message.content)


# Ensure session state variables are initialized
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

def handle_file_upload(unique_key_suffix=""):
    unique_key = f"file_uploader_{unique_key_suffix}"
    
    uploaded_files = st.file_uploader(
        label="Upload files", 
        type=["pdf", "docx", "md", "txt"], 
        accept_multiple_files=True, 
        key=unique_key  
    )
    
    if uploaded_files:
        st.session_state.uploaded_files.extend(uploaded_files)  # No more AttributeError
        with st.spinner("Analyzing your document(s)..."):
            create_vector_db(uploaded_files)



# Display uploaded files in the sidebar
files = database.get_data()
if len(files) > 1:
    # print(files)
    chatbot.set_retriever(files[0]["document_path"], files[0]["vector_path"])



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

# Call the function
handle_file_upload("1")


def process_files(options, option):
    chatbot.set_retriever(options[option]["document_path"], options[option]["vector_path"])
    # print(options[option]["document_path"], options[option]["vector_path"])

# Select an option
options = {}
for file in files:
    options[f"{file['id']}. {file['name']}"] = file
selected_option = st.selectbox("Select your file:", options)

# Call function if valid option is selected
if selected_option != "Select":
    process_files(options, selected_option)

with st.sidebar:
    st.title("Uploaded files")
    file_list_text = "\n".join([f"- {file['name']}" for file in files])
    st.markdown(file_list_text)


