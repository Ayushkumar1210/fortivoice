from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

@router.get("", response_model=List[AppointmentResponse])
async def list_appointments(
    status: Optional[str] = Query(None, description="Scheduled, Completed, Cancelled"),
    limit: int = Query(100, ge=1, le=500)
):
    return await appointment_service.get_all_appointments(status=status, limit=limit)

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: str):
    appointment = await appointment_service.get_appointment_by_id(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(app_in: AppointmentCreate):
    try:
        created = await appointment_service.create_appointment(app_in.dict())
        return created
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(appointment_id: str, app_in: AppointmentUpdate):
    updated = await appointment_service.update_appointment(appointment_id, app_in.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return updated

@router.delete("/{appointment_id}")
async def delete_appointment(appointment_id: str):
    success = await appointment_service.delete_appointment(appointment_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return {"message": "Appointment deleted successfully", "id": appointment_id}
