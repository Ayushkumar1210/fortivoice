import pytest
import os
import sys
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.core.exceptions import (
    AIConfigurationError,
    AIRateLimitError,
    AITemporaryServerError
)
from app.services.gemini_service import gemini_service
from app.services.groq_service import groq_service
from app.services.ai_service import ai_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_provider_state():
    """Ensure clean state before each test"""
    orig_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "auto"
    gemini_service.is_quota_exhausted = False
    groq_service.is_rate_limited = False
    yield
    settings.AI_PROVIDER = orig_provider
    gemini_service.is_quota_exhausted = False
    groq_service.is_rate_limited = False


# -------------------------------------------------------------------------
# Scenario 1: Gemini succeeds -> Groq is not called
# -------------------------------------------------------------------------
def test_scenario_1_gemini_succeeds_groq_not_called():
    mock_gemini_res = {
        "reply_text": "Hello, I am FortiVoice on Gemini AI.",
        "extracted_lead": {"name": "Alice Smith"},
        "sentiment": "Positive",
        "sentiment_score": 0.9,
        "lead_score": 85,
        "lead_status": "HOT",
        "score_reasoning": "Strong budget indicated.",
        "appointment_intent": {"requested": False}
    }

    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        mock_gemini.return_value = dict(mock_gemini_res)

        result = asyncio.run(ai_service.generate_voice_response(
            user_message="Hello, can you help me?",
            conversation_history=[],
            rag_context="FortiVoice plans.",
            customer_profile={}
        ))

        assert result["engine_mode"] == "live_gemini"
        assert result["provider"] == "gemini"
        assert result["reply_text"] == "Hello, I am FortiVoice on Gemini AI."
        mock_gemini.assert_called_once()
        mock_groq.assert_not_called()


# -------------------------------------------------------------------------
# Scenario 2: Gemini returns 429 -> Groq succeeds
# -------------------------------------------------------------------------
def test_scenario_2_gemini_429_groq_succeeds():
    mock_groq_res = {
        "reply_text": "Hello, I am FortiVoice powered by Groq LPU inference.",
        "extracted_lead": {"name": "Bob Miller", "budget": "$2,000/mo"},
        "sentiment": "Positive",
        "sentiment_score": 0.85,
        "lead_score": 80,
        "lead_status": "HOT",
        "score_reasoning": "Groq inference response with budget.",
        "appointment_intent": {"requested": False}
    }

    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        # Gemini raises 429 Quota Exceeded
        mock_gemini.side_effect = AIRateLimitError("ResourceExhausted: 429 quota exhausted", provider="gemini")
        mock_groq.return_value = dict(mock_groq_res)

        result = asyncio.run(ai_service.generate_voice_response(
            user_message="What plans do you offer?",
            conversation_history=[],
            rag_context="Pricing info.",
            customer_profile={}
        ))

        assert result["engine_mode"] == "live_groq"
        assert result["provider"] == "groq"
        assert "Groq LPU" in result["reply_text"]
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()


# -------------------------------------------------------------------------
# Scenario 3: Gemini returns 429 -> Groq also fails -> Local Demo Engine succeeds
# -------------------------------------------------------------------------
def test_scenario_3_gemini_429_groq_fails_local_demo_succeeds():
    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        # Both APIs fail on rate limit / quota
        mock_gemini.side_effect = AIRateLimitError("Gemini 429 quota limit", provider="gemini")
        mock_groq.side_effect = AIRateLimitError("Groq 429 rate limit exceeded", provider="groq")

        result = asyncio.run(ai_service.generate_voice_response(
            user_message="My name is Clara and my budget is $5,000 for Enterprise.",
            conversation_history=[],
            rag_context="Enterprise plan info.",
            customer_profile={}
        ))

        # Local Demo Engine must cleanly succeed without crashing
        assert result["engine_mode"] == "local_demo"
        assert result["provider"] == "local_demo"
        assert result["lead_score"] >= 40
        assert "Clara" in (result["extracted_lead"].get("name") or "")
        assert result["extracted_lead"].get("budget") is not None
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()


# -------------------------------------------------------------------------
# Scenario 4: Gemini temporary server error (502, 503, 504) -> Groq is attempted
# -------------------------------------------------------------------------
def test_scenario_4_gemini_server_error_groq_attempted():
    mock_groq_res = {
        "reply_text": "FortiVoice connected via Groq after Gemini 503 error.",
        "extracted_lead": {},
        "sentiment": "Neutral",
        "sentiment_score": 0.0,
        "lead_score": 60,
        "lead_status": "WARM",
        "score_reasoning": "Standard evaluation.",
        "appointment_intent": {"requested": False}
    }

    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        # Gemini encounters 503 Service Unavailable
        mock_gemini.side_effect = AITemporaryServerError("Gemini 503 Service Unavailable", provider="gemini")
        mock_groq.return_value = dict(mock_groq_res)

        result = asyncio.run(ai_service.generate_voice_response(
            user_message="Hello, are you online?",
            conversation_history=[],
            rag_context="",
            customer_profile={}
        ))

        assert result["engine_mode"] == "live_groq"
        assert result["provider"] == "groq"
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()


