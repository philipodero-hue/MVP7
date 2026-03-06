"""
Email alert configuration routes for Servex Holdings.
SESSION R: 4-hour smart emails.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime, timezone, timedelta
import logging
import asyncio

from database import db
from dependencies import get_current_user, get_tenant_id
from services.email_service import send_warehouse_summary_email

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/settings/email-alerts")
async def get_email_alert_settings(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get email alert configuration for this tenant."""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    config = tenant.get("email_alerts", {})
    return {
        "enabled": config.get("enabled", False),
        "recipient_email": config.get("recipient_email", ""),
        "smtp_host": config.get("smtp_host", ""),
        "smtp_port": config.get("smtp_port", 587),
        "smtp_user": config.get("smtp_user", ""),
        "smtp_password": config.get("smtp_password", ""),
        "smtp_from": config.get("smtp_from", ""),
        "interval_hours": config.get("interval_hours", 4),
        "last_sent_at": config.get("last_sent_at"),
    }


@router.put("/settings/email-alerts")
async def update_email_alert_settings(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update email alert configuration."""
    allowed = {"enabled", "recipient_email", "smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from", "interval_hours"}
    update = {k: v for k, v in data.items() if k in allowed}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"email_alerts": update}},
        upsert=False
    )
    return {"message": "Email alert settings updated", "settings": update}


@router.post("/settings/email-alerts/test")
async def test_email_alert(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Send a test email to verify SMTP configuration."""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    config = (tenant or {}).get("email_alerts", {})

    smtp_host = data.get("smtp_host") or config.get("smtp_host", "")
    smtp_port = int(data.get("smtp_port") or config.get("smtp_port", 587))
    smtp_user = data.get("smtp_user") or config.get("smtp_user", "")
    smtp_password = data.get("smtp_password") or config.get("smtp_password", "")
    smtp_from = data.get("smtp_from") or config.get("smtp_from", smtp_user)
    recipient_email = data.get("recipient_email") or config.get("recipient_email", "")

    if not smtp_host or not recipient_email:
        raise HTTPException(status_code=400, detail="smtp_host and recipient_email are required")

    # Send test with a dummy parcel
    test_parcels = [{
        "barcode": "SX00000001",
        "client_name": "Test Client",
        "recipient": "Test Recipient",
        "description": "Test Item",
        "category": "Test",
        "total_weight": 1.5,
        "destination": "Test Destination",
        "trip_number": "J-01-26",
        "status": "warehouse",
        "created_at": datetime.now(timezone.utc).isoformat()
    }]

    success = await asyncio.to_thread(
        send_warehouse_summary_email,
        smtp_host, smtp_port, smtp_user, smtp_password, smtp_from,
        recipient_email, test_parcels, tenant.get("company_name", "Servex")
    )

    if success:
        return {"message": f"Test email sent to {recipient_email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check SMTP configuration.")


@router.post("/settings/email-alerts/send-now")
async def trigger_email_alert_now(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Manually trigger warehouse summary email for last 4 hours."""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    config = (tenant or {}).get("email_alerts", {})

    if not config.get("enabled"):
        raise HTTPException(status_code=400, detail="Email alerts are not enabled")

    smtp_host = config.get("smtp_host", "")
    smtp_port = int(config.get("smtp_port", 587))
    smtp_user = config.get("smtp_user", "")
    smtp_password = config.get("smtp_password", "")
    smtp_from = config.get("smtp_from", smtp_user)
    recipient_email = config.get("recipient_email", "")

    if not smtp_host or not recipient_email:
        raise HTTPException(status_code=400, detail="SMTP configuration incomplete")

    # Fetch parcels added in last 4 hours
    hours_back = int(config.get("interval_hours", 4))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()

    parcels = await db.shipments.find(
        {"tenant_id": tenant_id, "created_at": {"$gte": since}},
        {"_id": 0}
    ).to_list(None)

    if not parcels:
        return {"message": "No new parcels in the last 4 hours. Email not sent.", "count": 0}

    success = await asyncio.to_thread(
        send_warehouse_summary_email,
        smtp_host, smtp_port, smtp_user, smtp_password, smtp_from,
        recipient_email, parcels, tenant.get("company_name", "Servex")
    )

    if success:
        # Update last_sent_at
        await db.tenants.update_one(
            {"id": tenant_id},
            {"$set": {"email_alerts.last_sent_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": f"Email sent with {len(parcels)} parcel(s)", "count": len(parcels)}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")
