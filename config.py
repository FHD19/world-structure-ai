"""
配置文件 — 世界结构认知AI
"""
import os

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-eecce14798e24b76987aa1b5d835874d")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# 系统提示词文件路径
SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "world_structure_ai_prompt.md")

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 新闻源说明（实际抓取逻辑见 news_fetcher.py）
# 目前使用的源: 百度新闻、36氪、财联社
# 均为国内可直接访问的源

# Flask配置
FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("PORT", 5000))