# -------------------------------------------------------------------------
# Scenario 5: Gemini invalid API key -> no automatic Groq fallback
# -------------------------------------------------------------------------
def test_scenario_5_gemini_invalid_key_no_groq_fallback():
    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        # Gemini fails authentication with invalid API key
        mock_gemini.side_effect = AIConfigurationError("Gemini API key is invalid (API_KEY_INVALID)", provider="gemini")

        # Service level: Must raise AIConfigurationError without falling back to Groq
        with pytest.raises(AIConfigurationError) as exc_info:
            asyncio.run(ai_service.generate_voice_response(
                user_message="Hello",
                conversation_history=[],
                rag_context="",
                customer_profile={}
            ))
        
        assert "Gemini" in str(exc_info.value)
        # Groq must NOT be called
        mock_groq.assert_not_called()

    # Route level: Calling /api/voice/interact returns HTTP 400 with clear configuration error
    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        mock_gemini.side_effect = AIConfigurationError("Gemini Authentication Error: Invalid API key.", provider="gemini")
        
        res = client.post("/api/voice/interact", json={
            "session_id": "test-invalid-key-session",
            "message": "Hello test"
        })
        assert res.status_code == 400
        data = res.json()
        assert "Authentication Error" in data["detail"]
        mock_groq.assert_not_called()


# -------------------------------------------------------------------------
# Scenario 6: Groq invalid API key -> clear configuration error
# -------------------------------------------------------------------------
def test_scenario_6_groq_invalid_key_clear_error():
    # Test case 6A: In AI_PROVIDER=groq mode
    settings.AI_PROVIDER = "groq"
    with patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        mock_groq.side_effect = AIConfigurationError("Groq Authentication Error: Invalid API key (401)", provider="groq")

        with pytest.raises(AIConfigurationError) as exc_info:
            asyncio.run(ai_service.generate_voice_response(
                user_message="Hello",
                conversation_history=[],
                rag_context="",
                customer_profile={}
            ))
        assert "Groq" in str(exc_info.value)

    # Test case 6B: In auto mode where Gemini 429 triggers Groq, but Groq has invalid key
    settings.AI_PROVIDER = "auto"
    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        mock_gemini.side_effect = AIRateLimitError("Gemini 429", provider="gemini")
        mock_groq.side_effect = AIConfigurationError("Groq API Authentication Error: Invalid or expired API key.", provider="groq")

        with pytest.raises(AIConfigurationError) as exc_info:
            asyncio.run(ai_service.generate_voice_response(
                user_message="Hello",
                conversation_history=[],
                rag_context="",
                customer_profile={}
            ))
        assert "Groq" in str(exc_info.value)

    # Route level HTTP 400 test for Groq invalid key
    with patch.object(gemini_service, "is_configured", return_value=True), \
         patch.object(gemini_service, "raw_gemini_voice_response", new_callable=AsyncMock) as mock_gemini, \
         patch.object(groq_service, "is_configured", return_value=True), \
         patch.object(groq_service, "generate_voice_response", new_callable=AsyncMock) as mock_groq:
        
        mock_gemini.side_effect = AIRateLimitError("Gemini 429", provider="gemini")
        mock_groq.side_effect = AIConfigurationError("Groq API Authentication Error: Invalid or expired API key.", provider="groq")

        res = client.post("/api/voice/interact", json={
            "session_id": "test-groq-auth-fail",
            "message": "Hello test"
        })
        assert res.status_code == 400
        assert "Groq API Authentication Error" in res.json()["detail"]


# -------------------------------------------------------------------------
# Test Groq Settings Test Endpoint
# -------------------------------------------------------------------------
def test_settings_test_groq_endpoint():
    # 1. Unconfigured
    with patch.object(groq_service, "api_key", ""), \
         patch.object(settings, "GROQ_API_KEY", ""):
        res = client.post("/api/settings/test-groq", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert "not configured" in data["message"]

    # 2. Successful test
    with patch.object(groq_service, "test_connection", return_value={
        "success": True,
        "provider": "groq",
        "message": "Successfully verified live Groq API connection (llama-3.3-70b-versatile)!",
        "response": "Groq connected",
        "model": "llama-3.3-70b-versatile"
    }):
        res = client.post("/api/settings/test-groq", json={"api_key": "gsk_test123"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "Groq connected" in data["response"]

    # 3. Invalid key error
    with patch.object(groq_service, "test_connection", side_effect=AIConfigurationError("Invalid API key", provider="groq")):
        res = client.post("/api/settings/test-groq", json={"api_key": "gsk_invalid"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert "Authentication Error" in data["error"]
