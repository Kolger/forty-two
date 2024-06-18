from .base import BaseProvider
import os
import base64
import json
import aiohttp
import asyncio
import random
from fortytwo.settings import Settings
from .types import UserSchema, AssistantSchema, SystemSchema, ChatMessageSchema, AIResponse


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key=Settings.OPENAI_API_KEY):
        self.api_key = api_key
        self.model = Settings.OPENAI_MODEL
        self.default_system_prompt = Settings.SYSTEM_PROMPT

    async def text(self, question, chat_history: list[ChatMessageSchema] = (), system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self.__prepare_payload(text=question, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    async def image(self, base64_images: list, question="What’s in this image?", chat_history: list[ChatMessageSchema] = (),
                    system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self.__prepare_payload(text=question, base64_images=base64_images, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    def __prepare_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}"
        }

        return headers

    def __prepare_payload(self, text, base64_images=(), chat_history=(), system_prompt=None):
        if not system_prompt:
            system_prompt = self.default_system_prompt

        pictures = []

        for base64_image in base64_images:
            pictures.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                *chat_history,
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        },
                        *pictures
                    ]
                }
            ],
            "max_tokens": Settings.MAX_COMPLETION_TOKENS
        }

        return payload

    async def __make_request(self, headers, payload) -> AIResponse:
        url = 'https://api.openai.com/v1/chat/completions'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=json.dumps(payload)) as resp:
                response = await resp.json()

                ai_response = AIResponse(
                    content=response['choices'][0]['message']['content'],
                    completion_tokens=response['usage']['completion_tokens'],
                    prompt_tokens=response['usage']['prompt_tokens'],
                    total_tokens=response['usage']['total_tokens']
                )
                return ai_response