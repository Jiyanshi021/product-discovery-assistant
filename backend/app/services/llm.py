# app/services/llm.py
from typing import List

from groq import Groq
from openai import OpenAI

from app.core.config import settings

groq_client = Groq(api_key=settings.GROQ_API_KEY)
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _build_prompt(question: str, chunks: List[str]) -> str:
    context = "\n\n---\n\n".join(chunks)
    return (
        "You are an AI fashion stylist. You must recommend outfits ONLY using the "
        "products listed in the context below.\n\n"
        "Rules:\n"
        "- Always try to suggest 2–4 suitable products from the context.\n"
        "- If the user's request cannot be matched exactly (e.g. they ask for hoodies "
        "but there are only sweatshirts or shorts), recommend the closest alternatives "
        "and clearly say they are similar options, not perfect matches.\n"
        "- Do NOT say “I don't know” as long as there is at least one product in the context. "
        "Only say you don't know if the context is completely empty.\n"
        "- Keep the answer short and focused on why these products match the user's request.\n\n"
        f"Context:\n{context}\n\n"
        f"User query: {question}\n\n"
        "Now give a short, friendly recommendation:"
    )

def answer_with_rag(question: str, chunks: List[str]) -> str:
    """
    Call Llama 3.1-8B-Instant on Groq first, fallback to GPT-4.1 if needed.
    """
    prompt = _build_prompt(question, chunks)

    # Primary: Groq (Llama 3.1-8B-Instant)
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception:
        # Fallback: OpenAI GPT-4.1
        resp = openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content
