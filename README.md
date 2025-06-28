# dc_bot
__一個具備 Gemini AI 對話能力的 Discord 機器人__

## 主要特色
- 使用 Google Gemini 1.5 Flash AI 模型進行對話 (可自行更改)
- 支援多種互動方式：指令前綴或提及（@）
- 內建上下文記憶功能，實現連貫對話
- 自動處理長回應，分段發送
- 支援網路搜尋功能，提供更準確的回答
- 可自定義機器人的回答風格和個性

## 使用方式
機器人支援兩種互動方式：

### 1. 使用前綴指令（預設使用 `!`）
- `!機器人 <問題>` - 向 Gemini 提問
- `!clear_memory` - 清除當前頻道的對話歷史

### 2. 使用提及（@）
你可以直接提及機器人來使用所有功能：
- `@機器人 <問題>` - 直接提問
- `@機器人 clear_memory` - 清除記憶

只需提及機器人而不輸入命令，機器人會提示可用的指令說明。


```

## 安裝步驟
1. 創建 `.env` 文件並添加必要的環境變數：
```env
DISCORD_TOKEN=你的Discord機器人令牌
GEMINI_API_KEY=你的Google Gemini API密鑰
LOG_LEVEL=INFO  # 可選，預設為 INFO
```

2. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

3. 運行機器人：
```bash
python discord_bot.py
```

## 注意事項
- 確保你的 Discord 機器人已開啟必要的權限（訊息讀取、發送等）
- 建議在首次使用時先測試基本功能是否正常
- 如遇到問題，可查看 `log/discord_bot.log` 檔案了解詳細錯誤信息

## 系統需求
- Python 3.8 或更高版本
- 穩定的網路連接
- Discord 機器人TOKEN
- Google Gemini API 密鑰
