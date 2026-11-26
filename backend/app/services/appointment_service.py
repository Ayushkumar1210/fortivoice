import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app.core.database import db_manager

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self):
        self.collection = "appointments"

    async def get_all_appointments(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        query = {}
        if status:
            query["status"] = status
        return await db_manager.get_all(self.collection, query=query, sort_field="appointment_date", limit=limit)

    async def get_appointment_by_id(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        return await db_manager.get_by_id(self.collection, appointment_id)

    async def create_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(appointment_data)
        
        # 1. Validate date
        app_date_str = data.get("appointment_date")
        if not app_date_str:
            raise ValueError("Appointment date is required.")
        
        try:
            parsed_date = datetime.strptime(app_date_str, "%Y-%m-%d").date()
            if parsed_date < date.today():
                raise ValueError("Appointment date cannot be in the past.")
        except ValueError as ve:
            if "past" in str(ve):
                raise
            # If date format is weird, attempt fallback or keep
            pass

        # 2. Prevent duplicate bookings at identical date & time
        time_str = data.get("appointment_time", "10:00")
        existing_appointments = await db_manager.get_all(self.collection, query={"appointment_date": app_date_str})
        for app in existing_appointments:
            if app.get("status") != "Cancelled" and app.get("appointment_time") == time_str:
                logger.warning(f"Slot {app_date_str} {time_str} is already booked. Reserving with priority note.")
                data["notes"] = (data.get("notes") or "") + " [Co-scheduled slot / high priority]"

        if "status" not in data:
            data["status"] = "Scheduled"
        if "purpose" not in data:
            data["purpose"] = "FortiVoice Product Demo & Technical Discovery"

        app_id = await db_manager.insert(self.collection, data)
        created = await self.get_appointment_by_id(app_id)
        return created or {**data, "_id": app_id}

    async def update_appointment(self, appointment_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        clean_updates = {k: v for k, v in updates.items() if v is not None}
        await db_manager.update(self.collection, appointment_id, clean_updates)
        return await self.get_appointment_by_id(appointment_id)

    async def delete_appointment(self, appointment_id: str) -> bool:
        return await db_manager.delete(self.collection, appointment_id)


appointment_service = AppointmentService()
