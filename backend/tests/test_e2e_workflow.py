import pytest
import os
import sys
from fastapi.testclient import TestClient

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_complete_e2e_sales_workflow():
    """
    Executes and verifies the full 11-step Sales Demo Workflow:
    1. Start a new sales conversation session.
    2. AI greets customer (voice STT/TTS format).
    3. Customer explains business requirements & company.
    4. AI asks follow-up questions and retrieves RAG knowledge.
    5. AI identifies customer details (Name, Company, Phone, Email, Budget).
    6. AI qualifies lead and assigns readiness score (HOT, WARM, COLD).
    7. AI analyzes customer sentiment (Positive, Neutral, Negative).
    8. AI grounds answers in RAG product knowledge (Pricing, SOC-2).
    9. AI suggests and books demo appointment on customer confirmation.
    10. AI generates executive post-call qualification summary.
    11. CRM dashboard updates with lead, score, sentiment, appointment & summary.
    """
    orig_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "local"
    try:
        session_id = f"e2e-demo-session-{os.getpid()}"

        # -------------------------------------------------------------------
        # Step 1 & 2: Initial Sales Inquiry (Customer introduces company and requirements)
        # -------------------------------------------------------------------
        payload_turn_1 = {
            "session_id": session_id,
            "message": "Hi, my name is Priya Sharma from Apex Global Logistics. We are evaluating FortiVoice to automate 8,000 inbound customer calls per month.",
            "language": "en"
        }

        res_1 = client.post("/api/voice/interact", json=payload_turn_1)
        assert res_1.status_code == 200, f"Turn 1 failed: {res_1.text}"
        data_1 = res_1.json()

        assert "reply_text" in data_1
        assert "speech_text" in data_1
        extracted_1 = data_1["extracted_lead"]
        assert extracted_1 is not None
        assert "Priya" in extracted_1.get("name", "")
        assert "Apex" in (extracted_1.get("company") or "")
        assert data_1["lead_score"] >= 40
        assert data_1["sentiment"] in ["Positive", "Neutral"]
        assert "*" not in data_1["speech_text"]
        assert "#" not in data_1["speech_text"]

        # -------------------------------------------------------------------
        # Step 3 & 4: Commercial & Pricing Discussion with RAG Knowledge Retrieval
        # -------------------------------------------------------------------
        payload_turn_2 = {
            "session_id": session_id,
            "message": "We have a budget of $3,500 per month. How much does your Pro or Enterprise plan cost, and are you SOC-2 compliant?",
            "language": "en",
            "customer_profile": extracted_1
        }

        res_2 = client.post("/api/voice/interact", json=payload_turn_2)
        assert res_2.status_code == 200, f"Turn 2 failed: {res_2.text}"
        data_2 = res_2.json()

        extracted_2 = data_2["extracted_lead"]
        assert extracted_2.get("budget") is not None
        assert len(data_2["rag_sources"]) > 0
        assert "SOC" in data_2["reply_text"] or "plan" in data_2["reply_text"].lower() or "dollar" in data_2["reply_text"].lower() or "$" in data_2["reply_text"]
        assert data_2["lead_score"] >= 60

        # -------------------------------------------------------------------
        # Step 5 & 6: Appointment Intent & Direct Demo Booking
        # -------------------------------------------------------------------
        payload_turn_3 = {
            "session_id": session_id,
            "message": "That sounds perfect! Let's book a VIP demo for Friday at 3 PM. You can reach me at priya@apexlogistics.io or call +1-555-890-1234.",
            "language": "en",
            "customer_profile": extracted_2
        }

        res_3 = client.post("/api/voice/interact", json=payload_turn_3)
        assert res_3.status_code == 200, f"Turn 3 failed: {res_3.text}"
        data_3 = res_3.json()

        extracted_3 = data_3["extracted_lead"]
        assert extracted_3.get("email") == "priya@apexlogistics.io"
        assert "555" in extracted_3.get("phone", "")
        assert data_3["lead_status"] == "HOT"
        assert data_3["lead_score"] >= 75
        assert data_3["sentiment"] == "Positive"
        assert data_3["appointment_intent"]["requested"] is True

        # -------------------------------------------------------------------
        # Step 7: Verify Appointment Saved in CRM Database
        # -------------------------------------------------------------------
        app_res = client.get("/api/appointments")
        assert app_res.status_code == 200
        apps = app_res.json()
        priya_app = next((a for a in apps if "Priya" in a.get("customer_name", "")), None)
        assert priya_app is not None, "Appointment was not automatically saved in CRM database"
        assert priya_app["customer_email"] == "priya@apexlogistics.io"
        assert priya_app["status"] == "Scheduled"

        # -------------------------------------------------------------------
        # Step 8: Verify Lead Saved in CRM Leads Management
        # -------------------------------------------------------------------
        lead_res = client.get("/api/leads?search=Apex")
        assert lead_res.status_code == 200
        leads = lead_res.json()
        assert len(leads) > 0, "Lead was not searchable by company name 'Apex'"
        apex_lead = leads[0]
        assert apex_lead["status"] == "HOT"
        assert "Apex" in apex_lead["company"]

        # -------------------------------------------------------------------
        # Step 9 & 10: End Call & Generate AI Executive Summary
        # -------------------------------------------------------------------
        summary_payload = {
            "session_id": session_id,
            "messages": [
                {"sender": "agent", "text": "Hello! I am FortiVoice. How can I help your business today?"},
                {"sender": "customer", "text": payload_turn_1["message"]},
                {"sender": "agent", "text": data_1["reply_text"]},
                {"sender": "customer", "text": payload_turn_2["message"]},
                {"sender": "agent", "text": data_2["reply_text"]},
                {"sender": "customer", "text": payload_turn_3["message"]},
                {"sender": "agent", "text": data_3["reply_text"]}
            ],
            "customer_profile": extracted_3
        }

        summary_res = client.post("/api/calls/summary", json=summary_payload)
        assert summary_res.status_code == 200, f"Summary creation failed: {summary_res.text}"
        call_record = summary_res.json()
        assert call_record["summary"] is not None
        assert call_record["requirements"] is not None
        assert call_record["next_action"] is not None
        assert call_record["lead_status"] == "HOT"

        # -------------------------------------------------------------------
        # Step 11: Verify CRM Dashboard Analytics Reflect the Interaction
        # -------------------------------------------------------------------
        dash_res = client.get("/api/analytics/dashboard")
        assert dash_res.status_code == 200
        metrics = dash_res.json()
        assert metrics["total_leads"] >= 1
        assert metrics["hot_leads"] >= 1
        assert metrics["upcoming_appointments"] >= 1
        assert metrics["sentiment_breakdown"]["Positive"] >= 1
    finally:
        settings.AI_PROVIDER = orig_provider


def test_hindi_voice_interaction():
    """Verifies natural Hindi voice conversation and qualification flow"""
    orig_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "local"
    try:
        session_id = f"hindi-session-{os.getpid()}"
        payload = {
            "session_id": session_id,
            "message": "Namaste, mujhe pricing janni hai aur demo schedule karna hai.",
            "language": "hi"
        }
        res = client.post("/api/voice/interact", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == "hi"
        assert "reply_text" in data
        assert any(w in data["reply_text"].lower() for w in ["demo", "plan", "hum", "dollar", "aapka", "karein", "baje"])
        assert data["appointment_intent"]["requested"] is True
    finally:
        settings.AI_PROVIDER = orig_provider
