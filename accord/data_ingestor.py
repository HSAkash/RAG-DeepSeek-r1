import os
from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain. retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank 
from langchain_community.embeddings. fastembed import FastEmbedEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from accord.utils import get_config, remove_thinking_from_message
from accord.file_loader import File
from accord import logger
import shortuuid
from pathlib import Path
from tqdm import tqdm
import pickle


class DataIngestor:
    def __init__(self, database):
        self.config = get_config()
        self.database = database

        # Load the context prompt template
        self.CONTEXT_PROMPT = ChatPromptTemplate.from_template(
            self.config.preprocessing.context_prompt.strip())
        # Initialize the text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.preprocessing.CHUNK_SIZE,
            overlap=self.config.preprocessing.CHUNK_OVERLAP,
        )
        # Initialize the LLM
        self.llm = ChatOllama(
            model=self.config.llm.MODEL_NAME,
            temperature=self.config.llm.TEMPERATURE,
            keep_alive=-1,
            verbose=False,
        )
        # Initialize the embedding model
        self.embedding_model = FastEmbedEmbeddings(model_name=self.config.preprocessing.EMBEDDING_MODEL)
        # Initialize the reranker
        # reorders documents based on relevance.
        self.reranker = FlashrankRerank(
            model=self.config.preprocessing.RERANKER,
            top_n=self.config.preprocessing.N_CONTEXT_RESULTS,
        )

    def generate_context(self, document: str, chunk: str) -> str:
        """
        Generates the context for the chunk
        Args:
            document (str): The full document
            chunk (str): The chunk
        Returns:
            str: The context modiby based on full document
        """
        messages = self.CONTEXT_PROMPT.format_messages(document=document, chunk=chunk)
        response = self.llm.invoke(messages)
        return remove_thinking_from_message(response.content)
    
    def create_chunks(self, document: Document) -> List [Document]: 
        chunks = self.text_splitter.split_documents([document])
        if not self.config.preprocessing.CONTEXTUALIZE_CHUNKS:
            return chunks
        contextual_chunks = [ ]
        for chunk in chunks:
            context = self.generate_context(document.page_content, chunk.page_content)
            chunk_with_context = f"{context}\n\n{chunk.page_content}"
            contextual_chunks.append(Document (page_content=chunk_with_context, metadata=chunk.metadata))
        return contextual_chunks

    def save_vector_store(self,voctor_db: InMemoryVectorStore, vector_db_path: Path):
        """
        Save the data to the database
        Args:
            voctor_db (InMemoryVectorStore): The vector store
            vector_db_path (Path): The path to save the vector store
        """
        voctor_db.dump(vector_db_path)

    def save_document(self, documents: List[Document], document_path: Path):
        """
        Save the document to the database
        Args:
            documents (List[Document]): The list of documents to save
        """
        with open(document_path, "wb") as f:
            pickle.dump(documents, f)

    def load_vector_store(self, vector_db_path: Path) -> InMemoryVectorStore:
        """
        Load the vectore data from the database
        Args:
            vector_db_path (Path): The path to load the vector store
        Returns:
            InMemoryVectorStore: The vector store
            if not exists then return empty vector store
        """
        if os.path.exists(vector_db_path):
            return InMemoryVectorStore.load(vector_db_path, self.embedding_model)
        return InMemoryVectorStore(self.embedding_model)
    
    def load_document(self, document_path: Path) -> List[Document]:
        """
        Load the document from the database
        Args:
            document_path (Path): The path to load the document
        Returns:
            List[Document]: The list of documents
        """
        if os.path.exists(document_path):
            with open(document_path, "rb") as f:
                return pickle.load(f)
        return [ ]
    
    def create_embeddings(
        self, chunks: List[Document],
        concate_vector_store: InMemoryVectorStore,
        isconcate: bool = True
    ) -> tuple[InMemoryVectorStore, InMemoryVectorStore]:
        """
        Create the embeddings for the chunks
        Args:
            chunks (List[Document]): The chunks of documents
            concate_vector_store (InMemoryVectorStore): previous vector store
            isconcate (bool): If True then add new documents to the previous vector store
        Returns:
            tuple[InMemoryVectorStore, InMemoryVectorStore]: new vector store and concate vector store
        """
        BATCH_SIZE = self.config.preprocessing.BATCH_SIZE
        # initialize the vector store
        vector_store = InMemoryVectorStore(self.embedding_model)
        for batch in tqdm(range(0, len(chunks), BATCH_SIZE)):
            batch_chunks = chunks[batch:batch + BATCH_SIZE]
            vector_store.add_documents(documents=batch_chunks)
            if isconcate:
                concate_vector_store.add_documents(documents=batch_chunks)
        return (vector_store, concate_vector_store)
            


        
    def create_vector_store(self, files: List[File], isconcate:bool=True):
        """
        Create the vector store for the files
        Args:
            files (List[File]): The list of files (documents) to create the vector store
            isconcate (bool): If True then add new documents to the previous vector store
        
        """
        # file data to stucture of Document data
        documents = [Document(file.content, metadata={"source": file.name}) for file in files]
        for document in documents:
            file_name = document.metadata["source"]
            logger.info(f"Processing {file_name}")
            vector_db_path = os.path.join(
                self.config.preprocessing.VECTOR_STORE_DIR,
                f"{shortuuid.uuid()}.db"
            )
            document_path = os.path.join(
                self.config.preprocessing.DOCUMENT_STORE_DIR,
                f"{file_name}.pkl"
            )
            # create chunks of the document
            chunks = self.create_chunks(document)
            # load previous vector store if exists
            concate_vector_store = self.load_vector_store(
                self.config.vector_store.CONCATENATE_VECTOR_FILE_PATH
            )
            # load previous document if exists
            if isconcate:
                concate_documents = self.load_document(self.config.preprocessing.CONCATENATE_DOCUMENT_FILE_PATH)
                concate_documents.extend(chunks)
                self.save_document(concate_documents, self.config.preprocessing.CONCATENATE_DOCUMENT_FILE_PATH)
            # create embeddings for the chunks
            vectore_store, concate_vector_store = self.create_embeddings(
                chunks,
                concate_vector_store,
                isconcate
            )
            # save the data to the database
            if isconcate:
                self.save_vector_store(concate_vector_store, self.config.vector_store.CONCATENATE_VECTOR_FILE_PATH)
            
            self.save_vector_store(vectore_store, vector_db_path)
            self.save_document(chunks, document_path)
            # insert the data to the database
            self.database.insert_data(file_name,document_path, vector_db_path)
            logger.info(f"Processed {file_name}")

    def get_retriever(self, document_path:Path, vector_db_path:Path) -> BaseRetriever:
        """
        Get the retriever
        Args:
            docid (int): The id of the document
        Returns:
            BaseRetriever: The retriever based on the given docid
        """

        vector_db = self.load_vector_store(vector_db_path)
        documents = self.load_document(document_path)
        if documents is None:
            raise ValueError("Document not found")

        semantic_retriever = vector_db.as_retriever(
            search_kwargs={
                "k": self.config.preprocessing.N_SEMANTIC_RESULTS
            }
        )
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k =  self.config.Preprocessing.N_BM25_RESULTS

        ensemble_retriever = EnsembleRetriever(
            retrievers=[semantic_retriever, bm25_retriever],
            weights=[0.6, 0.4],
        )

        logger.info("Retriever created")

        return ContextualCompressionRetriever(
            base_compressor = self.reranker,
            base_retriever=ensemble_retriever
        )