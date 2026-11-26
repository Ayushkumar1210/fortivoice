import json
import re
import os
import inspect
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationError,
    AIRateLimitError,
    AITemporaryServerError
)

logger = logging.getLogger(__name__)

SALES_AGENT_PROMPT = """You are "FortiVoice", an elite, autonomous AI Sales Voice Agent for FortiCloud Solutions.
Your goal is to converse with prospective clients over voice, answer their product/pricing inquiries accurately using the provided Company Knowledge Base, qualify the lead, and secure a 30-minute product demo / consultation.

VOICE RESPONSE GUIDELINES (CRITICAL):
- Your output will be read aloud to the customer using Text-to-Speech (TTS).
- Keep your response conversational, concise, warm, professional, and punchy (1 to 3 spoken sentences per turn).
- DO NOT use markdown formatting, asterisks (*), bullet points, or complex punctuation in "reply_text" because TTS will pronounce them weirdly.
- If the customer speaks Hindi, reply in natural, conversational Hindi (or Hinglish if appropriate). If English, reply in natural professional English.
- Always be persuasive but never pushy. Ground your answers strictly in the retrieved company knowledge. If you do not know a specific internal policy, state that you will confirm it during the live demo.

LEAD QUALIFICATION INSTRUCTIONS:
- Actively identify and extract customer information:
  * Name
  * Company / Organization name
  * Phone number
  * Email
  * Product interest (Starter, Pro, Enterprise, custom AI)
  * Budget (e.g. $500/mo, $2,000/mo, Enterprise scale)
  * Specific requirements / pain points
  * Purchase timeline (Immediate, 1-3 months, next year)
- Classify the lead:
  * HOT (Score 75-100): High budget, immediate timeline, decision maker, strong interest, or requested booking.
  * WARM (Score 40-74): Moderate interest, browsing solutions, evaluating budget, flexible timeline.
  * COLD (Score 0-39): Just curious, no budget, competitor scouting, or unresponsive to questions.
- Provide a clear 1-2 sentence "score_reasoning".

APPOINTMENT INTENT:
- If the customer asks to book a meeting, demo, consultation, or agrees to your offer to schedule one:
  * Detect date (format: YYYY-MM-DD or standard future date relative to today's date {today_date}).
  * Detect preferred time (e.g. 10:00, 14:30, 2:00 PM).
  * Set "appointment_intent": {{"requested": true, "preferred_date": "YYYY-MM-DD", "preferred_time": "HH:MM", "purpose": "..."}}.

SENTIMENT ANALYSIS:
- Classify sentiment as "Positive", "Neutral", or "Negative".
- sentiment_score from -1.0 to 1.0.

OUTPUT FORMAT:
You MUST respond strictly in valid JSON matching this structure without markdown code blocks:
{{
  "reply_text": "Spoken conversational response here.",
  "extracted_lead": {{
    "name": "...",
    "company": "...",
    "phone": "...",
    "email": "...",
    "product_interest": "...",
    "budget": "...",
    "requirements": "...",
    "timeline": "..."
  }},
  "sentiment": "Positive",
  "sentiment_score": 0.85,
  "lead_score": 85,
  "lead_status": "HOT",
  "score_reasoning": "Customer has high interest in the Pro tier and requested a demo for next week.",
  "appointment_intent": {{
    "requested": false,
    "preferred_date": null,
    "preferred_time": null,
    "purpose": null
  }}
}}
"""

