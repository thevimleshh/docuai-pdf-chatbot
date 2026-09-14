
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:4b"


def ask_ai(question: str, context: str) -> str:

    prompt = f"""
You are a professional PDF document assistant.

Your task is to answer the user's question using ONLY the information
available in the document context.

IMPORTANT RULES:

1. Give a complete and meaningful answer.
2. Do not answer with only a name, word, or short phrase.
3. If the answer is a person's name, college name, company name,
   place name, etc., include it in a complete sentence.
4. Explain the answer briefly when the document provides enough information.
5. Do not invent or assume information that is not present in the document.
6. If the answer is not available in the document, clearly say:
   "The information is not available in the uploaded document."
7. If the user asks in Hindi, answer in Hindi.
8. If the user asks in English, answer in English.
9. Keep the answer clear, natural, and easy to understand.

Document Context:
{context}

User Question:
{question}

Answer:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["response"].strip()

