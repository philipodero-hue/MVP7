"""
Email alert service for Servex Holdings.
Sends 4-hour smart emails with warehouse activity summaries.
"""
import csv
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


def send_warehouse_summary_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    recipient_email: str,
    parcels: list,
    tenant_name: str = "Servex"
) -> bool:
    """
    Send a warehouse summary email with CSV attachment.
    Returns True on success, False on failure.
    """
    try:
        # Build CSV attachment
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Barcode", "Client", "Recipient", "Description", "Category", "Weight (kg)", "Destination", "Trip", "Status", "Created At"])
        for p in parcels:
            writer.writerow([
                p.get("barcode", ""),
                p.get("client_name", ""),
                p.get("recipient", ""),
                p.get("description", ""),
                p.get("category", ""),
                p.get("total_weight", ""),
                p.get("destination", ""),
                p.get("trip_number", ""),
                p.get("status", ""),
                p.get("created_at", "")[:19].replace("T", " ") if p.get("created_at") else ""
            ])
        csv_content = output.getvalue()
        output.close()

        # Build email
        now = datetime.now(timezone.utc)
        subject = f"{tenant_name} Warehouse Update - {len(parcels)} New Parcel(s) - {now.strftime('%d %b %Y %H:%M')} UTC"

        msg = MIMEMultipart("mixed")
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        msg["Subject"] = subject

        body = MIMEText(f"""
Hello,

This is your 4-hour warehouse activity summary.

{len(parcels)} new parcel(s) have been added to the warehouse in the last 4 hours.

Please see the attached CSV for full details.

Summary:
- Total Parcels: {len(parcels)}
- Report Time: {now.strftime('%d %B %Y at %H:%M')} UTC

Regards,
{tenant_name} System
        """.strip(), "plain")
        msg.attach(body)

        # Attach CSV
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(csv_content.encode())
        encoders.encode_base64(attachment)
        filename = f"warehouse_update_{now.strftime('%Y%m%d_%H%M')}.csv"
        attachment.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(attachment)

        # Send via SMTP
        use_ssl = smtp_port == 465
        use_tls = smtp_port in (587, 25)

        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            if use_tls:
                server.starttls()

        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)

        server.sendmail(smtp_from, [recipient_email], msg.as_string())
        server.quit()
        logger.info(f"Warehouse summary email sent to {recipient_email} with {len(parcels)} parcels")
        return True

    except Exception as e:
        logger.error(f"Failed to send warehouse summary email: {e}")
        return False
