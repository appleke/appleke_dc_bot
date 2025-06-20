import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from cogs.gemini_api import ask_gemini




load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
client = discord.Client(intents = intents)
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 已登入：{bot.user}")


# 一開始bot開機需載入全部程式檔案
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")


@bot.command()
async def test_bot(ctx, *, prompt: str):
    """對 Gemini 提問"""
    await ctx.send("💬 Gemini 正在思考中...")
    response = ask_gemini(prompt)
    await ctx.send(response[:1900])  # Discord 字數限制是 2000
    

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# 確定執行此py檔才會執行
if __name__ == "__main__":
    asyncio.run(main())