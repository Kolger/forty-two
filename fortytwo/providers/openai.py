import json
import os

import aiohttp

from fortytwo.settings import Settings
from .base import BaseProvider
from .types import RequestHeaders,  AIResponse,  UniversalChatHistory
from .openai_types import OpenAIChatMessage, OpenAIImageMessage, OpenAIPayload, OpenAIAssistantMessage, OpenAIUserMessage


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key=Settings.OPENAI_API_KEY):
        self.api_key = api_key
        self.model = Settings.OPENAI_MODEL
        self.default_system_prompt = Settings.SYSTEM_PROMPT
        self.provider_name = "OPENAI"
        self.base_api_url = "https://api.openai.com/v1"

    async def text(self, question, chat_history: list[OpenAIChatMessage] = (), system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self.__prepare_payload(text=question, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    async def image(self, base64_images: list, question, chat_history: list[OpenAIChatMessage] = (),
                    system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self.__prepare_payload(text=question, base64_images=base64_images, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    def __prepare_headers(self):
        headers: RequestHeaders = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        return headers

    def __convert_chat_history(self, chat_history: UniversalChatHistory) -> list[OpenAIChatMessage]:
        converted_chat_history = []

        for message in chat_history:
            if message['role'] == "user":
                user_message: OpenAIUserMessage = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message['content']['text']
                        }
                    ]
                }

                if message['content']['images']:
                    for image in message['content']['images']:
                        user_message['content'].append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image}"}
                        })

                converted_chat_history.append(user_message)

            elif message['role'] == "assistant":
                assistant_message: OpenAIAssistantMessage = {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": message['content']['text']
                        }
                    ]
                }

                converted_chat_history.append(assistant_message)

        return converted_chat_history

    def __prepare_payload(self, text, base64_images=(), chat_history: list = (),
                          system_prompt: str = None) -> OpenAIPayload:
        if not system_prompt:
            system_prompt = self.default_system_prompt

        pictures: list[OpenAIImageMessage] = []

        for base64_image in base64_images:
            pictures.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })

        payload: OpenAIPayload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                *self.__convert_chat_history(chat_history),
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

    async def __make_request(self, headers: RequestHeaders, payload: OpenAIPayload) -> AIResponse:
        url = f'{self.base_api_url}/chat/completions'
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.post(url, headers=headers, data=json.dumps(payload)) as resp:
                response = await resp.json()

                try:
                    ai_response = AIResponse(
                        content=response['choices'][0]['message']['content'],
                        completion_tokens=response['usage']['completion_tokens'],
                        prompt_tokens=response['usage']['prompt_tokens'],
                        total_tokens=response['usage']['total_tokens'],
                        status=AIResponse.Status.OK,
                        provider=self.provider_name
                    )
                except KeyError as e:
                    ai_response = AIResponse(
                        content=f"Failed to make request to OpenAI API. Response: {response}",
                        completion_tokens=0,
                        prompt_tokens=0,
                        total_tokens=0,
                        provider=self.provider_name,
                        status=AIResponse.Status.ERROR
                    )

                return ai_response
