import os
import re
import json
import discord
from typing import Optional
from loguru import logger
from discord.ext import commands
from cogs.gemini_api import GeminiAPI
from cogs.memory import get_memory, save_memory
from config.config import ConfigManager

PROJECT_ROOT = os.getcwd()
PERSONALITY_FOLDER = os.path.join(PROJECT_ROOT, "assets/data/personality")
os.makedirs(PERSONALITY_FOLDER, exist_ok=True)

def get_prompt(system_prompt: str, user_nick: str, text: str, 
               personality: Optional[str] = None, 
               search_results: Optional[str] = None, 
               memory: Optional[str] = None) -> str:
    """構建提示詞"""
    prompt = system_prompt or ""
    
    if personality:
        prompt += f"\n\n{personality}"
    
    if memory:
        prompt += f"\n\n### 對話歷史：\n{memory}"
    
    if search_results:
        prompt += f"\n\n### 參考資料：\n{search_results}"
    
    prompt += f"\n\n### 使用者 {user_nick}：\n{text}\n\n### 你的回應："
    
    return prompt

def google_search(query: str) -> str:
    """模擬搜索功能，實際應用中需要實現真正的搜索"""
    # 此處應該實現實際的搜索功能
    logger.info(f"執行搜索: {query}")
    return f"關於「{query}」的搜索結果將顯示在這裡。"

def get_channel_name(channel) -> str:
    """安全地獲取頻道名稱，處理不同類型的頻道"""
    if hasattr(channel, "name"):
        return channel.name
    elif isinstance(channel, discord.DMChannel):
        return "私人訊息"
    else:
        return f"頻道 {channel.id}"

