import json
import os

import aiohttp

from fortytwo.settings import Settings
from .base import BaseProvider
from .types import RequestHeaders, AIResponse, UniversalChatHistory
from .anthropic_types import AnthropicRequestHeaders


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key=Settings.ANTHROPIC_API_KEY):
        self.api_key = api_key
        self.model = Settings.ANTHROPIC_MODEL
        self.default_system_prompt = Settings.SYSTEM_PROMPT

    async def text(self, question, chat_history: UniversalChatHistory = (), system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self._prepare_payload(text=question, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    async def image(self, base64_images: list, question, chat_history: UniversalChatHistory = (),
                    system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self._prepare_payload(text=question, base64_images=base64_images, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    def __prepare_headers(self) -> AnthropicRequestHeaders:
        headers: AnthropicRequestHeaders = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        return headers

    def _convert_chat_history(self, chat_history: UniversalChatHistory) -> list:
        converted_chat_history = []

        for message in chat_history:
            if message['role'] == "user":
                text = message['content']['text']

                if len(message['content']['images']) > 0 and (text is None or text == ''):
                    # Anthropic requires a text prompt when processing images
                    text = "Process the image(s)"

                user_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }

                if message['content']['images']:
                    for image in message['content']['images']:
                        image_data = {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image
                            }
                        }
                        user_message['content'].append(image_data)

                converted_chat_history.append(user_message)

            elif message['role'] == "assistant":
                assistant_message = {
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

    def _prepare_payload(self, text: str, base64_images=(), chat_history: UniversalChatHistory = None, system_prompt: str = None) -> dict:
        chat_history = self._convert_chat_history(chat_history)

        pictures: list[dict] = []

        for base64_image in base64_images:
            pictures.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64_image
                }
            })

        if len(base64_images) > 0 and (text is None or text == ''):
            # Anthropic requires a text prompt when processing images
            text = "Process the image(s)"

        payload = {
            "model": self.model,
            "system": system_prompt or self.default_system_prompt,
            "messages": [
                *chat_history,
                {
                    "role": "user",
                    "content": [
                        *pictures,
                        {"type": "text", "text": f"{text}", }
                    ]
                }
            ],
            "max_tokens": Settings.MAX_COMPLETION_TOKENS,
        }

        return payload

    async def __make_request(self, headers: AnthropicRequestHeaders, payload: dict) -> AIResponse:
        api_url = "https://api.anthropic.com/v1/messages"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                response_data = await response.json()
                try:
                    return AIResponse(
                        status=AIResponse.Status.OK,
                        content=response_data['content'][0]['text'],
                        total_tokens=response_data['usage']['input_tokens'] + response_data['usage']['output_tokens'],
                        completion_tokens=response_data['usage']['output_tokens'],
                        prompt_tokens=response_data['usage']['input_tokens'],
                        provider='ANTHROPIC'
                    )
                except KeyError as e:
                    return AIResponse(
                        status=AIResponse.Status.ERROR,
                        content=f"Failed to make request to Anthropic API. Response: {response_data}",
                        completion_tokens=0,
                        prompt_tokens=0,
                        total_tokens=0,
                        provider='ANTHROPIC'
                    )
