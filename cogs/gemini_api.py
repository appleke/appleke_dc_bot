import os
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from loguru import logger

# 環境變數設定，降低 Gemini API 的日誌輸出
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["GLOG_minloglevel"] = "3"

class GeminiAPI():
    def __init__(self, model='gemini-1.5-flash'):
        self.model = model
        self.api_key = os.getenv('GEMINI_API_KEY', None)
        genai.configure(api_key=self.api_key)
        logger.info(f"Gemini API 已初始化，使用模型: {self.model}")

    def get_response(self, prompt, temperature=0.7):
        """獲取 Gemini 回應"""
        try:
            model = genai.GenerativeModel(self.model)
            generation_config = GenerationConfig(temperature=temperature)
            response = model.generate_content(
                prompt, 
                generation_config=generation_config,
                safety_settings='BLOCK_NONE'
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API 錯誤: {str(e)}")
            return f"[Gemini 錯誤] {str(e)}"