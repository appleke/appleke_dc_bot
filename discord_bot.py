import os
import json
import asyncio
import discord
import sys
from dotenv import load_dotenv
from discord.ext import commands
from loguru import logger
from typing import cast

from config.config import ConfigManager

# 載入設定檔
config = ConfigManager()

# 載入環境變數
load_dotenv(override=True)
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logger.error("錯誤: 找不到 DISCORD_TOKEN 環境變數，請確認 .env 檔案中有設定此變數")
    sys.exit(1)

# 在這裡我們已經確認 TOKEN 不是 None
assert TOKEN is not None  # type: ignore

# 確保 TOKEN 是字串類型
TOKEN = cast(str, TOKEN)

# 設定系統日誌
log_path = "./log/discord_bot.log"
level = os.getenv("LOG_LEVEL", "INFO")
logger.add(log_path, level=level, format="{time} | {level} | {message}", rotation="10 MB")

# 機器初始化設定
intents = discord.Intents.default()
intents.messages = True
intents.members = True
intents.message_content = True

# 自定義前綴檢查函數
def get_prefix(bot, message):
    # 返回預設前綴和提及作為可能的前綴
    return commands.when_mentioned_or(config.bot_config['prefix'])(bot, message)

# 使用自定義前綴函數初始化機器人
bot = commands.Bot(command_prefix=get_prefix, help_command=None, intents=intents)

status_dict = {
    'online': discord.Status.online,
    'idle': discord.Status.idle,
    'dnd': discord.Status.dnd,
    'invisible': discord.Status.invisible
}

@bot.event
async def on_ready():
    logger.info(f"✅ 已登入：{bot.user}")
    game = discord.Game(config.bot_config['activity'])
    await bot.tree.sync()
    await bot.change_presence(status=status_dict[config.bot_config['status']], activity=game)
    
    # 打印所有已加載的 cogs
    logger.info(f"已加載的 cogs: {list(bot.cogs.keys())}")
    
    # 顯示可用的命令
    commands_list = [f"!{command.name}" for command in bot.commands]
    logger.info(f"可用命令: {', '.join(commands_list)}")
    
    # 檢查 Memory cog 是否已加載
    memory_cog = bot.get_cog("Memory")
    if memory_cog:
        logger.info("✅ Memory cog 已成功加載")
    else:
        logger.warning("❌ Memory cog 未加載")

@bot.event
async def on_message(message):
    # 忽略機器人自己的消息
    if message.author == bot.user:
        return

    # 檢查消息是否提及機器人，並確保 bot.user 不為 None
    if bot.user and bot.user in message.mentions:
        # 移除消息中的提及部分，獲取實際命令內容
        content = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        
        # 如果消息只有提及而沒有其他內容，可以添加預設回應
        if not content:
            await message.channel.send(f'你好！你可以用 `{config.bot_config["prefix"]}help` 或直接提及我來使用命令。')
            return

    # 繼續處理命令
    await bot.process_commands(message)

# 載入功能
async def load_extensions():
    all_cogs = os.listdir("./cogs")
    
    # 優先載入
    priority_cogs = ['llm.py']
    for filename in priority_cogs:
        if filename in all_cogs:
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"已載入優先擴展: {filename}")
            except Exception as e:
                logger.error(f"載入優先擴展 {filename} 失敗: {e}")
                continue

    # 依序載入其他擴展
    for filename in all_cogs:
        if filename.endswith(".py") and filename not in priority_cogs and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"已載入擴展: {filename}")
            except Exception as e:
                logger.error(f"載入擴展 {filename} 失敗: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("關閉機器人...")
    except Exception as e:
        logger.error(f"啟動失敗: {e}")