import json
import os

import aiohttp

from fortytwo.settings import Settings
from .base import BaseProvider
from .types import RequestHeaders, AIResponse, UniversalChatHistory

from .gemini_types import GeminiInlineData, GeminiChatHistory, GeminiPayload, GeminiUserMessage


class GeminiProvider(BaseProvider):
    def __init__(self, api_key=Settings.GEMINI_API_KEY):
        self.api_key = api_key
        self.model = Settings.GEMINI_MODEL
        self.default_system_prompt = Settings.SYSTEM_PROMPT

    async def text(self, question, chat_history: UniversalChatHistory = (), system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self.__prepare_payload(text=question, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    async def image(self, base64_images: list, question, chat_history: UniversalChatHistory = (),
                    system_prompt=None) -> AIResponse:
        headers = self.__prepare_headers()
        payload = self.__prepare_payload(text=question, base64_images=base64_images, chat_history=chat_history, system_prompt=system_prompt)

        ai_response = await self.__make_request(headers=headers, payload=payload)

        return ai_response

    def __prepare_headers(self) -> RequestHeaders:
        headers: RequestHeaders = {
            "Content-Type": "application/json",
        }

        return headers

    def __convert_chat_history(self, chat_history: UniversalChatHistory) -> GeminiChatHistory:
        converted_chat_history: GeminiChatHistory = []

        for message in chat_history:
            if message['role'] == "user":
                user_message: GeminiUserMessage = {
                    "role": "user",
                    "parts": [
                        {
                            "text": message['content']['text']
                        }
                    ]
                }

                if message['content']['images']:
                    for image in message['content']['images']:
                        user_message['parts'].append({
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image
                            }
                        })

                converted_chat_history.append(user_message)

            elif message['role'] == "assistant":
                converted_chat_history.append({
                    "role": "model",
                    "parts": [
                        {
                            "text": message['content']['text']
                        }
                    ]
                })

        return converted_chat_history

    def __prepare_payload(self, text: str, base64_images=(), chat_history: UniversalChatHistory = (),
                          system_prompt: str = None) -> GeminiPayload:
        if not system_prompt:
            system_prompt = self.default_system_prompt

        pictures: list = []

        chat_history = self.__convert_chat_history(chat_history)

        for base64_image in base64_images:
            pictures.append({
                "inline_data": GeminiInlineData(mime_type="image/jpeg", data=base64_image)
            })

        payload: GeminiPayload = {
            "system_instruction":
            {
                "parts": [
                    {
                        "text": system_prompt
                    }
                ]
            },
            "contents": [
                *chat_history,
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": text
                        },
                        *pictures
                    ]
                },

            ],
        }

        return payload

    async def __make_request(self, headers: RequestHeaders, payload: GeminiPayload) -> AIResponse:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            async with session.post(api_url, headers=headers, data=json.dumps(payload)) as response:
                response_json = await response.json()

                if response.status != 200:
                    return AIResponse(
                        content=f"Failed to make request to Gemini API. Status code: {response.status}. Response: {response_json}",
                        completion_tokens=0,
                        prompt_tokens=0,
                        total_tokens=0,
                        status=AIResponse.Status.ERROR,
                        provider="GEMINI"
                    )
                try:
                    return AIResponse(
                        content=response_json['candidates'][0]['content']['parts'][0]['text'],
                        completion_tokens=response_json['usageMetadata']['candidatesTokenCount'],
                        prompt_tokens=response_json['usageMetadata']['promptTokenCount'],
                        total_tokens=response_json['usageMetadata']['totalTokenCount'],
                        provider="GEMINI",
                   )
                except KeyError as e:
                    return AIResponse(
                        content=f"Failed to parse Gemini API response. Response: {response_json}. Error: {e}",
                        completion_tokens=0,
                        prompt_tokens=0,
                        total_tokens=0,
                        status=AIResponse.Status.ERROR,
                        provider="GEMINI"
                    )