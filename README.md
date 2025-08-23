Forty-two is a Telegram bot that allows you to create your own ChatGPT in Telegram with OpenAI GPT, Google Gemini, Anthropic Claude, DeepSeek, and OpenRouter models.

## Features

- Easy to use and deploy. You just need to set the Telegram and OpenAI/Gemini/Anthropic/DeepSeek/OpenRouter API keys and run the bot.
- Switching between different AI providers with saving the correspondence history.
- Ask another AI provider for a response to the same question.
- GPT Vision. You can send images to the bot and ask questions about them.
- Track your conversation history with GPT.
- Limit users who can interact with the bot.
- Log user messages to a file and the console.
- i18n for system messages. Currently, supports English, Spanish, Catalan and Russian.
- Fully asynchronous.
- MIT License.

## Setup

### 1. Create a .env file with the following content:

```
TELEGRAM_TOKEN=your_telegram_api_key
OPENAI_API_KEY=your_openai_api_key

# and / or
# GEMINI_API_KEY=your_gemini_api_key
# ANTHROPIC_API_KEY=your_anthropic_api_key
# DEEPSEEK_API_KEY=your_deepseek_api_key
# OPENROUTER_API_KEY=your_openrouter_api_key
```

### 2. Run the bot

With docker-compose:

```bash
docker-compose up -d
```

Run without Docker: 

```bash
uv sync
alembic upgrade head
python main.py
```

## Settings

| Variable              | Description                                                                                                                                                                             | Default Value                                   |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|
| TELEGRAM_TOKEN        | Telegram API key.                                                                                                                                                                       | -                                               |
| OPENAI_API_KEY        | OpenAI API key.                                                                                                                                                                         | -                                               |
| GEMINI_API_KEY        | Google Gemini API key.                                                                                                                                                                  | -                                               |
| ANTHROPIC_API_KEY     | Anthropic API key.                                                                                                                                                                      | -                                               |
| DEEPSEEK_API_KEY      | DeepSeek API key.                                                                                                                                                                       | -                                               |
| OPENROUTER_API_KEY    | OpenRouter API key.                                                                                                                                                                     | -                                               |
| PROVIDER              | Default provider for users. Users then can change their default provider with /provider command. Please note that API_KEY for selected provider is required.                            | OPENAI                                          |
| DB_STRING             | Database connection string.                                                                                                                                                             | sqlite+aiosqlite:///db.sqlite3                  |
| MAX_COMPLETION_TOKENS | Maximum tokens for completion.                                                                                                                                                          | 4096                                            |
| MAX_TOTAL_TOKENS      | Maximum tokens for total output. If AI provider uses more than this amount, the bot will summarize user input.                                                                          | 10000                                           |
| SYSTEM_PROMPT         | System prompt for GPT.                                                                                                                                                                  | You are a friendly assistant, your name is Rick |
| OPENAI_MODEL          | OpenAI model.                                                                                                                                                                           | gpt-5                                           |
| ANTHROPIC_MODEL       | Anthropic model.                                                                                                                                                                        | claude-sonnet-4-20250514                        |
| GEMINI_MODEL          | Gemini model.                                                                                                                                                                           | gemini-2.5-pro                                  |
| DEEPSEEK_MODEL        | DeepSeek model.                                                                                                                                                                         | deepseek-reasoner                               |
| OPENROUTER_MODEL      | OpenRouter model (see OpenRouter model IDs).                                                                                                                                            | openrouter/auto                                  |
| ALLOWED_USERS         | Comma-separated list of Telegram users who can interact with the bot. You can use both Telegram IDs or Usernames. If None, everyone can interact with the bot. Example: durov,238373289 | None                                            |
| LOG_MESSAGES          | Log user messages to a file and the console.                                                                                                                                            | False                                           |
| HISTORY_EXPIRATION    | If the last message from a user occurred more than the specified time in minutes, the message history will be reset.                                                                    | 30                                              |
| LANGUAGE              | Language for bot system messages. Curretly support en, es, ca, ru.                                                                                                                      | en                                              |

## Obtaining API keys

- [Telegram API key](https://core.telegram.org/bots#6-botfather)
- [OpenAI API key](https://beta.openai.com/signup/)
- [Gemini API key](https://ai.google.dev/gemini-api)
- [Anthropic API key](https://console.anthropic.com/dashboard)
- [DeepSeek API key](https://platform.deepseek.com/api_keys)
- [OpenRouter API key](https://openrouter.ai/)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Made with love in Barcelona
