import os
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import db_manager
from app.core.exceptions import AIConfigurationError, AIRateLimitError, AITemporaryServerError
from app.services.gemini_service import gemini_service
from app.services.groq_service import groq_service
from app.services.ai_service import ai_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["System Settings"])

class SettingsUpdateRequest(BaseModel):
    ai_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    default_language: Optional[str] = None

class GeminiTestRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None

class GroqTestRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None

def _mask_key(key: Optional[str]) -> str:
    if not key or not key.strip():
        return ""
    clean = key.strip()
    return f"{clean[:4]}...{clean[-4:]}" if len(clean) > 8 else "****"

@router.get("")
async def get_system_settings():
    is_gemini_configured = gemini_service.is_configured()
    is_gemini_quota_hit = gemini_service.is_quota_exhausted
    is_groq_configured = groq_service.is_configured()
    is_groq_rate_limited = groq_service.is_rate_limited
    
    provider_mode = (settings.AI_PROVIDER or "auto").strip().lower()
    last_used = ai_service.last_provider_used

    # Determine currently active engine label based on provider hierarchy
    if provider_mode == "local":
        active_engine = "local_demo"
        active_label = "LOCAL DEMO MODE"
    elif provider_mode == "gemini":
        if is_gemini_configured and not is_gemini_quota_hit:
            active_engine = "live_gemini"
            active_label = "LIVE GEMINI AI"
        else:
            active_engine = "local_demo"
            active_label = "LOCAL DEMO MODE"
    elif provider_mode == "groq":
        if is_groq_configured and not is_groq_rate_limited:
            active_engine = "live_groq"
            active_label = "LIVE GROQ AI"
        else:
            active_engine = "local_demo"
            active_label = "LOCAL DEMO MODE"
    else:  # "auto"
        if is_gemini_configured and not is_gemini_quota_hit:
            active_engine = "live_gemini"
            active_label = "LIVE GEMINI AI"
        elif is_groq_configured and not is_groq_rate_limited:
            active_engine = "live_groq"
            active_label = "LIVE GROQ AI"
        else:
            active_engine = "local_demo"
            active_label = "LOCAL DEMO MODE"

    # Status messages
    if is_gemini_quota_hit:
        gemini_status_msg = "Google Free-Tier Quota Limit (429) Reached - Automatic Fallback Active"
    elif is_gemini_configured:
        gemini_status_msg = f"Connected to Google AI Studio ({settings.GEMINI_MODEL})"
    else:
        gemini_status_msg = "Unconfigured (Waiting for API key)"

    if is_groq_rate_limited:
        groq_status_msg = "Groq Rate Limit (429) Reached - Fallback to Local Engine"
    elif is_groq_configured:
        groq_status_msg = f"Connected to Groq LPUs ({settings.GROQ_MODEL})"
    else:
        groq_status_msg = "Unconfigured (Optional Secondary Fallback)"

    gemini_key = gemini_service.api_key or settings.GEMINI_API_KEY
    groq_key = groq_service.api_key or settings.GROQ_API_KEY

    return {
        "status": "online",
        "ai_provider": provider_mode,
        "active_engine": active_engine,
        "active_label": active_label,
        "last_provider_used": last_used,
        "fallback_priority": [
            "Primary: Google Gemini AI",
            "Secondary: Groq AI",
            "Final: Local Heuristic Engine"
        ],
        "gemini": {
            "is_configured": is_gemini_configured,
            "mode": "live" if (is_gemini_configured and not is_gemini_quota_hit) else "local_demo",
            "is_quota_exhausted": is_gemini_quota_hit,
            "model": settings.GEMINI_MODEL,
            "masked_key": _mask_key(gemini_key),
            "status_message": gemini_status_msg
        },
        "groq": {
            "is_configured": is_groq_configured,
            "mode": "live" if (is_groq_configured and not is_groq_rate_limited) else "local_demo",
            "is_rate_limited": is_groq_rate_limited,
            "model": settings.GROQ_MODEL,
            "masked_key": _mask_key(groq_key),
            "status_message": groq_status_msg
        },
        "database": {
            "type": "MongoDB" if db_manager.is_mongo_connected else "Local Persistent JSON DB (MongoDB Fallback)",
            "is_live_mongo": db_manager.is_mongo_connected,
            "status": "healthy"
        },
        "rag": {
            "vector_store": "ChromaDB" if rag_service.collection else "Built-in TF-IDF Vector Index",
            "is_chroma_active": bool(rag_service.collection)
        },
        "environment": settings.ENVIRONMENT,
        "default_language": "en"
    }

def _persist_env_var(key: str, value: str):
    """Safely updates or adds environment variable in .env files"""
    env_paths = [
        ".env",
        "backend/.env",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    ]
    for env_path in env_paths:
        try:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                found = False
                for line in lines:
                    if line.startswith(f"{key}="):
                        new_lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        new_lines.append(line)
                if not found:
                    new_lines.append(f"{key}={value}\n")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
        except Exception as e:
            logger.warning(f"Could not persist {key} to {env_path}: {e}")

