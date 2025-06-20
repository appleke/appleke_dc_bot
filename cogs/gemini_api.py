import google.generativeai as genai
import os
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


model = genai.GenerativeModel("gemini-1.5-flash")

class GeminiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def ask_gemini(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"[Gemini 錯誤] {e}"
async def setup(bot):
    await bot.add_cog(GeminiCog(bot))    
