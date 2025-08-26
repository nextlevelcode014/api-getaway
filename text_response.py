from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi import status, HTTPException
from knowledge_base import get_client_db
from utils.config_dependencies import count_tokens
from typing import Any, Dict


template_prompt = """
    Responda a pergunta do usúario: {question}.
    Somente com base nessas informações : {knowledge_base}.
    """


def question(
    client_id: str,
    user_question: str,
    model_name: str,
) -> Dict[str, Any]:
    db = get_client_db(client_id, model_name)

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

    prompt_text = (
        str(prompt.to_string()) if hasattr(prompt, "to_string") else str(prompt)
    )
    input_tokens = count_tokens(prompt_text, model_name)

    llm = ChatGoogleGenerativeAI(model=model_name)
    response = llm.invoke(prompt)
    text_response = response.content

    output_tokens = count_tokens(text_response, model_name)
    total_tokens = input_tokens + output_tokens

    return {
        "response": text_response,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
        "model": model_name,
        "client_id": client_id,
    }