@router.post("")
async def update_system_settings(req: SettingsUpdateRequest):
    if req.ai_provider is not None:
        val = req.ai_provider.strip().lower()
        if val in ["auto", "gemini", "groq", "local"]:
            settings.AI_PROVIDER = val
            _persist_env_var("AI_PROVIDER", val)

    if req.gemini_api_key is not None:
        key = req.gemini_api_key.strip()
        settings.GEMINI_API_KEY = key
        gemini_service.update_api_key(key, req.gemini_model)
        _persist_env_var("GEMINI_API_KEY", key)

    if req.gemini_model:
        settings.GEMINI_MODEL = req.gemini_model.strip()
        gemini_service.model_name = settings.GEMINI_MODEL
        _persist_env_var("GEMINI_MODEL", settings.GEMINI_MODEL)

    if req.groq_api_key is not None:
        gkey = req.groq_api_key.strip()
        settings.GROQ_API_KEY = gkey
        groq_service.update_api_key(gkey, req.groq_model)
        _persist_env_var("GROQ_API_KEY", gkey)

    if req.groq_model:
        settings.GROQ_MODEL = req.groq_model.strip()
        groq_service.model_name = settings.GROQ_MODEL
        _persist_env_var("GROQ_MODEL", settings.GROQ_MODEL)

    return {
        "message": "Settings updated successfully",
        "ai_provider": settings.AI_PROVIDER,
        "gemini_configured": gemini_service.is_configured(),
        "groq_configured": groq_service.is_configured(),
        "gemini_model": settings.GEMINI_MODEL,
        "groq_model": settings.GROQ_MODEL
    }

@router.post("/test-gemini")
async def test_gemini_connection(req: Optional[GeminiTestRequest] = None):
    test_key = (
        (req.api_key.strip() if req and req.api_key else None)
        or gemini_service.api_key
        or settings.GEMINI_API_KEY
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    )
    test_model = (
        (req.model.strip() if req and req.model else None)
        or settings.GEMINI_MODEL
        or "gemini-3.8-flash"
    )

    if not test_key:
        return {
            "success": False,
            "mode": "local_demo",
            "message": "Gemini API key is not configured. Running in Local Demo Engine Mode."
        }

    try:
        import google.generativeai as genai
        genai.configure(api_key=test_key)
        model = genai.GenerativeModel(test_model)
        
        res = model.generate_content("Respond with 'Connection successful' in two words.")
        reply_content = res.text.strip() if hasattr(res, "text") and res.text else "Connection established."
        
        gemini_service.update_api_key(test_key, test_model)
        gemini_service.is_quota_exhausted = False
        gemini_service.active_mode = "live"
        settings.GEMINI_API_KEY = test_key
        settings.GEMINI_MODEL = test_model

        return {
            "success": True,
            "mode": "live",
            "message": f"Successfully verified live Google Gemini API connection ({test_model})!",
            "response": reply_content,
            "model": test_model
        }
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Quota" in err_msg or "ResourceExhausted" in err_msg:
            gemini_service.is_quota_exhausted = True
            gemini_service.active_mode = "local_demo"
            return {
                "success": False,
                "mode": "local_demo",
                "is_quota_exhausted": True,
                "message": "Google Gemini Free-Tier Quota Limit (429) is currently reached for this project. System will automatically route calls to Groq AI (Secondary) or Local Demo Engine."
            }
        
        logger.error(f"Gemini API test verification failed: {e}")
        return {
            "success": False,
            "mode": "local_demo",
            "error": err_msg
        }

@router.post("/test-groq")
async def test_groq_connection(req: Optional[GroqTestRequest] = None):
    test_key = (
        (req.api_key.strip() if req and req.api_key else None)
        or groq_service.api_key
        or settings.GROQ_API_KEY
        or os.environ.get("GROQ_API_KEY")
        or ""
    )
    test_model = (
        (req.model.strip() if req and req.model else None)
        or settings.GROQ_MODEL
        or "llama-3.3-70b-versatile"
    )

    if not test_key:
        return {
            "success": False,
            "mode": "local_demo",
            "message": "Groq API key is not configured."
        }

    try:
        result = groq_service.test_connection(api_key=test_key, model=test_model)
        settings.GROQ_API_KEY = test_key
        settings.GROQ_MODEL = test_model
        return result
    except AIConfigurationError as e:
        return {
            "success": False,
            "mode": "local_demo",
            "error": f"Groq Authentication Error: Invalid API key ({e.message})"
        }
    except AIRateLimitError as e:
        return {
            "success": False,
            "mode": "local_demo",
            "error": f"Groq Rate Limit (429): {e.message}"
        }
    except Exception as e:
        return {
            "success": False,
            "mode": "local_demo",
            "error": str(e)
        }