class LLMService(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = ConfigManager()
        
        self.system_prompt = self.config.bot_config.get("system_prompt", "")
        self.personality = self.config.bot_config.get("personality", "")
        self.gpt_api = self.config.bot_config.get("gpt_api", "gemini")
        self.model = self.config.bot_config.get("model", "gemini-1.5-flash")
        self.chat_memory = self.config.bot_config.get("chat_memory", False)
        self.use_search_engine = self.config.bot_config.get("use_search_engine", False)
        
        # 初始化 Gemini API
        self.gpt = GeminiAPI(self.model)
        logger.info(f"功能 {self.__class__.__name__} 初始化載入成功！")

    def get_response(self, chanel_id: int, user_nick: str, text: str, 
                    search_results: Optional[str] = None, 
                    memory: Optional[str] = None) -> str:
        """獲取 LLM 回應"""
        # 檢查是否有頻道專屬的個性
        file_path = os.path.join(PERSONALITY_FOLDER, f"{chanel_id}.json")
        personality = self.personality
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8-sig") as file:
                    data = json.load(file)
                    channel_personality = data.get("personality")
                    if channel_personality:
                        personality = channel_personality
            except Exception as e:
                logger.error(f"讀取個性檔案時發生錯誤: {e}")
        
        # 構建提示詞
        prompt = get_prompt(self.system_prompt, user_nick, text, personality, search_results, memory)

        # 生成回應
        temperature = 0.5 if search_results else 1.0
        response = self.gpt.get_response(prompt, temperature=temperature)
        
        return response if response else "無法生成回應"

    def get_search_results(self, text: str, channel_id: Optional[int] = None) -> Optional[str]:
        """判斷是否需要搜索並獲取搜索結果"""
        if not self.use_search_engine:
            return None
            
        system_prompt = self.system_prompt or ""
        prompt = f"{system_prompt}\n\n" + """
                    請根據以下使用者輸入及對話歷史，判斷是否需要擷取網路即時資訊，並提供適合搜尋的關鍵字（若無需搜尋則回答"無"）。 
                    你的任務是：
                    1. 判斷使用者問題是否涉及即時性、最新資訊或超出通用知識範疇的主題。
                    2. 若需要搜尋，提供有效的搜尋關鍵字，並根據對話上下文調整搜尋內容。
                    3. 若不需要搜尋，回答 {"search": false, "query":"無"}。
                    """
                    
        # 添加記憶上下文
        if self.chat_memory and channel_id:
            memory_text = get_memory(channel_id)
            if memory_text:
                prompt += f"""
                        ### 對話歷史：
                        {memory_text}
                        """
                        
        # 添加用戶輸入
        prompt += f"""
                    ### 使用者輸入：
                    {text}

                    ### 輸出格式要求：
                    - 使用 JSON 格式。
                    - 範例輸出：
                    {{"search": true, "query":"2025年台灣總統選舉候選人"}}
                    {{"search": true, "query":"昨天 NBA 勇士隊比賽結果"}}
                    {{"search": false, "query":"無"}}
                    """
                    
        try:
            # 獲取模型回應
            response = self.gpt.get_response(prompt, temperature=0.5)
            if not response:
                logger.error("[LLM] 模型回應為空")
                return None
                
            # 解析 JSON
            match = re.search(r"\{.*\}", response)
            if not match:
                logger.error(f"[LLM] 無法解析模型回應: {response}")
                return None
                
            response_json = match.group(0).strip()
            response_json = response_json.replace("True", "true").replace("False", "false")
            
            result = json.loads(response_json)
            if "search" not in result or "query" not in result:
                logger.error(f"[LLM] 模型回應格式無效: {result}")
                return None
                
            # 執行搜索
            if result["search"] and result["query"]:
                query = result["query"]
                search_results = google_search(query)
                return search_results
                
            return None
            
        except Exception as e:
            logger.error(f"[LLM] 搜索處理時發生錯誤: {e}")
            return None

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context) -> None:
        """顯示機器人的所有可用命令和功能說明"""
        prefix = self.bot.command_prefix
        if callable(prefix):
            prefix = "!"  # 使用預設前綴作為顯示
        
        # 創建一個 Discord Embed 來顯示幫助信息
        embed = discord.Embed(
            title="🤖 機器人使用指南",
            description="你可以使用以下兩種方式與我互動：\n1. 使用指令前綴 `!`\n2. 直接提及（@）我\n\n以下是所有可用的命令：",
            color=discord.Color.blue()
        )
        
        # 聊天功能
        embed.add_field(
            name="💬 聊天功能",
            value=(
                f"`{prefix}YTC <問題>` - 向 AI 提問\n"
                f"或是直接提及我：`@機器人 <問題>`"
            ),
            inline=False
        )
        
        # 記憶相關命令
        memory_commands = [
            f"`{prefix}clear_memory` - 清除當前頻道的對話歷史",
            f"`{prefix}show_memory` - 顯示當前的對話歷史"
        ]
        embed.add_field(
            name="🧠 記憶相關",
            value="\n".join(memory_commands),
            inline=False
        )
        
        # 系統設定命令
        admin_commands = [
            f"`{prefix}set_system_prompt <提示詞>` - 設定機器人的系統提示",
            f"`{prefix}set_personality <個性描述>` - 設定機器人的全局個性",
            f"`{prefix}set_channel_personality <個性描述>` - 設定當前頻道的專屬個性",
            f"`{prefix}clear_channel_personality` - 清除當前頻道的專屬個性",
            f"`{prefix}show_prompts` - 顯示當前的系統提示和個性設定"
        ]
        embed.add_field(
            name="⚙️ 系統設定",
            value="\n".join(admin_commands),
            inline=False
        )
        
        # 機器人功能說明
        features = [
            "✅ **AI 對話**：使用 Google Gemini 1.5 Flash AI 模型",
            "✅ **雙重互動**：支援指令前綴和提及（@）兩種方式",
            "✅ **記憶功能**：記住對話歷史，實現連貫對話",
            "✅ **個性設定**：可為機器人設定全局或頻道專屬的個性",
            "✅ **智能搜索**：問題涉及最新資訊時會自動搜索"
        ]
        embed.add_field(
            name="🌟 特色功能",
            value="\n".join(features),
            inline=False
        )
        
        
        await ctx.send(embed=embed)

    @commands.command(name="set_system_prompt")
    async def set_system_prompt(self, ctx: commands.Context, *, prompt: str) -> None:
        """設定機器人的系統提示
        
        用法: !set_system_prompt 你是一個友善的助手，請用繁體中文回答問題
        """
        # 更新記憶體中的系統提示
        self.system_prompt = prompt
        
        # 更新配置文件
        config_path = os.path.join(PROJECT_ROOT, "config", "bot_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            config_data["system_prompt"] = prompt
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
                
            await ctx.send(f"✅ 系統提示已更新為：\n```\n{prompt}\n```")
            logger.info(f"系統提示已更新，使用者：{ctx.author.name}，新提示：{prompt}")
        except Exception as e:
            await ctx.send(f"❌ 更新系統提示時發生錯誤：{str(e)}")
            logger.error(f"更新系統提示失敗：{e}")

    @commands.command(name="set_personality")
    async def set_personality(self, ctx: commands.Context, *, personality: str) -> None:
        """設定機器人的全局個性
        
        用法: !set_personality 你是一個幽默風趣的助手，喜歡用生動的比喻來解釋複雜概念
        """
        # 更新記憶體中的個性
        self.personality = personality
        
        # 更新配置文件
        config_path = os.path.join(PROJECT_ROOT, "config", "bot_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            config_data["personality"] = personality
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
                
            await ctx.send(f"✅ 全局個性已更新為：\n```\n{personality}\n```")
            logger.info(f"全局個性已更新，使用者：{ctx.author.name}，新個性：{personality}")
        except Exception as e:
            await ctx.send(f"❌ 更新全局個性時發生錯誤：{str(e)}")
            logger.error(f"更新全局個性失敗：{e}")

    @commands.command(name="set_channel_personality")
    async def set_channel_personality(self, ctx: commands.Context, *, personality: str) -> None:
        """設定當前頻道的專屬個性
        
        用法: !set_channel_personality 在這個頻道中，你是一個專業的程式設計教師
        """
        channel_id = ctx.channel.id
        channel_name = get_channel_name(ctx.channel)
        file_path = os.path.join(PERSONALITY_FOLDER, f"{channel_id}.json")
        
        try:
            # 確保目錄存在
            os.makedirs(PERSONALITY_FOLDER, exist_ok=True)
            
            # 寫入頻道專屬個性
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"personality": personality}, f, ensure_ascii=False, indent=4)
                
            await ctx.send(f"✅ 已為頻道 `{channel_name}` 設定專屬個性：\n```\n{personality}\n```")
            logger.info(f"頻道個性已更新，頻道：{channel_name}，ID：{channel_id}，新個性：{personality}")
        except Exception as e:
            await ctx.send(f"❌ 設定頻道個性時發生錯誤：{str(e)}")
            logger.error(f"設定頻道個性失敗：{e}")

    @commands.command(name="show_prompts")
    async def show_prompts(self, ctx: commands.Context) -> None:
        """顯示當前的系統提示和個性設定"""
        # 獲取系統提示
        system_prompt = self.system_prompt or "未設定"
        
        # 獲取全局個性
        global_personality = self.personality or "未設定"
        
        # 獲取頻道個性
        channel_id = ctx.channel.id
        channel_name = get_channel_name(ctx.channel)
        file_path = os.path.join(PERSONALITY_FOLDER, f"{channel_id}.json")
        channel_personality = "未設定"
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8-sig") as file:
                    data = json.load(file)
                    if data.get("personality"):
                        channel_personality = data["personality"]
            except Exception as e:
                logger.error(f"讀取頻道個性時發生錯誤: {e}")
        
        # 構建回應
        embed = discord.Embed(
            title="機器人提示設定",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="系統提示",
            value=f"```\n{system_prompt}\n```",
            inline=False
        )
        
        embed.add_field(
            name="全局個性",
            value=f"```\n{global_personality}\n```",
            inline=False
        )
        
        embed.add_field(
            name=f"頻道 `{channel_name}` 專屬個性",
            value=f"```\n{channel_personality}\n```",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="clear_channel_personality")
    async def clear_channel_personality(self, ctx: commands.Context) -> None:
        """清除當前頻道的專屬個性設定"""
        channel_id = ctx.channel.id
        channel_name = get_channel_name(ctx.channel)
        file_path = os.path.join(PERSONALITY_FOLDER, f"{channel_id}.json")
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                await ctx.send(f"✅ 已清除頻道 `{channel_name}` 的專屬個性設定")
                logger.info(f"已清除頻道個性，頻道：{channel_name}，ID：{channel_id}")
            except Exception as e:
                await ctx.send(f"❌ 清除頻道個性時發生錯誤：{str(e)}")
                logger.error(f"清除頻道個性失敗：{e}")
        else:
            await ctx.send(f"ℹ️ 頻道 `{channel_name}` 沒有專屬個性設定")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """當命令未定義時，觸發LLM事件"""
        if not isinstance(error, commands.CommandNotFound):
            raise error
            
        # 獲取用戶輸入
        user_input = ctx.message.content[len(ctx.prefix):].strip()
        if not user_input:
            return
            
        async with ctx.typing():
            # 基本資訊
            channel_id = ctx.channel.id
            user_nick = ctx.author.display_name
            guild_id = ctx.guild.id if ctx.guild else 'DM'
            
            # 獲取搜索結果
            search_results = None
            if self.use_search_engine:
                search_results = self.get_search_results(user_input, channel_id)
            
            # 獲取記憶
            memory = None
            if self.chat_memory:
                memory = get_memory(channel_id)
            
            # 生成回應
            response = self.get_response(channel_id, user_nick, user_input, search_results, memory)
            
            # 保存記憶
            if self.chat_memory and response:
                search_results_str = search_results if search_results is not None else ""
                save_memory(channel_id, user_nick, user_input, search_results_str, response)
            
            # 記錄日誌
            if response:
                logger.info(f"[LLM] 伺服器 ID: {guild_id}, 使用者: {ctx.author.name}, 輸入: {user_input[:50]}..., 輸出: {response[:50]}...")
                
                # 發送回應
                response_str = str(response) if response is not None else "無回應"
                
                # 確保 response_str 不為 None 再使用 len()
                if response_str and len(response_str) > 1900:
                    chunks = [response_str[i:i+1900] for i in range(0, len(response_str), 1900)]
                    for chunk in chunks:
                        await ctx.send(chunk)
                else:
                    await ctx.send(response_str)
            else:
                logger.error(f"[LLM] 無法生成回應，伺服器 ID: {guild_id}, 使用者: {ctx.author.name}, 輸入: {user_input[:50]}...")
                await ctx.send("抱歉..我無法處理這個訊息。")

    @commands.command(name="YTC")
    async def ytc_command(self, ctx: commands.Context, *, prompt: str) -> None:
        """向 Gemini 提問（具有上下文記憶）
        
        用法: !YTC 你好，請介紹一下自己
        """
        async with ctx.typing():
            # 基本資訊
            channel_id = ctx.channel.id
            user_nick = ctx.author.display_name
            guild_id = ctx.guild.id if ctx.guild else 'DM'
            
            # 獲取搜索結果
            search_results = None
            if self.use_search_engine:
                search_results = self.get_search_results(prompt, channel_id)
            
            # 獲取記憶
            memory = None
            if self.chat_memory:
                memory = get_memory(channel_id)
            
            # 生成回應
            response = self.get_response(channel_id, user_nick, prompt, search_results, memory)
            
            # 檢查回應是否有效
            if not response:
                error_msg = "無法生成回應"
                logger.error(f"[LLM] {error_msg}，伺服器 ID: {guild_id}, 使用者: {ctx.author.name}, 輸入: {prompt[:50]}...")
                await ctx.send(f"抱歉，我遇到了一些問題：{error_msg}")
                return
                
            # 檢查是否為錯誤回應
            if response.startswith("[Gemini 錯誤]"):
                logger.error(f"[LLM] {response}，伺服器 ID: {guild_id}, 使用者: {ctx.author.name}, 輸入: {prompt[:50]}...")
                await ctx.send(f"抱歉，我遇到了一些問題：{response}")
                return
            
            # 保存記憶
            if self.chat_memory:
                search_results_str = search_results if search_results is not None else ""
                save_memory(channel_id, user_nick, prompt, search_results_str, response)
            
            # 記錄日誌
            logger.info(f"[LLM] 伺服器 ID: {guild_id}, 使用者: {ctx.author.name}, 輸入: {prompt[:50]}..., 輸出: {response[:50]}...")
            
            # 分段發送長回應
            if len(response) > 1900:
                chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(response)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LLMService(bot)) 