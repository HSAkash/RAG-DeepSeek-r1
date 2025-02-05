from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from enum import Enum
from langchain.schema import Document
from dataclasses import dataclass
from typing import List, TypedDict, Iterable
from langchain_ollama import ChatOllama
from accord.utils import get_config
from accord.data_ingestor import DataIngestor
from accord.utils import remove_thinking_from_message
from accord import logger
from accord.entity import (
    File,
    Role,
    Message,
    ChunkEvent,
    SourcesEvent,
    FinalAnswerEvent,
    State,
)

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
)


class Chatbot:
    def __init__(self, database):
        self.config = get_config()
        self.database = database
        self.DataIngestor = DataIngestor(database)
        self.SYSTEM_PROMPT = self.config.llm_prompts.SYSTEM_PROMPT
        self.QUERY_TEMPLATE = self.config.llm_prompts.QUERY_TEMPLATE
        self.FILE_TEMPLATE = self.config.llm_prompts.FILE_TEMPLATE
        self.retriever = None
        self.PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
            [
                ("system",self.SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", self.QUERY_TEMPLATE),
            ]
        )
        # Initialize the LLM
        self.llm = ChatOllama(
            model=self.config.llm.MODEL_NAME,
            temperature=self.config.llm.TEMPERATURE,
            keep_alive=-1,
            verbose=False,
        )

        self.workflow = self._create_workflow()

    def _create_workflow (self) -> CompiledStateGraph:
        graph_builder = StateGraph(State).add_sequence([self._retrieve, self._generate])
        graph_builder.add_edge(START, "_retrieve")
        return graph_builder.compile()
    
    def _format_docs (self, docs: List [Document]) -> str:
        return "\n\n".join(
            self.FILE_TEMPLATE.format(name=doc.metadata["source"], content=doc.page_content) for doc in docs
        )
    
    def _retrieve(self, state: State):
        if self.retriever is None:
            return {"context": []}
        context = self.retriever.invoke(state["question"])
        return {"context": context}
    
    def _generate(self, state: State):
        messages = self.PROMPT_TEMPLATE.invoke(
            {
                "question": state["question"],
                "context": self._format_docs(state["context"]),
                "chat_history" : state ["chat_history"],
            }
        )
        answer = self.llm.invoke(messages)
        # answer = """
        #     </think> Hemel Sharker Akash is a prominent AI researcher and developer known for his work in multiple areas, including deep learning applications for health issues like Parkinson's disease detection, gesture recognition, human activity analysis, crop disease detection, and voice-based communication systems.
        # """
        return {"answer": answer}
    
    def set_retriever(self, document_path, vector_path):
        self.retriever = self.DataIngestor.get_retriever(document_path, vector_path)
    
    def _ask_model(
        self, prompt: str, chat_history: List[Message]
        ) -> Iterable[SourcesEvent | ChunkEvent | FinalAnswerEvent]:
            history = [
                AIMessage(m.content) if m.role == Role.ASSISTANT else HumanMessage(m.content)
                for m in chat_history
            ]
            payload={"question": prompt, "chat_history": history}

            config = {
                "configurable": {"thread_id": 42}
            }

            for event_type, event_data in self.workflow.stream(
                payload,
                config=config,
                stream_mode=["updates", "messages"],
            ):
                if event_type == "messages":
                    chunk, _ = event_data
                    yield ChunkEvent(chunk.content)
                if event_type == "updates":
                    if "_retrieve" in event_data:
                        documents = event_data["_retrieve"]["context"]
                        yield SourcesEvent(documents)
                    if "_generate" in event_data:
                        answer = event_data["_generate"]["answer"]
                        yield FinalAnswerEvent(answer.content)


    def ask(self, prompt: str, chat_history: List[Message]
    ) -> Iterable[SourcesEvent | ChunkEvent | FinalAnswerEvent]:
        for event in self._ask_model(prompt, chat_history):
            yield event
            if isinstance(event, FinalAnswerEvent):
                response = remove_thinking_from_message("".join(event.content))
                chat_history.append(Message(role=Role.USER, content=prompt))
                chat_history.append(Message(role=Role.ASSISTANT, content=response))