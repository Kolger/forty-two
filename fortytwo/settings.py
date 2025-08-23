import os
from dotenv import load_dotenv
load_dotenv()


class Settings:
    PROVIDER = os.environ.get('PROVIDER', 'OPENAI')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', None)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', None)
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', None)
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', None)
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', None)
    ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-pro')
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-reasoner')
    OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'openrouter/auto')
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    DB_STRING = os.environ.get('DB_STRING')
    MAX_COMPLETION_TOKENS = int(os.environ.get('MAX_COMPLETION_TOKENS', 4096))
    MAX_TOTAL_TOKENS = int(os.environ.get('MAX_TOKENS', 10000))
    SYSTEM_PROMPT = os.environ.get('SYSTEM_PROMPT', "You are friendly assistant, your name is Rick")
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-5')
    ALLOWED_USERS = os.environ.get('ALLOWED_USERS', None)
    LOG_MESSAGES = os.environ.get('LOG_MESSAGES', False)
    HISTORY_EXPIRATION = int(os.environ.get('HISTORY_EXPIRATION', 30))
    LANGUAGE = os.environ.get('LANGUAGE', 'en')
