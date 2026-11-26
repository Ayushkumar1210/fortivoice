from typing import Dict, Any, List
from fastapi import APIRouter
from datetime import datetime, date

from app.models.schemas import DashboardAnalytics
from app.core.database import db_manager

router = APIRouter(prefix="/api/analytics", tags=["Dashboard Analytics"])

@router.get("/dashboard", response_model=DashboardAnalytics)
async def get_dashboard_metrics():
    # 1. Fetch leads
    leads = await db_manager.get_all("leads", limit=500)
    total_leads = len(leads)
    hot_leads = sum(1 for l in leads if str(l.get("status", "")).upper() == "HOT")
    warm_leads = sum(1 for l in leads if str(l.get("status", "")).upper() == "WARM")
    cold_leads = sum(1 for l in leads if str(l.get("status", "")).upper() == "COLD")

    scores = [int(l.get("score", 50)) for l in leads if l.get("score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 50.0

    # 2. Fetch calls
    calls = await db_manager.get_all("calls", limit=500)
    total_conversations = len(calls)

    # 3. Fetch appointments
    today_str = date.today().isoformat()
    appointments = await db_manager.get_all("appointments", limit=500)
    upcoming_appointments = sum(
        1 for a in appointments
        if a.get("status") == "Scheduled" and str(a.get("appointment_date", "")) >= today_str
    )

    # 4. Conversion rate (Leads with appointment or HOT / Total leads)
    conversion_rate = round((hot_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    # 5. Sentiment breakdown
    sentiment_breakdown = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for l in leads:
        sent = (l.get("sentiment") or "Neutral").capitalize()
        if sent in sentiment_breakdown:
            sentiment_breakdown[sent] += 1
        else:
            sentiment_breakdown["Neutral"] += 1

    # 6. Recent activities log
    activities = []
    for l in leads[:4]:
        activities.append({
            "type": "lead_created",
            "title": f"Lead qualified: {l.get('name', 'Prospect')}",
            "subtitle": f"{l.get('status')} lead • Score: {l.get('score', 50)}/100",
            "timestamp": l.get("created_at")
        })
    for a in appointments[:3]:
        activities.append({
            "type": "appointment_scheduled",
            "title": f"Demo booked: {a.get('customer_name', 'Customer')}",
            "subtitle": f"Date: {a.get('appointment_date')} at {a.get('appointment_time')}",
            "timestamp": a.get("created_at")
        })
    for c in calls[:3]:
        activities.append({
            "type": "call_completed",
            "title": f"Call summary: {c.get('customer_name', 'Inbound Caller')}",
            "subtitle": f"Sentiment: {c.get('sentiment')} • Next: {c.get('next_action', 'Follow up')[:40]}...",
            "timestamp": c.get("created_at")
        })

    activities.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)

    return DashboardAnalytics(
        total_leads=total_leads,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        total_conversations=total_conversations,
        upcoming_appointments=upcoming_appointments,
        conversion_rate=conversion_rate,
        average_lead_score=avg_score,
        sentiment_breakdown=sentiment_breakdown,
        recent_activities=activities[:10]
    )
