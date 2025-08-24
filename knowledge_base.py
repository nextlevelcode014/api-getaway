from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = "base"
VECTOR_DIR = "vectorstores"


def create_db(client_id: str):
    documents = load_documents(client_id)
    chunks = splitter_chunks(documents)
    vetorize_chunks(chunks, client_id)


def load_documents(client_id: str):
    loader = PyPDFDirectoryLoader(f"{BASE_DIR}/{client_id}")
    return loader.load()


def splitter_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=500, length_function=len, add_start_index=True
    )
    return splitter.split_documents(documents)


def vetorize_chunks(chunks, client_id: str):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    persist_dir = f"{VECTOR_DIR}/{client_id}"
    Chroma.from_documents(chunks, embeddings, persist_directory=persist_dir)
    print(f"Database created for client {client_id} at {persist_dir}")


def get_client_db(client_id: str):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    persist_dir = f"{VECTOR_DIR}/{client_id}"
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)
