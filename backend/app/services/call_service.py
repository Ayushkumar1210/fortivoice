import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.database import db_manager
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)

class CallService:
    def __init__(self):
        self.collection = "calls"

    async def get_all_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        return await db_manager.get_all(self.collection, sort_field="created_at", limit=limit)

    async def get_call_by_id(self, call_id: str) -> Optional[Dict[str, Any]]:
        return await db_manager.get_by_id(self.collection, call_id)

    async def save_call_session(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(call_data)
        doc_id = await db_manager.insert(self.collection, data)
        return await self.get_call_by_id(doc_id) or {**data, "_id": doc_id}

    async def end_call_and_generate_summary(
        self,
        call_id: str,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None,
        duration_seconds: int = 0
    ) -> Dict[str, Any]:
        """Generates AI summary, calculates final qualification, and persists in MongoDB"""
        summary_result = await gemini_service.generate_call_summary(messages, customer_profile)
        
        customer_name = (customer_profile or {}).get("name") or "Inbound Caller"
        customer_phone = (customer_profile or {}).get("phone")
        customer_email = (customer_profile or {}).get("email")

        call_record = {
            "call_id": call_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "duration_seconds": duration_seconds,
            "messages": messages,
            "summary": summary_result.get("summary"),
            "requirements": summary_result.get("customer_requirements") or summary_result.get("requirements"),
            "objections": summary_result.get("customer_objections") or summary_result.get("objections"),
            "lead_qualification": summary_result.get("lead_qualification"),
            "lead_score": summary_result.get("lead_score"),
            "lead_status": summary_result.get("lead_status"),
            "sentiment": summary_result.get("sentiment"),
            "next_action": summary_result.get("recommended_next_action") or summary_result.get("next_action"),
            "customer_requirements": summary_result.get("customer_requirements") or summary_result.get("requirements"),
            "customer_objections": summary_result.get("customer_objections") or summary_result.get("objections"),
            "recommended_next_action": summary_result.get("recommended_next_action") or summary_result.get("next_action"),
            "engine_mode": summary_result.get("engine_mode", "local_demo"),
            "provider": summary_result.get("provider", "local_demo"),
            "created_at": datetime.utcnow().isoformat()
        }

        # Check if call already exists
        existing = await db_manager.get_all(self.collection, query={"call_id": call_id})
        if existing:
            rec_id = str(existing[0]["_id"])
            await db_manager.update(self.collection, rec_id, call_record)
            saved = await self.get_call_by_id(rec_id)
        else:
            rec_id = await db_manager.insert(self.collection, call_record)
            saved = await self.get_call_by_id(rec_id)

        return saved or {**call_record, "_id": rec_id}


call_service = CallService()
