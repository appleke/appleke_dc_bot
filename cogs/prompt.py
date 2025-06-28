from discord.ext import commands
from loguru import logger
from typing import Optional

def get_prompt(system_prompt: str, user_nick: str, text: str, 
               personality: Optional[str] = None, 
               search_results: Optional[str] = None, 
               memory: Optional[str] = None) -> str:

    prompt = f"""
                [系統設定]
                \n{system_prompt}\n
                """

    if personality is not None:
        prompt += f"""
                    \n[個性設定]
                    \n{personality}\n
                    """
        
    if memory is not None:
        prompt += f"""
                    \n[歷史對話] （最舊的在上，最新的在下）
                    \n{memory}\n
                    """
    
    if search_results is not None:
        prompt += f"""
                    \n[搜尋結果]
                    \n{search_results}\n
                    """

    prompt += f"""
                \n[使用者輸入]
                \n{user_nick}：{text}
                """
    return prompt

# 為了符合 Discord.py 擴展要求，添加一個空的 Cog 類和 setup 函數
class PromptCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PromptCog 已初始化")

async def setup(bot):
    await bot.add_cog(PromptCog(bot))
    logger.info("PromptCog 已設置完成")