from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi import status, HTTPException
from sqlalchemy.orm import Session
from knowledge_base import get_client_db
from typing import Any, Dict
from model.db import Model
import tiktoken


template_prompt = """
    Responda a pergunta do usúario: {question}.
    Somente com base nessas informações : {knowledge_base}.
    """


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    try:
        if "gemini" in model_name.lower:
            return len(text) // 4

        encoding = tiktoken.encoding_for_model(model_name)
        return len(encoding(text))
    except Exception:
        return len(text.split()) * 1.3


def calculate_cost(
    prompt_tokens: int, completion_tokens: int, model_name: str, session: Session
) -> float:
    model = session.query(Model).filter(Model.model_name == model_name).first()

    prompt_cost = (prompt_tokens / 1000) * model.value_per_token
    completion_cost = (completion_tokens / 1000) * model.value_per_token

    return prompt_cost + completion_cost


def question(
    client_id: str,
    user_question: str,
    model_name: str,
) -> Dict[str, Any]:
    db = get_client_db(client_id)

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
    prompt_tokens = count_tokens(prompt_text, model_name)

    llm = ChatGoogleGenerativeAI(model=model_name)
    response = llm.invoke(prompt)
    text_response = response.content

    completion_tokens = count_tokens(text_response, model_name)
    total_tokens = prompt_tokens + completion_tokens

    return {
        "response": text_response,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "model": model_name,
        "client_id": client_id,
    }
