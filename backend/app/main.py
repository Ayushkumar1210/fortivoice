import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date, timedelta

from app.core.config import settings
from app.core.database import db_manager
from app.api import leads, appointments, calls, voice, rag, analytics, settings as settings_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fortivoice")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to DB & seed sample leads if empty
    logger.info("Initializing FortiVoice Backend...")
    await db_manager.connect(settings.MONGODB_URI, settings.MONGODB_DB_NAME)
    
    # Check if we should seed sample CRM data
    lead_count = await db_manager.count("leads")
    if lead_count == 0:
        logger.info("Seeding initial enterprise CRM leads and appointments...")
        await seed_initial_data()

    yield

    # Shutdown
    await db_manager.close()
    logger.info("FortiVoice Backend shutdown complete.")


app = FastAPI(
    title="FORTIVOICE – Autonomous AI Sales Voice Agent & Smart CRM API",
    description="Enterprise voice AI agent, RAG semantic search, lead qualification, and CRM platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits all localhost / staging frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(voice.router)
app.include_router(leads.router)
app.include_router(appointments.router)
app.include_router(calls.router)
app.include_router(rag.router)
app.include_router(analytics.router)
app.include_router(settings_api.router)

@app.get("/")
async def root():
    return {
        "app": "FORTIVOICE",
        "description": "Autonomous AI Sales Voice Agent & Smart CRM",
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db_manager.is_mongo_connected else "local_fallback_active"
    }


async def seed_initial_data():
    today = date.today()
    sample_leads = [
        {
            "name": "Sarah Jenkins",
            "phone": "+1 (555) 234-5678",
            "email": "sjenkins@apexcloud.io",
            "product_interest": "Enterprise Custom Plan",
            "budget": "$4,000 / month",
            "requirements": "Automating 8,000 inbound SaaS qualification calls per month with Salesforce sync.",
            "timeline": "Immediate (within 2 weeks)",
            "status": "HOT",
            "score": 92,
            "score_reasoning": "High budget ($4k/mo), enterprise volume, immediate timeline, demo requested.",
            "sentiment": "Positive",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "name": "Rajesh Sharma",
            "phone": "+91 98112 34567",
            "email": "rajesh@techflow.in",
            "product_interest": "Professional Growth Plan",
            "budget": "$1,500 / month",
            "requirements": "Multilingual customer support in Hindi & English with 24/7 coverage.",
            "timeline": "Within 30 days",
            "status": "WARM",
            "score": 68,
            "score_reasoning": "Good budget fit, evaluated multilingual voice feature, scheduling internal review.",
            "sentiment": "Positive",
            "created_at": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(hours=5)).isoformat()
        },
        {
            "name": "David Martinez",
            "phone": "+1 (555) 876-5432",
            "email": "dmartinez@nexustech.org",
            "product_interest": "Starter Plan",
            "budget": "$400 / month",
            "requirements": "Small e-commerce phone triage, requested discounts.",
            "timeline": "Evaluating next quarter",
            "status": "COLD",
            "score": 35,
            "score_reasoning": "Budget below minimum Starter tier ($499/mo) and purchase timeline is delayed.",
            "sentiment": "Neutral",
            "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        }
    ]

    for lead in sample_leads:
        await db_manager.insert("leads", lead)

    sample_appointments = [
        {
            "customer_name": "Sarah Jenkins",
            "customer_phone": "+1 (555) 234-5678",
            "customer_email": "sjenkins@apexcloud.io",
            "appointment_date": (today + timedelta(days=1)).isoformat(),
            "appointment_time": "14:00",
            "purpose": "Enterprise Architecture & Custom SIP Trunking Demo",
            "status": "Scheduled",
            "notes": "Interested in 8k monthly minutes tier and Salesforce integration.",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "customer_name": "Rajesh Sharma",
            "customer_phone": "+91 98112 34567",
            "customer_email": "rajesh@techflow.in",
            "appointment_date": (today + timedelta(days=2)).isoformat(),
            "appointment_time": "11:30",
            "purpose": "Multilingual Voice AI Discovery Call",
            "status": "Scheduled",
            "notes": "Will test live Hindi speech synthesis and accent recognition.",
            "created_at": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
            "updated_at": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        }
    ]

    for app in sample_appointments:
        await db_manager.insert("appointments", app)

    sample_calls = [
        {
            "call_id": "call-init-001",
            "customer_name": "Sarah Jenkins",
            "customer_phone": "+1 (555) 234-5678",
            "customer_email": "sjenkins@apexcloud.io",
            "duration_seconds": 184,
            "messages": [
                {"sender": "agent", "text": "Hello! I am FortiVoice, your autonomous AI sales specialist. How can I help your business today?"},
                {"sender": "customer", "text": "Hi, we need to automate our inbound SaaS sales qualification calls. We get about 8,000 calls a month. What plan fits?"},
                {"sender": "agent", "text": "Our Enterprise Custom Plan is built specifically for that scale, featuring dedicated VPC deployment, custom CRM synchronization with Salesforce, and SOC-2 compliance."},
                {"sender": "customer", "text": "That sounds great. Can we schedule a demo for tomorrow at 2 PM?"},
                {"sender": "agent", "text": "I would be delighted to schedule that demo for tomorrow at 2:00 PM EST. Sending your confirmation now."}
            ],
            "summary": "Customer Sarah Jenkins from ApexCloud discussed high-volume voice automation (8k calls/mo). Reviewed Enterprise tier capabilities and SOC-2 compliance.",
            "requirements": "8,000 inbound calls/month, Salesforce integration, SOC-2 compliance.",
            "objections": "Inquired about data isolation and enterprise latency guarantees.",
            "lead_qualification": "Enterprise HOT lead. Decision maker with clear budget and volume.",
            "lead_score": 92,
            "lead_status": "HOT",
            "sentiment": "Positive",
            "next_action": "Deliver technical whitepaper and host calendar demo tomorrow at 2:00 PM.",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        }
    ]

    for c in sample_calls:
        await db_manager.insert("calls", c)
