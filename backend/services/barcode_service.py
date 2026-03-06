"""
Barcode generation service.
Generates short, scannable barcodes at parcel intake.
Also handles legacy barcode formats and invoice numbering.
"""
from database import db
from datetime import datetime, timezone
from typing import Optional
import random
import string


def generate_barcode(trip_number: Optional[str], shipment_seq: int, piece_number: int) -> str:
    """
    Generate barcode in format: [trip_number]-[shipment_seq]-[piece_number] or TEMP-[random]
    (Legacy function for trip-based barcodes)
    
    Args:
        trip_number: Trip number (e.g., "S27") or None for temp barcode
        shipment_seq: Shipment sequence number (zero-padded to 3 digits)
        piece_number: Piece number within shipment (zero-padded to 2 digits)
    
    Returns:
        Barcode string (e.g., "S27-001-01" or "TEMP-123456")
    """
    if trip_number:
        return f"{trip_number}-{shipment_seq:03d}-{piece_number:02d}"
    else:
        random_digits = ''.join(random.choices(string.digits, k=6))
        return f"TEMP-{random_digits}"


async def generate_invoice_number(tenant_id: str) -> str:
    """
    Generate invoice number in format: INV-YYYY-NNN
    
    Args:
        tenant_id: Tenant ID to scope invoice numbering
    
    Returns:
        Invoice number string (e.g., "INV-2026-001")
    """
    current_year = datetime.now(timezone.utc).year
    
    # Find the highest invoice number for this tenant this year
    pattern = f"INV-{current_year}-"
    last_invoice = await db.invoices.find_one(
        {"tenant_id": tenant_id, "invoice_number": {"$regex": f"^{pattern}"}},
        {"_id": 0, "invoice_number": 1},
        sort=[("invoice_number", -1)]
    )
    
    if last_invoice:
        # Extract the sequence number and increment
        last_num = int(last_invoice["invoice_number"].split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    
    return f"INV-{current_year}-{next_num:03d}"


async def generate_parcel_barcode(tenant_id: str) -> str:
    """
    Generate short sequential barcode.
    Format: SX######## (10 characters - SX + 8 digits)
    NEVER resets - permanent sequential counter.

    Examples:
    - SX00000001 (Parcel 1)
    - SX00000347 (Parcel 347)
    - SX99999999 (Max)
    """
    # Counter key WITHOUT year - permanent sequential, never resets
    counter_key = f"parcel_barcode_{tenant_id}"

    # Atomic increment
    counter_doc = await db.counters.find_one_and_update(
        {"key": counter_key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True
    )

    sequence = counter_doc["value"]

    # Check capacity (99,999,999 parcels max)
    if sequence > 99999999:
        raise ValueError(
            "Barcode capacity exceeded. Contact support to extend format."
        )

    # Build barcode: SX00000001 (SX + 8 digits)
    barcode = f"SX{sequence:08d}"

    # Verify uniqueness (should never happen with atomic counter, but safety check)
    existing = await db.shipments.find_one({
        "barcode": barcode,
        "tenant_id": tenant_id
    })

    if existing:
        # Collision detected - retry
        print(f"WARNING: Barcode collision detected for {barcode}. Retrying.")
        return await generate_parcel_barcode(tenant_id)

    return barcode


async def generate_parcel_barcode_warehouse(tenant_id: str, warehouse_id: str) -> str:
    """
    Generate barcode with warehouse prefix.
    Format: W####### (8 characters)

    Examples:
    - J0000001 (Johannesburg, Parcel 1)
    - N0000001 (Nairobi, Parcel 1)
    """
    # Get warehouse code
    warehouse = await db.warehouses.find_one({"id": warehouse_id, "tenant_id": tenant_id})
    if not warehouse:
        raise ValueError("Warehouse not found")

    warehouse_code = warehouse.get("code", "X")  # Fallback if code is missing

    # Counter per warehouse per year
    current_year = datetime.now(timezone.utc).year
    counter_key = f"parcel_barcode_{tenant_id}_{warehouse_code}_{current_year}"

    counter_doc = await db.counters.find_one_and_update(
        {"key": counter_key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True
    )

    sequence = counter_doc["value"]

    # Build barcode: J0000001
    barcode = f"{warehouse_code}{sequence:07d}"

    return barcode
