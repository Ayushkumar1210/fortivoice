import logging
from typing import Dict, Any, List, Optional
from datetime import date

from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationError,
    AIRateLimitError,
    AITemporaryServerError
)
from app.services.gemini_service import gemini_service
from app.services.groq_service import groq_service

logger = logging.getLogger(__name__)

class AIService:
    """
    Unified AI Orchestrator implementing Automatic Gemini -> Groq -> Local Demo Fallback.
    
    Priority:
    1. PRIMARY: Google Gemini AI
    2. SECONDARY: Groq AI (Llama 3.3 70B / Llama 3.1 8B)
    3. FINAL FALLBACK: Local Heuristic Demo Engine (Resilient simulation)

    Rules:
    - Quota exhaustion (429) or temporary server errors (502, 503, 504) trigger automatic fallback.
    - Invalid API keys / authentication failures raise clear configuration errors without silent fallback.
    """
    def __init__(self):
        self.last_provider_used = "local_demo"
        self.last_error = ""

    def get_provider_mode(self) -> str:
        return (settings.AI_PROVIDER or "auto").strip().lower()

    async def generate_voice_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_context: str,
        customer_profile: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        mode = self.get_provider_mode()

        # Manual Mode: Local only
        if mode == "local":
            logger.info("AI_PROVIDER=local: Using Local Demo Engine directly.")
            out = gemini_service._local_intelligent_agent(user_message, conversation_history, rag_context, customer_profile, language)
            out["engine_mode"] = "local_demo"
            out["provider"] = "local_demo"
            self.last_provider_used = "local_demo"
            return out

        # Manual Mode: Groq only
        if mode == "groq":
            if not groq_service.is_configured():
                raise AIConfigurationError("AI_PROVIDER is set to 'groq', but GROQ_API_KEY is not configured.", provider="groq")
            try:
                out = await groq_service.generate_voice_response(user_message, conversation_history, rag_context, customer_profile, language)
                out["engine_mode"] = "live_groq"
                out["provider"] = "groq"
                self.last_provider_used = "groq"
                return out
            except AIConfigurationError:
                raise
            except (AIRateLimitError, AITemporaryServerError) as e:
                logger.warning(f"Groq failed in groq-only mode ({e}). Falling back to local engine.")
                out = gemini_service._local_intelligent_agent(user_message, conversation_history, rag_context, customer_profile, language)
                out["engine_mode"] = "local_demo"
                out["provider"] = "local_demo"
                self.last_provider_used = "local_demo"
                return out

        # Manual Mode: Gemini only
        if mode == "gemini":
            if not gemini_service.is_configured():
                raise AIConfigurationError("AI_PROVIDER is set to 'gemini', but GEMINI_API_KEY is not configured.", provider="gemini")
            try:
                out = await gemini_service.raw_gemini_voice_response(user_message, conversation_history, rag_context, customer_profile, language)
                out["engine_mode"] = "live_gemini"
                out["provider"] = "gemini"
                self.last_provider_used = "gemini"
                return out
            except AIConfigurationError:
                raise
            except (AIRateLimitError, AITemporaryServerError) as e:
                logger.warning(f"Gemini failed in gemini-only mode ({e}). Falling back to local engine.")
                out = gemini_service._local_intelligent_agent(user_message, conversation_history, rag_context, customer_profile, language)
                out["engine_mode"] = "local_demo"
                out["provider"] = "local_demo"
                self.last_provider_used = "local_demo"
                return out

        # Default Mode: "auto" (Gemini -> Groq -> Local Demo)
        gemini_attempted = False
        if gemini_service.is_configured() and not gemini_service.is_quota_exhausted:
            gemini_attempted = True
            try:
                out = await gemini_service.raw_gemini_voice_response(user_message, conversation_history, rag_context, customer_profile, language)
                out["engine_mode"] = "live_gemini"
                out["provider"] = "gemini"
                self.last_provider_used = "gemini"
                return out
            except AIConfigurationError as auth_err:
                # Rule 5: Gemini invalid API key -> no automatic Groq fallback!
                logger.error(f"Gemini authentication failed: {auth_err}. Halting fallback chain.")
                self.last_error = str(auth_err)
                raise
            except (AIRateLimitError, AITemporaryServerError) as retryable_err:
                logger.warning(f"Gemini primary failed ({retryable_err}). Attempting secondary provider Groq...")
                self.last_error = str(retryable_err)
            except Exception as e:
                logger.error(f"Unexpected Gemini error: {e}. Attempting secondary provider Groq...")
                self.last_error = str(e)

        # Secondary: Try Groq
        if groq_service.is_configured() and not groq_service.is_rate_limited:
            try:
                out = await groq_service.generate_voice_response(user_message, conversation_history, rag_context, customer_profile, language)
                out["engine_mode"] = "live_groq"
                out["provider"] = "groq"
                self.last_provider_used = "groq"
                return out
            except AIConfigurationError as auth_err:
                # Rule 6: Groq invalid API key -> clear configuration error!
                logger.error(f"Groq authentication failed: {auth_err}. Halting fallback chain.")
                self.last_error = str(auth_err)
                raise
            except (AIRateLimitError, AITemporaryServerError) as retryable_err:
                logger.warning(f"Groq secondary failed ({retryable_err}). Engaging final Local Demo Engine...")
                self.last_error = str(retryable_err)
            except Exception as e:
                logger.error(f"Unexpected Groq error: {e}. Engaging final Local Demo Engine...")
                self.last_error = str(e)

        # Final Fallback: Local Heuristic Engine
        logger.info("Routing voice request to Local Demo Engine (Quota/Server Fallback).")
        out = gemini_service._local_intelligent_agent(user_message, conversation_history, rag_context, customer_profile, language)
        out["engine_mode"] = "local_demo"
        out["provider"] = "local_demo"
        self.last_provider_used = "local_demo"
        return out

    async def generate_call_summary(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        mode = self.get_provider_mode()

        if mode == "local":
            out = gemini_service._local_summary_generator(messages, customer_profile)
            out["engine_mode"] = "local_demo"
            out["provider"] = "local_demo"
            self.last_provider_used = "local_demo"
            return out

        if mode == "groq":
            if not groq_service.is_configured():
                raise AIConfigurationError("AI_PROVIDER is set to 'groq', but GROQ_API_KEY is not configured.", provider="groq")
            try:
                out = await groq_service.generate_call_summary(messages, customer_profile)
                out["engine_mode"] = "live_groq"
                out["provider"] = "groq"
                self.last_provider_used = "groq"
                return out
            except AIConfigurationError:
                raise
            except (AIRateLimitError, AITemporaryServerError):
                out = gemini_service._local_summary_generator(messages, customer_profile)
                out["engine_mode"] = "local_demo"
                out["provider"] = "local_demo"
                self.last_provider_used = "local_demo"
                return out

        if mode == "gemini":
            if not gemini_service.is_configured():
                raise AIConfigurationError("AI_PROVIDER is set to 'gemini', but GEMINI_API_KEY is not configured.", provider="gemini")
            try:
                out = await gemini_service.raw_gemini_call_summary(messages, customer_profile)
                out["engine_mode"] = "live_gemini"
                out["provider"] = "gemini"
                self.last_provider_used = "gemini"
                return out
            except AIConfigurationError:
                raise
            except (AIRateLimitError, AITemporaryServerError):
                out = gemini_service._local_summary_generator(messages, customer_profile)
                out["engine_mode"] = "local_demo"
                out["provider"] = "local_demo"
                self.last_provider_used = "local_demo"
                return out

        # Default Mode: "auto"
        if gemini_service.is_configured() and not gemini_service.is_quota_exhausted:
            try:
                out = await gemini_service.raw_gemini_call_summary(messages, customer_profile)
                out["engine_mode"] = "live_gemini"
                out["provider"] = "gemini"
                self.last_provider_used = "gemini"
                return out
            except AIConfigurationError as auth_err:
                logger.error(f"Gemini authentication failed during summary: {auth_err}.")
                raise
            except (AIRateLimitError, AITemporaryServerError) as retryable_err:
                logger.warning(f"Gemini call summary failed ({retryable_err}). Trying Groq...")
            except Exception as e:
                logger.error(f"Unexpected Gemini summary error: {e}. Trying Groq...")

        if groq_service.is_configured() and not groq_service.is_rate_limited:
            try:
                out = await groq_service.generate_call_summary(messages, customer_profile)
                out["engine_mode"] = "live_groq"
                out["provider"] = "groq"
                self.last_provider_used = "groq"
                return out
            except AIConfigurationError as auth_err:
                logger.error(f"Groq authentication failed during summary: {auth_err}.")
                raise
            except (AIRateLimitError, AITemporaryServerError) as retryable_err:
                logger.warning(f"Groq call summary failed ({retryable_err}). Falling back to Local Demo Engine...")
            except Exception as e:
                logger.error(f"Unexpected Groq summary error: {e}. Falling back to Local Demo Engine...")

        out = gemini_service._local_summary_generator(messages, customer_profile)
        out["engine_mode"] = "local_demo"
        out["provider"] = "local_demo"
        self.last_provider_used = "local_demo"
        return out


ai_service = AIService()
