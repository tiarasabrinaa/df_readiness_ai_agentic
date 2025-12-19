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
logger.setLevel(logging.DEBUG)

class LLMService:
    def __init__(self):
        self.url = "https://llm.rokade.id/v1/chat/completions"
        self.token = "8q27r8ADo8yaqaINYaty4w8tyai"
        self.model = "Qwen/Qwen2.5-7B-Instruct-AWQ"
        logger.info(f"LLMService initialized with URL: {self.url}, Model: {self.model}")
        
        self.token_fallback_gemini = settings.FALLBACK_LLM_KEY_GEMINI
        self.token_fallback_openai = settings.FALLBACK_LLM_KEY_OPENAI
        
        # DEBUG: Log configuration (mask sensitive data)
        logger.info(f"LLM Config - URL: {self.url}")
        logger.info(f"LLM Config - Model: {self.model}")
        logger.info(f"LLM Config - Token: {'***' + self.token[-4:] if self.token and len(self.token) > 4 else 'NOT SET'}")
        
        # Validate primary LLM configuration
        if not self.url or not self.url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid or missing LLM_URL: {self.url}. Primary LLM will be skipped.")
            self.url = None
        
        if not self.token:
            logger.error("LLM_TOKEN is not set!")
        
        if not self.model:
            logger.error("LLM_MODEL is not set!")
        
    async def call_llm(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Try LLMs in cascade:
        1. Primary LLM (required)
        2. Gemini fallback (optional)
        3. OpenAI fallback (optional)
        """
        
        # === TRY PRIMARY LLM ===
        if self.url:
            try:
                result = await self._call_primary_llm(messages, max_tokens, temperature)
                
                # Check if result looks like an error
                if not self._is_error_response(result):
                    logger.info("Primary LLM succeeded")
                    return result
                
                logger.warning("Primary LLM returned error response, trying fallback")
                
            except Exception as e:
                logger.error(f"Primary LLM failed with exception: {e}")
        else:
            logger.error("Primary LLM not configured")
            return "Error: Primary LLM tidak dikonfigurasi dengan benar. Periksa LLM_URL, LLM_TOKEN, dan LLM_MODEL."
        
        # === TRY GEMINI FALLBACK (only if configured) ===
        if self.token_fallback_gemini and len(self.token_fallback_gemini) > 20:
            try:
                result = await self._call_gemini_fallback(messages)
                
                if not self._is_error_response(result):
                    logger.info("Gemini fallback succeeded")
                    return result
                
                logger.warning("Gemini returned error response")
                
            except Exception as e:
                logger.error(f"Gemini fallback failed: {e}")
        else:
            logger.info("Gemini fallback not configured, skipping")
        
        # === TRY OPENAI FALLBACK (only if configured) ===
        if self.token_fallback_openai and len(self.token_fallback_openai) > 20:
            try:
                result = await self._call_openai_fallback(messages)
                logger.info("OpenAI fallback succeeded")
                return result
                
            except Exception as e:
                logger.error(f"OpenAI fallback failed: {e}")
        else:
            logger.info("OpenAI fallback not configured, skipping")
        
        # All failed
        return "Maaf, sistem AI sedang tidak tersedia. Silakan coba lagi nanti."


    async def _call_primary_llm(self, messages: list, max_tokens: int, temperature: float) -> str:
        """Call primary LLM API"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.8,
            "top_k": 20,
            "max_tokens": max_tokens,  # FIXED: Added max_tokens
            "presence_penalty": 1.5,
            "chat_template_kwargs": {"enable_thinking": False},  # FIXED: Added this
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        logger.info(f"Calling primary LLM at {self.url} with model {self.model}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.url, json=payload, headers=headers)
            
            # Log response for debugging
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 401:
                logger.error(f"401 Response body: {response.text}")
                raise Exception(f"API Auth Error 401 - Token invalid or expired")
            
            if response.status_code != 200:
                logger.error(f"API Error {response.status_code}: {response.text}")
                raise Exception(f"API Error {response.status_code}")
            
            data = response.json()
            
            # Check for error in response body (even if status is 200)
            if 'error' in data:
                logger.error(f"API returned error in body: {data['error']}")
                raise Exception(f"API Error: {data['error']}")
            
            if choices := data.get('choices'):
                if message := choices[0].get('message'):
                    if content := message.get('content', '').strip():
                        # Validate content is meaningful
                        if len(content) < 10:
                            logger.error(f"Primary LLM returned too short response: {content}")
                            raise Exception("Response too short")
                        
                        logger.info(f"Primary LLM returned {len(content)} characters")
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
            logger.error(f"Gemini fallback failed: {e}", exc_info=True)
            raise  # Re-raise to trigger next fallback

    async def _call_openai_fallback(self, messages: list) -> str:
        """Call OpenAI as another fallback"""
        try:
            # Validate API key first
            if not self.token_fallback_openai or len(self.token_fallback_openai) < 20:
                logger.error("OpenAI API key not configured or invalid")
                raise Exception("OpenAI API key not configured")
            
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
            logger.error(f"OpenAI fallback failed: {e}", exc_info=True)
            raise  # Re-raise to show final error

    def _is_error_response(self, text: str) -> bool:
        """Check if response text is an error message"""
        if not text or len(text.strip()) < 10:  # Too short to be valid
            return True
            
        error_indicators = [
            "maaf, terjadi masalah",
            "error",
            "timeout",
            "tidak ada respons",
            "kesalahan sistem",
            "tidak tersedia"
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