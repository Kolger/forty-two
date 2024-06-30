import os
from dotenv import load_dotenv
load_dotenv()


class Settings:
    PROVIDER = os.environ.get('PROVIDER', 'OPENAI')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', None)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', None)
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', None)
    ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20240620')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-1.5-flash')
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    DB_STRING = os.environ.get('DB_STRING')
    MAX_COMPLETION_TOKENS = int(os.environ.get('MAX_COMPLETION_TOKENS', 4096))
    MAX_TOTAL_TOKENS = int(os.environ.get('MAX_TOKENS', 10000))
    SYSTEM_PROMPT = os.environ.get('SYSTEM_PROMPT', "You are friendly assistant, your name is Rick")
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o')
    ALLOWED_USERS = os.environ.get('ALLOWED_USERS', None)
    LOG_MESSAGES = os.environ.get('LOG_MESSAGES', False)
    HISTORY_EXPIRATION = int(os.environ.get('HISTORY_EXPIRATION', 30))
    LANGUAGE = os.environ.get('LANGUAGE', 'en')