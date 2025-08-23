from langchain_chroma.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi import status, HTTPException
from config import DATABASE_PATH


template_prompt = """
    Responda a pergunta do usúario: {question}.
    Somente com base nessas informações : {knowledge_base}.
    """


def question(user_question: str, model_name: str):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    db = Chroma(persist_directory=DATABASE_PATH, embedding_function=embeddings)

    results = db.similarity_search_with_relevance_scores(user_question, k=3)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Low relevance score: {results[0][1]}",
        )

    result_texts = [doc.page_content for doc, score in results]

    knowledge_base = "\n\n----\n\n".join(result_texts)
    prompt_template = ChatPromptTemplate.from_template(template_prompt)
    prompt = prompt_template.invoke(
        {"question": user_question, "knowledge_base": knowledge_base}
    )

    llm = ChatGoogleGenerativeAI(model=model_name)
    text_response = llm.invoke(prompt).content

    return text_response
