import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.database import db_manager

logger = logging.getLogger(__name__)

class LeadService:
    def __init__(self):
        self.collection = "leads"

    async def get_all_leads(self, status: Optional[str] = None, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = {}
        if status and status.upper() in ["HOT", "WARM", "COLD"]:
            query["status"] = status.upper()

        leads = await db_manager.get_all(self.collection, query=query, sort_field="created_at", limit=limit)
        
        if search:
            search_lower = search.lower()
            filtered = []
            for lead in leads:
                name = lead.get("name", "").lower()
                company = (lead.get("company") or "").lower()
                email = (lead.get("email") or "").lower()
                phone = (lead.get("phone") or "").lower()
                interest = (lead.get("product_interest") or "").lower()
                if search_lower in name or search_lower in company or search_lower in email or search_lower in phone or search_lower in interest:
                    filtered.append(lead)
            return filtered

        return leads

    async def get_lead_by_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        return await db_manager.get_by_id(self.collection, lead_id)

    async def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(lead_data)
        if "score" not in data or data.get("score") is None:
            data["score"] = 50
        if "status" not in data or not data.get("status"):
            data["status"] = "WARM"
        if "sentiment" not in data or not data.get("sentiment"):
            data["sentiment"] = "Neutral"

        lead_id = await db_manager.insert(self.collection, data)
        created = await self.get_lead_by_id(lead_id)
        return created or {**data, "_id": lead_id}

    async def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        clean_updates = {k: v for k, v in updates.items() if v is not None}
        await db_manager.update(self.collection, lead_id, clean_updates)
        return await self.get_lead_by_id(lead_id)

    async def delete_lead(self, lead_id: str) -> bool:
        return await db_manager.delete(self.collection, lead_id)

    async def upsert_from_voice_session(
        self,
        extracted_info: Dict[str, Any],
        score: int,
        status: str,
        reasoning: str,
        sentiment: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Finds existing lead by session, phone, or email; updates or creates a new record"""
        email = extracted_info.get("email")
        phone = extracted_info.get("phone")
        name = extracted_info.get("name") or "Autonomous Voice Lead"

        existing = None
        all_leads = await db_manager.get_all(self.collection, limit=200)

        for l in all_leads:
            if l.get("session_id") == session_id:
                existing = l
                break
            if email and l.get("email") == email:
                existing = l
                break
            if phone and l.get("phone") == phone:
                existing = l
                break

        lead_payload = {
            "name": name,
            "company": extracted_info.get("company"),
            "phone": phone,
            "email": email,
            "product_interest": extracted_info.get("product_interest"),
            "budget": extracted_info.get("budget"),
            "requirements": extracted_info.get("requirements"),
            "timeline": extracted_info.get("timeline"),
            "score": score,
            "status": status,
            "score_reasoning": reasoning,
            "sentiment": sentiment,
            "session_id": session_id
        }

        if existing:
            # Merge fields
            merged = {**existing}
            for k, v in lead_payload.items():
                if v is not None:
                    merged[k] = v
            await db_manager.update(self.collection, str(existing["_id"]), merged)
            return await self.get_lead_by_id(str(existing["_id"])) or merged
        else:
            lead_id = await db_manager.insert(self.collection, lead_payload)
            return await self.get_lead_by_id(lead_id) or {**lead_payload, "_id": lead_id}


lead_service = LeadService()
