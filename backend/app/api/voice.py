import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status

from app.models.schemas import VoiceChatRequest, VoiceChatResponse
from app.core.exceptions import AIConfigurationError
from app.services.rag_service import rag_service
from app.services.gemini_service import gemini_service
from app.services.lead_service import lead_service
from app.services.appointment_service import appointment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice Assistant"])

@router.post("/interact", response_model=VoiceChatResponse)
async def voice_interaction(req: VoiceChatRequest):
    """
    Main conversational pipeline:
    1. Semantic retrieval from knowledge base (RAG)
    2. Context-aware prompt execution via Gemini LLM
    3. Lead attribute extraction & score classification
    4. Sentiment analysis
    5. Automatic appointment booking if intent detected
    6. Lead record persistence in CRM database
    """
    # 1. RAG retrieval
    rag_sources = rag_service.query(req.message, top_k=3)
    rag_context = "\n---\n".join([f"Source ({s.get('metadata', {}).get('source', 'Company Doc')}): {s['text']}" for s in rag_sources])

    # 2. Unified AI conversational generation (Gemini -> Groq -> Local Demo)
    try:
        ai_output = await gemini_service.generate_voice_response(
            user_message=req.message,
            conversation_history=req.conversation_history or [],
            rag_context=rag_context,
            customer_profile=req.customer_profile or {},
            language=req.language or "en"
        )
    except AIConfigurationError as auth_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(auth_err)
        )

    reply_text = ai_output.get("reply_text", "Thank you for contacting FortiVoice. How can I assist your business further?")
    sentiment = ai_output.get("sentiment", "Neutral")
    sentiment_score = ai_output.get("sentiment_score", 0.0)
    lead_score = ai_output.get("lead_score", 50)
    lead_status = ai_output.get("lead_status", "WARM")
    score_reasoning = ai_output.get("score_reasoning", "Standard lead interaction.")
    extracted_lead = ai_output.get("extracted_lead", {})
    appointment_intent = ai_output.get("appointment_intent", {})

    # 3. Check and auto-book appointment if intent detected
    if appointment_intent and appointment_intent.get("requested"):
        pref_date = appointment_intent.get("preferred_date")
        pref_time = appointment_intent.get("preferred_time") or "11:00 AM"
        cust_name = extracted_lead.get("name") or (req.customer_profile or {}).get("name") or "Inbound Voice Prospect"
        cust_phone = extracted_lead.get("phone") or (req.customer_profile or {}).get("phone")
        cust_email = extracted_lead.get("email") or (req.customer_profile or {}).get("email")

        if pref_date:
            try:
                await appointment_service.create_appointment({
                    "customer_name": cust_name,
                    "customer_phone": cust_phone,
                    "customer_email": cust_email,
                    "appointment_date": pref_date,
                    "appointment_time": pref_time,
                    "purpose": appointment_intent.get("purpose") or "FortiVoice Product Demo Consultation",
                    "status": "Scheduled",
                    "notes": f"Automatically booked via Voice Assistant. Session: {req.session_id}"
                })
                # Bump lead score on successful appointment
                lead_score = min(98, max(85, lead_score + 15))
                lead_status = "HOT"
                score_reasoning += " (VIP Demo Consultation booked)"
            except Exception as e:
                logger.warning(f"Could not auto-create appointment: {e}")

    # 4. Upsert lead in CRM
    saved_lead = await lead_service.upsert_from_voice_session(
        extracted_info=extracted_lead,
        score=lead_score,
        status=lead_status,
        reasoning=score_reasoning,
        sentiment=sentiment,
        session_id=req.session_id
    )

    # 5. Clean reply text for TTS Speech (ensure no stray Markdown formatting)
    clean_speech = reply_text.replace("*", "").replace("#", "").replace("`", "")

    return VoiceChatResponse(
        session_id=req.session_id,
        reply_text=reply_text,
        speech_text=clean_speech,
        language=req.language or "en",
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        extracted_lead=saved_lead or extracted_lead,
        lead_score=lead_score,
        lead_status=lead_status,
        appointment_intent=appointment_intent,
        rag_sources=rag_sources,
        engine_mode=ai_output.get("engine_mode", "local_demo"),
        provider=ai_output.get("provider", "local_demo")
    )


# WebSocket connection manager for live stream / real-time events
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def voice_websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "ping":
                await websocket.send_json({"action": "pong", "session_id": session_id})
            elif action == "transcript_update":
                # Broadcast live partial speech recognized from browser
                await websocket.send_json({
                    "action": "transcript_received",
                    "text": payload.get("text", ""),
                    "is_final": payload.get("is_final", False)
                })
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(session_id)
