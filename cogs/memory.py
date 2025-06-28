import os
import json
import datetime
from loguru import logger
from discord.ext import commands
from collections import defaultdict, deque
import time

MEMORY_PATH = "assets/data/memory"
os.makedirs(MEMORY_PATH, exist_ok=True)

def get_memory(channel_id, num_memories=5):
    file_path = os.path.join(MEMORY_PATH, f"{channel_id}.json")
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            memories = json.load(f)
            memories = memories[-num_memories:] if memories else []
            memory_str = ""
            for memory in memories:
                memory_str += f"使用者：{memory['使用者']}\n"
                memory_str += f"使用者輸入：{memory['使用者輸入']}\n"
                if memory['參考資料']:
                    memory_str += f"參考資料：{memory['參考資料']}\n"
                memory_str += f"機器人回覆：{memory['機器人回覆']}\n"
                memory_str += f"時間：{memory['時間']}\n\n"
            return memory_str

    except Exception as e:
        logger.error(f"[記憶] 讀取時發生錯誤: {e}")
        return None

def save_memory(channel_id, user_nick, user_input, search_results, response, max_memories=100):
    file_path = os.path.join(MEMORY_PATH, f"{channel_id}.json")
    memories = []
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                memories = json.load(f)
        except Exception as e:
            logger.error(f"[記憶] 讀取時發生錯誤: {e}")
    
    # 紀錄記憶
    new_memory = {
        "使用者": user_nick,
        "使用者輸入": user_input,
        "參考資料": search_results,
        "機器人回覆": response,
        "時間": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    memories.append(new_memory)
    
    # 只保留最新的 max_memories 筆資料
    if len(memories) > max_memories:
        memories = memories[-max_memories:]
    
    # 儲存記憶
    try:
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[記憶] 儲存失敗: {e}")

class Memory(commands.Cog, name="Memory"):
    def __init__(self, bot):
        self.bot = bot
        # 使用者對話歷史（暫存在記憶體中）
        self.conversation_history = defaultdict(lambda: defaultdict(lambda: deque(maxlen=20)))
        logger.info("Memory cog 已初始化")
        logger.info(f"記憶檔案將儲存在: {os.path.abspath(MEMORY_PATH)}")

    def add_message(self, user_id, channel_id, role, content):
        """添加一條消息到對話歷史（記憶體和檔案）"""
        try:
            # 確保 role 是 Gemini API 支持的格式 (user 或 model)
            if role == "assistant":
                role = "model"
                
            # 添加到記憶體中的暫存
            message = {
                "role": role,
                "parts": [{"text": content}],
                "timestamp": time.time()
            }
            
            self.conversation_history[user_id][channel_id].append(message)
            
            # 如果是模型回應，則保存到檔案中
            if role == "model":
                # 獲取對話歷史中的上一條用戶消息
                user_messages = [msg for msg in self.conversation_history[user_id][channel_id] if msg["role"] == "user"]
                if user_messages:
                    last_user_message = user_messages[-1]["parts"][0]["text"]
                    user_nick = self.get_user_nick(user_id)
                    save_memory(channel_id, user_nick, last_user_message, "", content)
            
            logger.info(f"已添加消息到歷史: user_id={user_id}, channel_id={channel_id}, role={role}, 內容長度={len(content)}")
        except Exception as e:
            logger.error(f"添加消息失敗: {e}")
            import traceback
            traceback.print_exc()

    def get_user_nick(self, user_id):
        """獲取用戶的暱稱，如果找不到則返回 ID"""
        try:
            user = self.bot.get_user(user_id)
            return user.display_name if user else f"User_{user_id}"
        except Exception as e:
            logger.error(f"獲取用戶暱稱失敗: {e}")
            return f"User_{user_id}"

    def get_conversation_context(self, user_id, channel_id):
        """獲取用戶的對話上下文，格式為 Gemini API 所需的格式"""
        try:
            # 從記憶體中獲取對話歷史
            history = list(self.conversation_history[user_id][channel_id])
            logger.info(f"從記憶體獲取歷史記錄: user_id={user_id}, channel_id={channel_id}, 記錄數={len(history)}")
            
            if not history:
                # 如果記憶體中沒有歷史記錄，嘗試從檔案中加載
                file_memory = get_memory(channel_id)
                if file_memory:
                    logger.info(f"從檔案中加載了記憶: channel_id={channel_id}, 長度={len(file_memory)}")
                    # 將檔案記憶添加為系統消息
                    return [{
                        "role": "model",
                        "parts": [{"text": "以下是之前的對話記錄，請參考：\n\n" + file_memory}]
                    }]
                else:
                    logger.info("沒有歷史記錄，返回空列表")
                    return []
                
            # 格式化為 Gemini API 需要的格式
            formatted_context = []
            for msg in history:
                if "role" in msg and "parts" in msg and len(msg["parts"]) > 0:
                    formatted_msg = {
                        "role": msg["role"],
                        "parts": msg["parts"]
                    }
                    formatted_context.append(formatted_msg)
            
            logger.info(f"返回格式化上下文，長度: {len(formatted_context)}")
            return formatted_context
        except Exception as e:
            logger.error(f"獲取對話上下文失敗: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def clear_user_history(self, user_id, channel_id=None):
        """清除特定用戶的對話歷史"""
        try:
            # 清除記憶體中的歷史
            if channel_id:
                if user_id in self.conversation_history and channel_id in self.conversation_history[user_id]:
                    self.conversation_history[user_id][channel_id].clear()
                    logger.info(f"已清除用戶 {user_id} 在頻道 {channel_id} 的記憶體歷史記錄")
                
                # 清除檔案中的歷史
                file_path = os.path.join(MEMORY_PATH, f"{channel_id}.json")
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"已刪除頻道 {channel_id} 的檔案歷史記錄: {file_path}")
                    except Exception as e:
                        logger.error(f"刪除檔案失敗: {e}")
            else:
                if user_id in self.conversation_history:
                    self.conversation_history[user_id].clear()
                    logger.info(f"已清除用戶 {user_id} 的所有記憶體歷史記錄")
            return True
        except Exception as e:
            logger.error(f"清除用戶歷史時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False

    @commands.command()
    async def clear_memory(self, ctx):
        """清除與機器人的對話歷史"""
        success = self.clear_user_history(ctx.author.id, ctx.channel.id)
        if success:
            await ctx.send("✅ 已清除您在此頻道的對話歷史")
        else:
            await ctx.send("❌ 清除對話歷史時發生錯誤，請查看控制台日誌")

    @commands.command()
    async def show_memory(self, ctx):
        """顯示當前的對話歷史（用於調試）"""
        try:
            # 顯示記憶體中的歷史
            memory_history = list(self.conversation_history[ctx.author.id][ctx.channel.id])
            
            # 顯示檔案中的歷史
            file_memory = get_memory(ctx.channel.id)
            
            if not memory_history and not file_memory:
                await ctx.send("您在此頻道沒有對話歷史")
                return
            
            if memory_history:
                await ctx.send(f"記憶體中有 {len(memory_history)} 條對話歷史：")
                for i, msg in enumerate(memory_history):
                    content = msg["parts"][0]["text"] if msg["parts"] else "空內容"
                    await ctx.send(f"{i+1}. {msg['role']}: {content[:100]}..." if len(content) > 100 else f"{i+1}. {msg['role']}: {content}")
            
            if file_memory:
                await ctx.send("檔案中的對話歷史：")
                # 分段發送，每段最多 1900 字符
                for i in range(0, len(file_memory), 1900):
                    chunk = file_memory[i:i+1900]
                    await ctx.send(chunk)
        except Exception as e:
            await ctx.send(f"❌ 顯示記憶時發生錯誤: {str(e)}")
            logger.error(f"顯示記憶時發生錯誤: {e}")
            import traceback
            traceback.print_exc()

    @commands.command()
    async def debug_memory_path(self, ctx):
        """顯示記憶檔案路徑（用於調試）"""
        try:
            file_path = os.path.join(MEMORY_PATH, f"{ctx.channel.id}.json")
            await ctx.send(f"記憶檔案路徑: {file_path}")
            
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                await ctx.send(f"檔案存在，大小: {size} 字節")
            else:
                await ctx.send("檔案不存在")
                
            await ctx.send(f"記憶目錄: {MEMORY_PATH}")
            if os.path.exists(MEMORY_PATH):
                files = os.listdir(MEMORY_PATH)
                await ctx.send(f"目錄中的檔案: {', '.join(files) if files else '無'}")
            else:
                await ctx.send("記憶目錄不存在")
        except Exception as e:
            await ctx.send(f"❌ 調試記憶路徑時發生錯誤: {str(e)}")
            logger.error(f"調試記憶路徑時發生錯誤: {e}")
            import traceback
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(Memory(bot))
    logger.info("Memory cog 已設置完成") 