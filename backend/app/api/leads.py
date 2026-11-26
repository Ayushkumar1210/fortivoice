from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import LeadCreate, LeadUpdate, LeadResponse
from app.services.lead_service import lead_service

router = APIRouter(prefix="/api/leads", tags=["Leads"])

@router.get("", response_model=List[LeadResponse])
async def list_leads(
    status: Optional[str] = Query(None, description="Filter by HOT, WARM, or COLD"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    limit: int = Query(100, ge=1, le=500)
):
    return await lead_service.get_all_leads(status=status, search=search, limit=limit)

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str):
    lead = await lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead

@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(lead_in: LeadCreate):
    created = await lead_service.create_lead(lead_in.dict())
    return created

@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: str, lead_in: LeadUpdate):
    updated = await lead_service.update_lead(lead_id, lead_in.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return updated

@router.delete("/{lead_id}")
async def delete_lead(lead_id: str):
    success = await lead_service.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return {"message": "Lead deleted successfully", "id": lead_id}
