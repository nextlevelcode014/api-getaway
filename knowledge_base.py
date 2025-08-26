from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = "base"
VECTOR_DIR = "vectorstores"


def create_db(client_id: str, model_type: str):
    documents = load_documents(client_id)
    chunks = splitter_chunks(documents)
    return vetorize_chunks(chunks, client_id, model_type)


def load_documents(client_id: str):
    loader = PyPDFDirectoryLoader(f"{BASE_DIR}/{client_id}")
    return loader.load()


def splitter_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=500, length_function=len, add_start_index=True
    )
    return splitter.split_documents(documents)


def vetorize_chunks(chunks, client_id: str, model_type: str):
    if model_type.startswith("gemini-"):
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    elif model_type.startswith("gpt-"):
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    else:
        return None

    try:
        persist_dir = f"{VECTOR_DIR}/{client_id}"
        db = Chroma.from_documents(chunks, embeddings, persist_directory=persist_dir)

        print(f"Database created for client {client_id} at {persist_dir}")
        return db
    except Exception as e:
        print(f"Error creating DB for client {client_id}: {e}")
        return None


def get_client_db(client_id: str, model_type: str):
    persist_dir = f"{VECTOR_DIR}/{client_id}"

    if not os.path.exists(persist_dir):
        print(f"Knowledgebase for client {client_id} not found.")
        return None

    if model_type.startswith("gemini-"):
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    elif model_type.startswith("gpt-"):
        embeddings = OpenAIEmbeddings("text-embedding-3-small")
    else:
        return None

    try:
        db = Chroma(persist_directory=persist_dir, embedding_function=embeddings)

        if not db._collection.count():
            print(f"Knowledgebase for client {client_id} is empty.")
            return None

        print(f"Knowledgebase loaded for client {client_id}.")
        return db

    except Exception as e:
        print(f"Error loading DB for client {client_id}: {e}")
        return None
