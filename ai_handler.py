import os
from google import genai
from google.genai import types # Tizim ko'rsatmalari uchun kerak
from dotenv import load_dotenv

load_dotenv()

class AIHandler:
    def __init__(self):
        # API kalitini .env dan yuklash
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Siz xohlagan model (Gemini 3 Flash - eng yangi va tekin limitli model)
        self.model_id = "gemini-3-flash-preview" 

    async def get_answer(self, question: str, entries: list) -> str:
        # Bilimlar bazasini matnga aylantirish
        knowledge = ""
        for i, entry in enumerate(entries, 1):
            knowledge += f"\n--- {i}. {entry['content']}\n"

        # Tizim ko'rsatmasi (System Instruction)
        # Yangi SDKda buni config qismida berish juda qulay
        system_instruction = """Sen O'zbekiston fuqarolariga huquqiy masalalar bo'yicha yordam beruvchi Advokat Bot assistentisan.
Faqat Bilimlar Bazasidagi ma'lumotlarga asoslanib javob ber. 
Agar ma'lumot bo'lmasa: 'Kechirasiz, bu mavzu bo'yicha bazamizda ma'lumot yo'q' deb javob ber.
Javobni aniq va faqat O'zbek tilida yoz."""

        user_prompt = f"Bilimlar Bazasi:\n{knowledge}\n\nFuqaroning savoli: {question}"

        try:
            # Yangi SDK formati bo'yicha so'rov yuborish
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1 # Huquqiy aniqlik uchun kreativlikni kamaytiramiz
                )
            )
            return response.text
        except Exception as e:
            return f"⚠️ Xatolik yuz berdi: {str(e)}"