CALL_SUMMARY_PROMPT = """You are an Executive Sales Analyst AI.
Analyze the following completed sales conversation transcript between the FortiVoice AI Agent and the prospective customer.
Provide a thorough executive sales qualification summary.

TRANSCRIPT:
{transcript}

Generate a structured JSON response with:
{{
  "summary": "Concise 2-3 paragraph summary of the call, discussing what was covered.",
  "customer_requirements": "Bullet points or sentence describing customer exact business needs and volume.",
  "customer_objections": "Any concerns, pricing hesitation, or security questions raised.",
  "lead_qualification": "Detailed evaluation of lead fit and qualification status.",
  "lead_score": 85,
  "lead_status": "HOT",
  "score_reasoning": "Reason for the assigned score.",
  "sentiment": "Positive",
  "recommended_next_action": "Exact next step for the sales rep (e.g., Send Enterprise pricing proposal and calendar invite for Thursday at 2 PM)."
}}
Respond ONLY in valid JSON.
"""

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self.model_name = settings.GEMINI_MODEL or "gemini-3.8-flash"
        self._client_initialized = False
        self.is_quota_exhausted = False
        self.last_error = ""
        self.active_mode = "local_demo"
        self._init_gemini()

    def _init_gemini(self):
        if self.api_key and self.api_key.strip():
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key.strip())
                self._client_initialized = True
                self.active_mode = "local_demo" if self.is_quota_exhausted else "live"
                logger.info(f"Gemini API configured with model {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to configure Gemini API: {e}")
                self._client_initialized = False
                self.active_mode = "local_demo"
        else:
            self._client_initialized = False
            self.active_mode = "local_demo"

    def update_api_key(self, api_key: str, model_name: Optional[str] = None):
        self.api_key = api_key.strip()
        if model_name:
            self.model_name = model_name
        self.is_quota_exhausted = False
        self.last_error = ""
        self._init_gemini()

    def is_configured(self) -> bool:
        if not self.api_key:
            self.api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
            if self.api_key:
                self._init_gemini()
        return bool(self.api_key and self._client_initialized)

    def _get_generation_config(self, temperature: float = 0.4) -> Dict[str, Any]:
        """Constructs generation configuration safely checking installed SDK capabilities"""
        config: Dict[str, Any] = {"temperature": temperature}
        try:
            import google.generativeai as genai
            if hasattr(genai, "types") and hasattr(genai.types, "GenerationConfig"):
                init_params = inspect.signature(genai.types.GenerationConfig.__init__).parameters
                if "response_mime_type" in init_params:
                    config["response_mime_type"] = "application/json"
        except Exception:
            pass
        return config

    def _classify_and_raise(self, error: Exception):
        """Inspects Gemini exception and raises appropriate classified AIException"""
        err_str = str(error).lower()
        err_type = type(error).__name__

        # 1. Invalid API Key / Authentication Error
        if (
            err_type in ["Unauthenticated", "PermissionDenied"]
            or "api_key_invalid" in err_str
            or "api key not valid" in err_str
            or "invalid api key" in err_str
            or "api key invalid" in err_str
            or ("invalid argument" in err_str and "api_key" in err_str)
            or "401" in err_str
            or "403" in err_str
        ):
            self.last_error = f"Authentication Error: {error}"
            raise AIConfigurationError(
                f"Gemini API Authentication Error: Invalid or expired API key. {error}",
                provider="gemini"
            )

        # 2. Quota Exhaustion / Rate Limits (HTTP 429)
        if (
            err_type == "ResourceExhausted"
            or "429" in err_str
            or "resourceexhausted" in err_str
            or "quota" in err_str
            or "rate limit" in err_str
        ):
            self.is_quota_exhausted = True
            self.last_error = f"Free-tier quota limit reached (429): {error}"
            self.active_mode = "local_demo"
            raise AIRateLimitError(
                f"Gemini Quota Exceeded (429): {error}",
                provider="gemini"
            )

        # 3. Upstream Temporary Server Errors (500, 502, 503, 504, Timeouts)
        if (
            err_type in ["BadGateway", "ServiceUnavailable", "GatewayTimeout", "InternalServerError"]
            or any(s in err_str for s in ["500", "502", "503", "504", "bad gateway", "service unavailable", "gateway timeout", "internal server error", "timeout", "timed out", "connection error", "network error"])
        ):
            self.last_error = f"Temporary Server Error: {error}"
            self.is_quota_exhausted = True
            raise AITemporaryServerError(
                f"Gemini Temporary Server Error ({err_type}): {error}",
                provider="gemini"
            )

        self.last_error = f"Gemini Error: {error}"
        raise error

    async def raw_gemini_voice_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_context: str,
        customer_profile: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Direct call to Gemini GenerativeModel without local fallback"""
        if not self.is_configured():
            raise AIConfigurationError("Gemini API key is not configured.", provider="gemini")

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
            import google.generativeai as genai
            genai.configure(api_key=self.api_key.strip())
            gen_config = self._get_generation_config(temperature=0.4)

            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=prompt_filled,
                generation_config=gen_config
            )
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: model.generate_content(user_prompt)),
                timeout=3.0
            )
            raw_text = response.text.strip() if hasattr(response, "text") and response.text else ""
            data = self._clean_and_parse_json(raw_text)
            if data and "reply_text" in data:
                data["engine_mode"] = "live_gemini"
                data["provider"] = "gemini"
                self.active_mode = "live"
                self.is_quota_exhausted = False
                return data
            raise ValueError(f"Gemini response could not be parsed as valid JSON: {raw_text[:120]}")
        except asyncio.TimeoutError:
            self.last_error = "Gemini request timed out after 4 seconds."
            raise AITemporaryServerError("Gemini request timed out (4s).", provider="gemini")
        except Exception as e:
            self._classify_and_raise(e)

    async def raw_gemini_call_summary(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Direct call to Gemini for post-call summary without local fallback"""
        if not self.is_configured():
            raise AIConfigurationError("Gemini API key is not configured.", provider="gemini")

        transcript = ""
        for m in messages:
            sender = m.get("sender", "unknown")
            text = m.get("text", "")
            transcript += f"[{sender.upper()}]: {text}\n"

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key.strip())
            gen_config = self._get_generation_config(temperature=0.2)

            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=gen_config
            )
            prompt = CALL_SUMMARY_PROMPT.format(transcript=transcript)
            response = model.generate_content(prompt, request_options={"timeout": 5.0})
            raw_text = response.text.strip() if hasattr(response, "text") and response.text else ""
            data = self._clean_and_parse_json(raw_text)
            if data and "summary" in data:
                data["engine_mode"] = "live_gemini"
                data["provider"] = "gemini"
                return data
            raise ValueError(f"Gemini call summary response could not be parsed as JSON: {raw_text[:120]}")
        except Exception as e:
            self._classify_and_raise(e)

    async def generate_voice_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_context: str,
        customer_profile: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Routes through unified AI orchestrator (Gemini -> Groq -> Local Demo)"""
        from app.services.ai_service import ai_service
        return await ai_service.generate_voice_response(
            user_message, conversation_history, rag_context, customer_profile, language
        )

    async def generate_call_summary(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Routes through unified AI orchestrator (Gemini -> Groq -> Local Demo)"""
        from app.services.ai_service import ai_service
        return await ai_service.generate_call_summary(messages, customer_profile)

    def _clean_and_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Strip markdown codeblocks
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

    def _local_intelligent_agent(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_context: str,
        customer_profile: Optional[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """Production-ready heuristic fallback engine to guarantee 100% reliable interview demo"""
        msg_lower = user_message.lower()
        profile = customer_profile or {}

        # 1. Extract contact details
        phone_match = re.search(r'(\+?\d[\d -]{8,}\d)', user_message)
        email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', user_message)
        name_match = re.search(r'(?:my name is|i am|this is|i\'m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', user_message, re.IGNORECASE)
        company_match = re.search(r'(?:from|at|with|represent|company is|working for)\s+([A-Z0-9][a-zA-Z0-9&.-]+(?:\s+[A-Z0-9][a-zA-Z0-9&.-]+)*)', user_message, re.IGNORECASE)

        extracted = dict(profile)
        if phone_match and not extracted.get("phone"):
            extracted["phone"] = phone_match.group(1).strip()
        if email_match and not extracted.get("email"):
            extracted["email"] = email_match.group(1).strip()
        if name_match and not extracted.get("name"):
            extracted["name"] = name_match.group(1).strip()
        if company_match and not extracted.get("company"):
            extracted["company"] = company_match.group(1).strip()

        # Extract budget
        budget_match = re.search(r'(\$\s?\d+[\d,]*|\d+\s?(?:dollars|usd|k|thousand|lakh))', msg_lower)
        if budget_match:
            extracted["budget"] = budget_match.group(1)

        # Extract product interest
        if "enterprise" in msg_lower:
            extracted["product_interest"] = "Enterprise Custom Plan"
        elif "pro" in msg_lower or "growth" in msg_lower:
            extracted["product_interest"] = "Professional Growth Plan"
        elif "starter" in msg_lower:
            extracted["product_interest"] = "Starter Plan"

        # 2. Sentiment analysis
        pos_words = ["great", "awesome", "perfect", "interested", "love", "good", "yes", "definitely", "sure", "sounds good", "excellent", "impressive", "achha", "badhiya", "sahi"]
        neg_words = ["expensive", "costly", "bad", "no", "not interested", "disappointed", "hate", "slow", "mehnga", "bekaar", "nahi"]
        
        pos_count = sum(1 for w in pos_words if w in msg_lower)
        neg_count = sum(1 for w in neg_words if w in msg_lower)

        if pos_count > neg_count:
            sentiment = "Positive"
            sentiment_score = min(0.9, 0.4 + 0.15 * pos_count)
        elif neg_count > pos_count:
            sentiment = "Negative"
            sentiment_score = max(-0.9, -0.4 - 0.15 * neg_count)
        else:
            sentiment = "Neutral"
            sentiment_score = 0.0

        # 3. Detect Appointment Booking Intent
        appointment_intent = {
            "requested": False,
            "preferred_date": None,
            "preferred_time": None,
            "purpose": "FortiVoice Product Demo"
        }
        booking_keywords = ["demo", "appointment", "schedule", "book", "meeting", "call me", "talk to sales", "calendar", "mulaqat"]
        has_booking_intent = any(k in msg_lower for k in booking_keywords)

        if has_booking_intent:
            appointment_intent["requested"] = True
            # Extract date if mentioned
            today = date.today()
            if "tomorrow" in msg_lower:
                appointment_intent["preferred_date"] = (today + timedelta(days=1)).isoformat()
            elif "friday" in msg_lower:
                appointment_intent["preferred_date"] = (today + timedelta(days=(4 - today.weekday()) % 7 or 7)).isoformat()
            elif "monday" in msg_lower:
                appointment_intent["preferred_date"] = (today + timedelta(days=(0 - today.weekday()) % 7 or 7)).isoformat()
            else:
                appointment_intent["preferred_date"] = (today + timedelta(days=2)).isoformat()

            # Extract time
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', msg_lower)
            if time_match and ("am" in msg_lower or "pm" in msg_lower or ":" in msg_lower):
                appointment_intent["preferred_time"] = time_match.group(1).upper()
            else:
                appointment_intent["preferred_time"] = "14:00"

        # 4. Lead Scoring Calculation
        score = 40
        reasoning_points = []
        if extracted.get("phone") or extracted.get("email"):
            score += 20
            reasoning_points.append("Contact information provided")
        if extracted.get("budget"):
            score += 20
            reasoning_points.append(f"Budget indicated ({extracted.get('budget')})")
        if appointment_intent["requested"]:
            score += 20
            reasoning_points.append("Requested interactive product demonstration")
        if sentiment == "Positive":
            score += 10
            reasoning_points.append("Strong positive sentiment observed")
        elif sentiment == "Negative":
            score -= 15
            reasoning_points.append("Customer expressed objections or hesitations")

        lead_score = max(5, min(98, score))
        if lead_score >= 75:
            lead_status = "HOT"
        elif lead_score >= 40:
            lead_status = "WARM"
        else:
            lead_status = "COLD"

        score_reasoning = "; ".join(reasoning_points) if reasoning_points else "Initial introductory phase."

        # 5. Natural Voice Response Generation (Grounded in knowledge base)
        if language == "hi":
            if has_booking_intent:
                reply = f"Bilkul! Hum aapke liye demo schedule kar rahe hain {appointment_intent['preferred_date']} ko {appointment_intent['preferred_time']} baje. Kya main aapka phone number aur email confirm kar sakta hoon?"
            elif "price" in msg_lower or "cost" in msg_lower or "pricing" in msg_lower or "kitna" in msg_lower:
                reply = "Hamara Starter Plan char sau ninyanve dollar per month se shuru hota hai jisme 1,000 voice minutes milte hain, aur Enterprise Plan custom scale ke liye available hai. Kya aapki team ke liye demo book karein?"
            else:
                reply = "Namaste! Main FortiVoice hoon, aapka autonomous AI sales specialist. Hum aapke customer calls ko automate karne aur instant leads qualify karne mein madad karte hain. Aap kis product tier ke baare mein janna chahte hain?"
        else:
            if has_booking_intent:
                reply = f"I would be glad to set up your VIP product demonstration for {appointment_intent['preferred_date']} at {appointment_intent['preferred_time']}. Could you confirm the best email and phone number to send your confirmation invite?"
            elif "price" in msg_lower or "cost" in msg_lower or "pricing" in msg_lower:
                reply = "Our Starter tier begins at $499 per month for 1,000 voice minutes, while our Pro tier is $1,499 per month for 5,000 minutes with multilingual support. Would you like me to book a 30-minute demo to review which plan matches your call volume?"
            elif "security" in msg_lower or "soc" in msg_lower or "hipaa" in msg_lower:
                reply = "FortiVoice is fully SOC-2 Type II certified and HIPAA compliant with end-to-end TLS 1.3 audio encryption. We never train public models on your proprietary conversations."
            elif "timeline" in msg_lower or "setup" in msg_lower or "how long" in msg_lower:
                reply = "You can be up and running in under 48 hours on our Starter plan, or 3 to 5 business days for custom CRM and telephony integrations."
            else:
                name_greeting = f" {extracted['name']}" if extracted.get("name") else ""
                reply = f"Hello{name_greeting}! I am FortiVoice, your autonomous AI sales specialist. We empower enterprises to automate inbound sales calls and qualify leads instantly. What business requirements can I help you solve today?"

        return {
            "reply_text": reply,
            "extracted_lead": extracted,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "lead_score": lead_score,
            "lead_status": lead_status,
            "score_reasoning": score_reasoning,
            "appointment_intent": appointment_intent
        }

    def _local_summary_generator(self, messages: List[Dict[str, Any]], customer_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        user_texts = [m.get("text", "") for m in messages if m.get("sender") == "customer"]
        combined = " ".join(user_texts).lower()

        name = customer_profile.get("name", "Prospect") if customer_profile else "Prospect"
        budget = customer_profile.get("budget", "Not specified") if customer_profile else "Not specified"

        objections = "None explicitly recorded. Customer expressed positive interest in capability demonstration."
        if "expensive" in combined or "cost" in combined:
            objections = "Pricing clarification requested regarding minute overage and tier breakdown."
        elif "security" in combined:
            objections = "Security validation regarding SOC-2 and HIPAA compliance requirements."

        reqs = "Automated inbound voice assistant, CRM synchronization, and appointment scheduling."
        if "hindi" in combined:
            reqs += " Specifically interested in multilingual Hindi & English support."

        lead_score = 80 if ("demo" in combined or "book" in combined or budget != "Not specified") else 60
        lead_status = "HOT" if lead_score >= 75 else "WARM"

        return {
            "summary": f"FortiVoice completed an inbound discovery conversation with {name}. The prospect reviewed system architecture, voice response latency, and pricing tiers. Key questions centered on CRM integration and rollout timelines.",
            "customer_requirements": reqs,
            "customer_objections": objections,
            "lead_qualification": f"Lead qualified as {lead_status}. High purchase intent with active interest in enterprise voice workflows.",
            "lead_score": lead_score,
            "lead_status": lead_status,
            "score_reasoning": "Prospect engaged in thorough product discussion, verified pricing requirements, and requested consultation follow-up.",
            "sentiment": "Positive",
            "recommended_next_action": f"Sales team to deliver executive PDF deck, confirm booked calendar consultation, and prepare ROI projection for {budget} budget."
        }


gemini_service = GeminiService()
