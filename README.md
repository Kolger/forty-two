Forty-two is a Telegram bot that allows you to create your own ChatGPT in Telegram.

## Features

- East to use and deploy. You have to just set Telegram and OpenAI API keys and run the bot.
- GPT Vision. You can send images to bot and ask questions about them.
- Track your conversation history for GPT.
- Fully asynchronous.
- MIT License.

## Settings


| Variable                | Description                    | Default Value                                   |
|-------------------------|--------------------------------|-------------------------------------------------|
| `TELEGRAM_API_KEY`      | Telegram API key.              | -                                               |
| `OPENAI_API_KEY`        | OpenAI API key.                | -                                               |
| `DB_STRING`             | Database connection string.    | sqlite+aiosqlite:///db.sqlite3                  |
| `MAX_COMPLETION_TOKENS` | Maximum tokens for completion. | 4096                                            |
| `MAX_TOTAL_TOKENS`      | Maximum tokens for total.      | 10000                                           |
| `SYSTEM_PROMPT`         | System prompt for GPT.         | "You are friendly assistant, your name is Rick" |
| `OPENAI_MODEL`          | OpenAI model.                  | "gpt-4o"                                        |


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Made with love in Barcelona
