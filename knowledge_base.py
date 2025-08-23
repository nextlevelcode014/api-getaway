from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

base = "base"


def create_db():
    documents = load_documents()
    chunks = splitter_chunks(documents)
    vetorize_chunks(chunks)


def load_documents():
    loader = PyPDFDirectoryLoader(base)
    return loader.load()


def splitter_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=500, length_function=len, add_start_index=True
    )

    return splitter.split_documents(documents)


def vetorize_chunks(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    Chroma.from_documents(chunks, embeddings, persist_directory="database")
    print("Database created")


create_db()
