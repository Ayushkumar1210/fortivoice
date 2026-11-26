import logging
from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import CallCreate, CallResponse, GenerateSummaryRequest, GenerateSummaryResponse
from app.core.exceptions import AIConfigurationError
from app.services.call_service import call_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["Calls & Transcripts"])

@router.get("", response_model=List[CallResponse])
async def list_calls(limit: int = Query(100, ge=1, le=500)):
    return await call_service.get_all_calls(limit=limit)

@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: str):
    call = await call_service.get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call record not found")
    return call

@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def save_call(call_in: CallCreate):
    return await call_service.save_call_session(call_in.dict())

@router.post("/summary", response_model=CallResponse)
async def generate_call_summary(req: GenerateSummaryRequest):
    messages_data = [m.dict() for m in req.messages]
    try:
        result = await call_service.end_call_and_generate_summary(
            call_id=req.session_id,
            messages=messages_data,
            customer_profile=req.customer_profile
        )
        return result
    except AIConfigurationError as auth_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(auth_err)
        )
    except Exception as exc:
        logger.error(f"Error generating call summary: {exc}")
        from datetime import datetime
        from app.services.gemini_service import gemini_service
        fallback_data = gemini_service._local_summary_generator(messages_data, req.customer_profile)
        return {
            "id": req.session_id,
            "_id": req.session_id,
            "call_id": req.session_id,
            "customer_name": (req.customer_profile or {}).get("name") or "Inbound Caller",
            "customer_phone": (req.customer_profile or {}).get("phone"),
            "customer_email": (req.customer_profile or {}).get("email"),
            "duration_seconds": 0,
            "messages": messages_data,
            "summary": fallback_data.get("summary"),
            "requirements": fallback_data.get("customer_requirements"),
            "objections": fallback_data.get("customer_objections"),
            "lead_qualification": fallback_data.get("lead_qualification"),
            "lead_score": fallback_data.get("lead_score", 75),
            "lead_status": fallback_data.get("lead_status", "HOT"),
            "sentiment": fallback_data.get("sentiment", "Positive"),
            "next_action": fallback_data.get("recommended_next_action"),
            "customer_requirements": fallback_data.get("customer_requirements"),
            "customer_objections": fallback_data.get("customer_objections"),
            "recommended_next_action": fallback_data.get("recommended_next_action"),
            "engine_mode": "local_demo",
            "provider": "local_demo",
            "created_at": datetime.utcnow().isoformat()
        }
