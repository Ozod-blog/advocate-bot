import sys
import os
import logging
from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from bot.config.config import load_config

logger = logging.getLogger(__name__)
config = load_config()

openai_client = OpenAI(
    base_url=config.openai_base_url,
    api_key=config.openai_token
)

async def get_ai_response(prompt):
    try:
        logger.info(f"Sending request to AI with prompt: {prompt[:50]}...")
        
        completion = openai_client.chat.completions.create(
            model="anthropic/claude-3-sonnet",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        logger.info("Successfully received response from AI")
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in AI response: {str(e)}")
        return f"Xatolik yuz berdi: {str(e)}"

async def summarize_text(text, max_length=500):
    try:
        prompt = f"Quyidagi matnni ixcham tarzda qisqartiring (maksimum {max_length} belgi): {text}"
        return await get_ai_response(prompt)
    except Exception as e:
        logger.error(f"Error summarizing text: {str(e)}")
        return text[:max_length] + "..."

async def translate_to_uzbek(text):
    try:
        prompt = f"Quyidagi matnni o'zbek tiliga tarjima qiling: {text}"
        return await get_ai_response(prompt)
    except Exception as e:
        logger.error(f"Error translating text: {str(e)}")
        return text

async def answer_question(question, context=None):
    try:
        if context:
            prompt = f"Quyidagi kontekst asosida savolga javob bering:\n\nKontekst: {context}\n\nSavol: {question}"
        else:
            prompt = question
        
        return await get_ai_response(prompt)
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        return f"Savolingizga javob berishda xatolik yuz berdi: {str(e)}" 