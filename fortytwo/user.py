from fortytwo.database.models import User, Message, Picture
from fortytwo.providers.openai import OpenAIProvider
from fortytwo.providers.base import BaseProvider


async def summarize(user_id, s):
    messages = await Message.get_by_user(user_id, s)
    provider: BaseProvider = OpenAIProvider()
    chat_history = ""
    for message in messages:
        chat_history += f'Question: \n {message.message_text or ''} \n Answer: {message.answer or ''}\n\n'

    #chat_history = [{"role": "user", "content": str(chat_history)}]
    system_prompt = "Summarize this dialog for me in 1000 characters or less. Answer USING ONLY English not another language."

    summarized_dialog = await provider.text(question=chat_history, system_prompt=system_prompt)
    await Message.clear_by_user(user_id, s)
    message = Message(user=user_id, message_text="What we've discussed earlier?", answer=str(summarized_dialog))
    s.add(message)
    await s.commit()

    return str(summarized_dialog)
