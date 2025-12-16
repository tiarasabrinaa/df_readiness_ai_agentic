# services/llm_service.py
import httpx
import json
from typing import Dict, Any, Optional, List
from config.settings import settings
import logging

from google import genai
from google.genai import types
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.url = settings.LLM_URL
        self.token = settings.LLM_TOKEN
        self.model = settings.LLM_MODEL
        
        self.token_fallback_gemini = settings.FALLBACK_LLM_KEY_GEMINI
        self.token_fallback_openai = settings.FALLBACK_LLM_KEY_OPENAI
        
    async def call_llm(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Try LLMs in cascade:
        1. Primary LLM
        2. Gemini fallback
        3. OpenAI fallback
        """
        
        # === TRY PRIMARY LLM ===
        try:
            result = await self._call_primary_llm(messages, max_tokens, temperature)
            
            # Check if result looks like an error
            if not self._is_error_response(result):
                return result
            
            logger.warning("Primary LLM returned error response, trying Gemini")
            
        except Exception as e:
            logger.error(f"Primary LLM failed with exception: {e}")
        
        # === TRY GEMINI FALLBACK ===
        try:
            result = await self._call_gemini_fallback(messages)
            
            # Check if result looks like an error
            if not self._is_error_response(result):
                return result
            
            logger.warning("Gemini returned error response, trying OpenAI")
            
        except Exception as e:
            logger.error(f"Gemini fallback failed with exception: {e}")
        
        # === TRY OPENAI FALLBACK ===
        try:
            result = await self._call_openai_fallback(messages)
            return result
            
        except Exception as e:
            logger.error(f"OpenAI fallback also failed: {e}")
            return "Maaf, semua sistem AI sedang tidak tersedia. Silakan coba lagi nanti."


    async def _call_primary_llm(self, messages: list, max_tokens: int, temperature: float) -> str:
        """Call primary LLM API"""
        payload = {
            "model": self.model,
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.8,
            "top_k": 20,
            "presence_penalty": 1.5,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Authorization": f"Bearer {self.token}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"API Error {response.status_code}: {response.text}")
                raise Exception(f"API Error {response.status_code}")
            
            data = response.json()
            
            if choices := data.get('choices'):
                if message := choices[0].get('message'):
                    if content := message.get('content', '').strip():
                        return content
            
            logger.error(f"Unexpected response structure: {data.keys()}")
            raise Exception("Unexpected response structure")

    async def _call_gemini_fallback(self, messages: list) -> str:
        """Call Gemini as fallback"""
        try:
            client = genai.Client(api_key=self.token_fallback_gemini)
            
            gemini_contents = []
            system_instruction = None
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_instruction = msg['content']
                    continue
                
                role = 'model' if msg['role'] == 'assistant' else 'user'
                gemini_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg['content'])]
                    )
                )
            
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                system_instruction=system_instruction
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_contents,
                config=config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Fallback LLM also failed: {e}", exc_info=True)
            return "Maaf, sistem AI sedang tidak tersedia. Silakan coba lagi nanti."

    async def _call_openai_fallback(self, messages: list) -> str:
        """Call OpenAI as another fallback"""
        try:
            openai_client = OpenAI(api_key=self.token_fallback_openai)
            
            formatted_messages = [
                {"role": msg["role"], "content": msg["content"]} for msg in messages
            ]
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=formatted_messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            if response.choices:
                return response.choices[0].message.content.strip()
            
            logger.error("OpenAI returned empty choices")
            raise Exception("OpenAI returned empty response")
            
        except Exception as e:
            logger.error(f"OpenAI Fallback LLM also failed: {e}", exc_info=True)
            return "Maaf, sistem AI sedang tidak tersedia. Silakan coba lagi nanti."

    def _is_error_response(self, text: str) -> bool:
        """Check if response text is an error message"""
        error_indicators = [
            "maaf, terjadi masalah",
            "error",
            "timeout",
            "tidak ada respons",
            "kesalahan sistem"
        ]
        return any(indicator in text.lower() for indicator in error_indicators)
    
    async def generate_response(self, prompt: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Generate response based on prompt and conversation history
        """
        messages = []
        
        # Add system message with the prompt
        messages.append({
            "role": "system", 
            "content": prompt
        })
        
        # Add conversation history if provided
        if conversation_history:
            # Take last 8 messages to avoid token limit and ensure context
            recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
            messages.extend(recent_history)
            
            # If no recent user message, add a generic prompt
            if not any(msg.get('role') == 'user' for msg in recent_history[-2:]):
                messages.append({
                    "role": "user",
                    "content": "Lanjutkan percakapan assessment dan ajukan pertanyaan berikutnya."
                })
        else:
            # If no conversation history, add initial user message
            messages.append({
                "role": "user",
                "content": "Mulai assessment digital forensics readiness."
            })
        
        logger.info(f"Generating response with {len(messages)} messages")
        return await self.call_llm(messages, max_tokens=1500, temperature=0.7)
    
# Create global instance
llm_service = LLMService()