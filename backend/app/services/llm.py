# app/services/llm.py
from typing import List, Optional
import logging

from groq import Groq
from openai import OpenAI, RateLimitError, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize clients
groq_client = Groq(api_key=settings.GROQ_API_KEY)
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

PRIMARY_MODEL = "llama-3.1-8b-instant"  # 🚀 fastest, cheaper, works great
FALLBACK_MODEL = "gpt-4.1-mini"        # light fallback


def _build_prompt(question: str, chunks: List[str]) -> str:
    # Limit context to avoid oversized input
    context = "\n\n---\n\n".join(chunks[:40])
    return (
        "You are an AI fashion stylist. You must recommend outfits ONLY using the "
        "products listed in the context below.\n\n"
        "Rules:\n"
        "- Suggest 2–4 suitable products from the context.\n"
        "- If no exact match exists, recommend closest alternatives.\n"
        "- Never say 'I don't know' if there are products in context.\n"
        "- Keep the message short.\n\n"
        f"Context:\n{context}\n\n"
        f"User query: {question}\n\n"
        "Now give a short, friendly recommendation:"
    )


def answer_with_rag(question: str, chunks: List[str]) -> Optional[str]:
    if not chunks:
        return None

    prompt = _build_prompt(question, chunks)

    # 🔹 First: Try Groq Instant model
    try:
        logger.info("🧠 Using Groq — llama-3.1-8b-instant")
        resp = groq_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful fashion stylist."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,  # required for Groq API
        )
        return resp.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"⚠️ Groq failed! Switching to OpenAI: {e}")

    # 🔹 Then: fallback only if Groq failed
    try:
        logger.info("🪂 Using OpenAI fallback — GPT-4.1-mini")
        resp = openai_client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()

    except RateLimitError as e:
        logger.warning(f"OpenAI quota exceeded: {e}")
        return (
            "I'm unable to generate the full recommendation right now — "
            "but these products match your request!"
        )

    except APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return (
            "Model response failed — but you can still explore the suggested products!"
        )

    except Exception as e:
        logger.error(f"Unexpected LLM error: {e}")
        return "I'm having trouble responding right now."
