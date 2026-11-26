from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator

# --- Lead Models ---
class LeadBase(BaseModel):
    name: Optional[str] = "Anonymous Lead"
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    product_interest: Optional[str] = None
    budget: Optional[str] = None
    requirements: Optional[str] = None
    timeline: Optional[str] = None
    status: str = Field(default="WARM", description="HOT, WARM, or COLD")
    score: int = Field(default=50, ge=0, le=100)
    score_reasoning: Optional[str] = None
    sentiment: str = Field(default="Neutral", description="Positive, Neutral, or Negative")

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    product_interest: Optional[str] = None
    budget: Optional[str] = None
    requirements: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None
    score_reasoning: Optional[str] = None
    sentiment: Optional[str] = None

class LeadResponse(LeadBase):
    id: str
    _id: Optional[str] = None
    created_at: str
    updated_at: str

    @model_validator(mode="before")
    @classmethod
    def set_id_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_id = str(data.get("id") or data.get("_id") or "")
            data["id"] = raw_id
            data["_id"] = raw_id
        return data


# --- Appointment Models ---
class AppointmentBase(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    appointment_date: str  # YYYY-MM-DD
    appointment_time: str  # HH:MM or format like "14:00"
    purpose: Optional[str] = "Product Demo & Sales Consultation"
    status: str = Field(default="Scheduled", description="Scheduled, Completed, Cancelled")
    notes: Optional[str] = None
    lead_id: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    status: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: str
    _id: Optional[str] = None
    created_at: str
    updated_at: str

    @model_validator(mode="before")
    @classmethod
    def set_id_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_id = str(data.get("id") or data.get("_id") or "")
            data["id"] = raw_id
            data["_id"] = raw_id
        return data


# --- Call & Conversation Models ---
class ChatMessage(BaseModel):
    sender: str = Field(description="customer or agent or system")
    text: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    sentiment: Optional[str] = None

class CallBase(BaseModel):
    call_id: str
    customer_name: Optional[str] = "Customer"
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    duration_seconds: int = 0
    messages: List[ChatMessage] = []
    summary: Optional[str] = None
    requirements: Optional[str] = None
    objections: Optional[str] = None
    lead_qualification: Optional[str] = None
    lead_score: Optional[int] = None
    lead_status: Optional[str] = None
    sentiment: Optional[str] = "Neutral"
    next_action: Optional[str] = None
    customer_requirements: Optional[str] = None
    customer_objections: Optional[str] = None
    recommended_next_action: Optional[str] = None
    booked_appointment: Optional[Dict[str, Any]] = None
    engine_mode: Optional[str] = "local_demo"
    provider: Optional[str] = "local_demo"

class CallCreate(CallBase):
    pass

class CallResponse(CallBase):
    id: str
    _id: Optional[str] = None
    created_at: str

    @model_validator(mode="before")
    @classmethod
    def set_id_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_id = str(data.get("id") or data.get("_id") or "")
            data["id"] = raw_id
            data["_id"] = raw_id
        return data


# --- Voice / Conversational API Models ---
class VoiceChatRequest(BaseModel):
    session_id: str
    message: str
    language: str = "en"  # "en" or "hi"
    customer_profile: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

class VoiceChatResponse(BaseModel):
    session_id: str
    reply_text: str
    speech_text: str
    language: str
    sentiment: str  # Positive, Neutral, Negative
    sentiment_score: float  # -1.0 to 1.0
    extracted_lead: Optional[Dict[str, Any]] = None
    lead_score: Optional[int] = None
    lead_status: Optional[str] = None
    appointment_intent: Optional[Dict[str, Any]] = None
    rag_sources: List[Dict[str, Any]] = []
    engine_mode: Optional[str] = "local_demo"
    provider: Optional[str] = "local_demo"


# --- Call Summary Request & Response ---
class GenerateSummaryRequest(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    customer_profile: Optional[Dict[str, Any]] = None

class GenerateSummaryResponse(BaseModel):
    summary: str
    customer_requirements: str
    customer_objections: str
    lead_qualification: str
    lead_score: int
    lead_status: str  # HOT, WARM, COLD
    score_reasoning: str
    sentiment: str
    recommended_next_action: str


# --- RAG Models ---
class DocumentItem(BaseModel):
    id: str
    _id: Optional[str] = None
    filename: str
    file_type: str
    chunk_count: int
    file_size_kb: float
    uploaded_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def set_id_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_id = str(data.get("id") or data.get("_id") or "")
            data["id"] = raw_id
            data["_id"] = raw_id
        return data

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 4

class RAGQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]


# --- Dashboard Analytics ---
class DashboardAnalytics(BaseModel):
    total_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    total_conversations: int
    upcoming_appointments: int
    conversion_rate: float
    average_lead_score: float
    sentiment_breakdown: Dict[str, int]
    recent_activities: List[Dict[str, Any]]
