import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import date

from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationError,
    AIRateLimitError,
    AITemporaryServerError
)
from app.services.gemini_service import SALES_AGENT_PROMPT, CALL_SUMMARY_PROMPT

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        self.model_name = settings.GROQ_MODEL or "qwen/qwen3.8-27b"
        self.is_rate_limited = False
        self.last_error = ""

    def update_api_key(self, api_key: str, model_name: Optional[str] = None):
        self.api_key = api_key.strip()
        if model_name:
            self.model_name = model_name
        self.is_rate_limited = False
        self.last_error = ""

    def is_configured(self) -> bool:
        if not self.api_key:
            self.api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        return bool(self.api_key and self.api_key.strip())

    def _clean_and_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            cleaned = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except Exception:
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
        return None

    def _classify_and_raise(self, error: Exception):
        """Inspects error and raises the corresponding AIException"""
        from groq import (
            AuthenticationError,
            RateLimitError,
            InternalServerError,
            APIConnectionError,
            APIStatusError
        )
        err_str = str(error).lower()
        status_code = getattr(error, "status_code", None)

        if (
            isinstance(error, AuthenticationError)
            or status_code == 401
            or "invalid_api_key" in err_str
            or "invalid api key" in err_str
            or "unauthorized" in err_str
        ):
            self.last_error = f"Authentication Failed (401): {error}"
            raise AIConfigurationError(
                f"Groq API Authentication Error: Invalid or expired API key. {error}",
                provider="groq"
            )

        if (
            isinstance(error, RateLimitError)
            or status_code == 429
            or "429" in err_str
            or "rate limit" in err_str
            or "quota" in err_str
            or "tokens per minute" in err_str
        ):
            self.is_rate_limited = True
            self.last_error = f"Rate Limit Exceeded (429): {error}"
            raise AIRateLimitError(
                f"Groq Rate Limit Exceeded (429): {error}",
                provider="groq"
            )

        if (
            isinstance(error, (InternalServerError, APIConnectionError))
            or status_code in [500, 502, 503, 504]
            or any(s in err_str for s in ["500", "502", "503", "504", "bad gateway", "service unavailable", "gateway timeout", "internal server error", "timeout", "timed out", "connection error", "network error"])
        ):
            self.last_error = f"Temporary Server Error: {error}"
            raise AITemporaryServerError(
                f"Groq Upstream Temporary Server Error ({status_code or '5xx'}): {error}",
                provider="groq"
            )

        # For any unexpected exception
        self.last_error = f"Groq Error: {error}"
        raise error

    async def generate_voice_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_context: str,
        customer_profile: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Executes voice dialogue, lead extraction, qualification, and sentiment analysis via Groq.
        """
        if not self.is_configured():
            raise AIConfigurationError("Groq API key is not configured.", provider="groq")

        from groq import Groq

        today_str = date.today().isoformat()
        formatted_history = ""
        for msg in (conversation_history or [])[-8:]:
            role = msg.get("sender") or msg.get("role", "user")
            text = msg.get("text") or msg.get("content", "")
            formatted_history += f"{role.upper()}: {text}\n"

        prompt_filled = SALES_AGENT_PROMPT.format(today_date=today_str)
        user_prompt = f"""COMPANY KNOWLEDGE BASE RETRIEVED CONTEXT:
\"\"\"{rag_context or 'Standard enterprise sales offerings apply.'}\"\"\"

EXISTING CUSTOMER PROFILE COLLECTED SO FAR:
{json.dumps(customer_profile or {}, indent=2)}

LANGUAGE MODE:
{"Hindi (Respond naturally in Hindi)" if language == "hi" else "English"}

CONVERSATION TRANSCRIPT SO FAR:
{formatted_history}
CUSTOMER JUST SAID: "{user_message}"

Generate the required JSON output:
"""

        try:
            import asyncio
            client = Groq(api_key=self.api_key.strip(), timeout=4.0)
            loop = asyncio.get_running_loop()
            completion = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": prompt_filled},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.4,
                        response_format={"type": "json_object"}
                    )
                ),
                timeout=4.0
            )
            raw_text = completion.choices[0].message.content or ""
            data = self._clean_and_parse_json(raw_text)
            if data and "reply_text" in data:
                data["engine_mode"] = "live_groq"
                data["provider"] = "groq"
                self.is_rate_limited = False
                return data
            raise ValueError(f"Groq response did not contain valid JSON schema: {raw_text[:120]}")
        except asyncio.TimeoutError:
            self.last_error = "Groq request timed out after 4 seconds."
            raise AITemporaryServerError("Groq request timed out (4s).", provider="groq")
        except Exception as e:
            err_str = str(e).lower()
            if ("model_not_found" in err_str or "does not exist" in err_str) and self.model_name != "qwen/qwen3.8-27b":
                logger.warning(f"Groq model {self.model_name} unavailable; retrying with verified model qwen/qwen3.8-27b")
                self.model_name = "qwen/qwen3.8-27b"
                return await self.generate_voice_response(user_message, conversation_history, rag_context, customer_profile, language)
            self._classify_and_raise(e)

    async def generate_call_summary(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates post-call executive summary, objection evaluation, and next action via Groq.
        """
        if not self.is_configured():
            raise AIConfigurationError("Groq API key is not configured.", provider="groq")

        from groq import Groq

        transcript = ""
        for m in messages:
            sender = m.get("sender", "unknown")
            text = m.get("text", "")
            transcript += f"[{sender.upper()}]: {text}\n"

        prompt = CALL_SUMMARY_PROMPT.format(transcript=transcript)

        try:
            client = Groq(api_key=self.api_key.strip(), timeout=5.0)
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an Executive Sales Analyst AI. Respond strictly in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw_text = completion.choices[0].message.content or ""
            data = self._clean_and_parse_json(raw_text)
            if data and "summary" in data:
                data["engine_mode"] = "live_groq"
                data["provider"] = "groq"
                return data
            raise ValueError(f"Groq summary response could not be parsed: {raw_text[:120]}")
        except Exception as e:
            err_str = str(e).lower()
            if ("model_not_found" in err_str or "does not exist" in err_str) and self.model_name != "qwen/qwen3.8-27b":
                logger.warning(f"Groq summary model {self.model_name} unavailable; retrying with verified model qwen/qwen3.8-27b")
                self.model_name = "qwen/qwen3.8-27b"
                return await self.generate_call_summary(messages, customer_profile)
            self._classify_and_raise(e)

    def test_connection(self, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Synchronously tests Groq connection and model availability"""
        test_key = (api_key or self.api_key or settings.GROQ_API_KEY).strip()
        test_model = (model or self.model_name or settings.GROQ_MODEL or "qwen/qwen3.8-27b").strip()

        if not test_key:
            return {
                "success": False,
                "provider": "groq",
                "message": "Groq API key is not configured."
            }

        try:
            from groq import Groq
            client = Groq(api_key=test_key)
            completion = client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": "Respond with 'Groq connected' in two words."}],
                max_tokens=10
            )
            content = completion.choices[0].message.content or "Groq connected"
            self.update_api_key(test_key, test_model)
            return {
                "success": True,
                "provider": "groq",
                "message": f"Successfully verified live Groq API connection ({test_model})!",
                "response": content.strip(),
                "model": test_model
            }
        except Exception as e:
            self._classify_and_raise(e)


groq_service = GroqService()
