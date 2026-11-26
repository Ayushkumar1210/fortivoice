import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.gemini_service import gemini_service

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "FORTIVOICE"

def test_leads_crud():
    # 1. Create a lead
    new_lead = {
        "name": "Marcus Vance",
        "phone": "+1 (555) 345-6789",
        "email": "marcus@vancetech.io",
        "product_interest": "Enterprise Custom Plan",
        "budget": "$5,000 / month",
        "requirements": "Automating 10k inbound enterprise calls/month",
        "timeline": "Immediate",
        "status": "HOT",
        "score": 95,
        "score_reasoning": "High budget and enterprise volume",
        "sentiment": "Positive"
    }
    create_res = client.post("/api/leads", json=new_lead)
    assert create_res.status_code == 201
    lead_data = create_res.json()
    lead_id = lead_data["id"]
    assert lead_data["name"] == "Marcus Vance"
    assert lead_data["status"] == "HOT"

    # 2. Get the lead by ID
    get_res = client.get(f"/api/leads/{lead_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Marcus Vance"

    # 3. Update the lead
    update_res = client.put(f"/api/leads/{lead_id}", json={"budget": "$6,000 / month"})
    assert update_res.status_code == 200
    assert update_res.json()["budget"] == "$6,000 / month"

    # 4. List leads
    list_res = client.get("/api/leads?status=HOT")
    assert list_res.status_code == 200
    assert any(l["id"] == lead_id for l in list_res.json())

def test_appointments_crud():
    # Create appointment
    app_payload = {
        "customer_name": "Marcus Vance",
        "customer_phone": "+1 (555) 345-6789",
        "customer_email": "marcus@vancetech.io",
        "appointment_date": "2026-12-01",
        "appointment_time": "15:00",
        "purpose": "Enterprise Architecture Review",
        "status": "Scheduled"
    }
    create_res = client.post("/api/appointments", json=app_payload)
    assert create_res.status_code == 201
    app_data = create_res.json()
    app_id = app_data["id"]
    assert app_data["customer_name"] == "Marcus Vance"

    # List appointments
    list_res = client.get("/api/appointments")
    assert list_res.status_code == 200
    assert len(list_res.json()) > 0

    # Update appointment status
    upd_res = client.put(f"/api/appointments/{app_id}", json={"status": "Completed"})
    assert upd_res.status_code == 200
    assert upd_res.json()["status"] == "Completed"

def test_rag_query():
    # Test semantic retrieval on default pre-seeded enterprise playbook
    res = client.post("/api/rag/query", json={"query": "What is the pricing for Starter plan?", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert len(data["results"]) > 0
    # Check that retrieved content contains pricing info
    found_pricing = any("499" in r["text"] or "Starter" in r["text"] for r in data["results"])
    assert found_pricing

def test_voice_interaction_flow():
    # End-to-End Voice Interaction (Local Heuristic Pipeline)
    # Customer asks about pricing and schedules demo
    session_id = "test-session-voice-001"
    
    with patch.object(gemini_service, "is_configured", return_value=False):
        # Turn 1: Product & pricing inquiry
        payload_1 = {
            "session_id": session_id,
            "message": "Hi, my name is Alex Mercer. Can you tell me how much the Starter plan costs and what it includes?",
            "language": "en"
        }
        res_1 = client.post("/api/voice/interact", json=payload_1)
        assert res_1.status_code == 200
        data_1 = res_1.json()
        assert "reply_text" in data_1
        assert "speech_text" in data_1
        assert data_1["lead_score"] >= 40
        assert data_1["extracted_lead"] is not None
        assert "Alex Mercer" in (data_1["extracted_lead"].get("name") or "")

        # Turn 2: Booking Demo with phone and email
        payload_2 = {
            "session_id": session_id,
            "message": "That sounds great! I would like to book a demo for next Friday at 2 PM. My email is alex@mercer.com and phone is +1-555-987-6543.",
            "language": "en",
            "customer_profile": data_1["extracted_lead"]
        }
        res_2 = client.post("/api/voice/interact", json=payload_2)
        assert res_2.status_code == 200
        data_2 = res_2.json()
        assert data_2["lead_score"] >= 75  # Boosted for booking intent and details
        assert data_2["lead_status"] == "HOT"
        assert data_2["sentiment"] == "Positive"

    # Verify that appointment was booked in database
    appointments_res = client.get("/api/appointments")
    assert appointments_res.status_code == 200
    alex_apps = [a for a in appointments_res.json() if "Alex" in a.get("customer_name", "")]
    assert len(alex_apps) > 0

def test_voice_interaction_with_gemini_mock():
    # Test that when Gemini API is configured, the response from Gemini is used
    mock_gemini_json = """{
        "reply_text": "Welcome to FortiVoice! Our Enterprise plan is ideal for your scale.",
        "extracted_lead": {
            "name": "Evelyn Reed",
            "phone": "+1-800-555-0199",
            "email": "evelyn@techcorp.com",
            "product_interest": "Enterprise Custom Plan",
            "budget": "$10,000 / month",
            "requirements": "Global telephony with SIP integration",
            "timeline": "Immediate"
        },
        "sentiment": "Positive",
        "sentiment_score": 0.95,
        "lead_score": 96,
        "lead_status": "HOT",
        "score_reasoning": "Enterprise budget and immediate global rollout.",
        "appointment_intent": {
            "requested": true,
            "preferred_date": "2026-12-05",
            "preferred_time": "14:00",
            "purpose": "Global Architecture Discovery"
        }
    }"""
    mock_response = MagicMock()
    mock_response.text = mock_gemini_json

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch("google.generativeai.GenerativeModel", return_value=mock_model), \
         patch.object(gemini_service, "is_configured", return_value=True):
        
        payload = {
            "session_id": "test-gemini-mock-session",
            "message": "My name is Evelyn Reed from TechCorp. We need enterprise global telephony for $10,000/month.",
            "language": "en"
        }
        res = client.post("/api/voice/interact", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["reply_text"] == "Welcome to FortiVoice! Our Enterprise plan is ideal for your scale."
        assert data["lead_score"] >= 95
        assert data["lead_status"] == "HOT"
        assert data["extracted_lead"]["name"] == "Evelyn Reed"
        assert data["extracted_lead"]["budget"] == "$10,000 / month"

def test_call_summary():
    # Test post-call summary generation
    session_id = "test-call-summary-001"
    summary_req = {
        "session_id": session_id,
        "messages": [
            {"sender": "agent", "text": "Hello, how can I help you?"},
            {"sender": "customer", "text": "We need to automate 5,000 inbound sales calls with Salesforce integration."},
            {"sender": "agent", "text": "Our Pro plan supports 5,000 minutes and includes native Salesforce sync."},
            {"sender": "customer", "text": "Awesome, book a demo for tomorrow."}
        ],
        "customer_profile": {
            "name": "Jordan Hayes",
            "budget": "$1,500 / month"
        }
    }
    with patch.object(gemini_service, "is_configured", return_value=False):
        res = client.post("/api/calls/summary", json=summary_req)
        assert res.status_code == 200
        summary_data = res.json()
        assert "summary" in summary_data
        assert "requirements" in summary_data
        assert "next_action" in summary_data
        assert summary_data["lead_status"] == "HOT"

def test_dashboard_analytics():
    res = client.get("/api/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["total_leads"] > 0
    assert "sentiment_breakdown" in data
    assert "recent_activities" in data

def test_settings_api():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "gemini" in data
    assert "database" in data
    assert "rag" in data

def test_settings_test_gemini_unconfigured():
    # With no key configured, test endpoint returns helpful clear instructions
    from app.core.config import settings
    with patch.object(gemini_service, "api_key", ""), \
         patch.object(settings, "GEMINI_API_KEY", ""), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
        res = client.post("/api/settings/test-gemini", json={})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert "not configured" in data["message"]

def test_settings_test_gemini_with_mock_key():
    mock_res = MagicMock()
    mock_res.text = "Connection successful"
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_res

    with patch("google.generativeai.configure") as mock_configure, \
         patch("google.generativeai.GenerativeModel", return_value=mock_model):
        
        res = client.post("/api/settings/test-gemini", json={
            "api_key": "AIzaSyFakeKeyForTestingPurposes12345",
            "model": "gemini-1.5-flash"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["response"] == "Connection successful"
        mock_configure.assert_called_with(api_key="AIzaSyFakeKeyForTestingPurposes12345")
