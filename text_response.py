from langchain_chroma.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from config import DATABASE_PATH


template_prompt = """
    Responda a pergunta do usúario: {quetion}.
    Somente com base nessas informações : {knowledge_base}.
    """


def quetion(user_quetion, model):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    db = Chroma(persist_directory=DATABASE_PATH, embedding_function=embeddings)

    results = db.similarity_search_with_relevance_scores(user_quetion, k=3)

    if len(results) == 0 or results[0][1] < 0.7:
        print(f"Score muito baixo: {results[0][1]}")
        return {"error": "Score muito baixo"}

    reult_texts = []
    for result in results:
        text = result[0].page_content
        reult_texts.append(text)

    knowledge_base = "\n\n----\n\n".join(reult_texts)
    prompt = ChatPromptTemplate.from_template(template_prompt)
    prompt = prompt.invoke({"quetion": user_quetion, "knowledge_base": knowledge_base})

    model = ChatGoogleGenerativeAI(model=model)
    text_response = model.invoke(prompt).content

    return text_response
