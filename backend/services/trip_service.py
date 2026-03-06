"""
Trip service for Servex Holdings backend.
Handles trip-based invoice numbering system (SESSION N Part 1).
"""
import logging
from datetime import datetime, timezone
from database import db

logger = logging.getLogger(__name__)

# Warehouse code mapping
WAREHOUSE_CODES = {
    "nairobi": "N",
    "johannesburg": "J",
    "joburg": "J",
    "jhb": "J",
    "durban": "D",
    "mombasa": "M",
    "cape town": "C",
    "harare": "H",
    "dar es salaam": "D",
}


def get_warehouse_code(warehouse_name: str) -> str:
    """Get warehouse code from warehouse name."""
    if not warehouse_name:
        return "X"
    name_lower = warehouse_name.lower()
    for key, code in WAREHOUSE_CODES.items():
        if key in name_lower:
            return code
    # Fallback: use first letter of warehouse name
    return warehouse_name[0].upper()


async def generate_trip_prefix(tenant_id: str, warehouse_name: str) -> dict:
    """
    Generate a unique trip prefix for a new trip.
    Format: {Warehouse_Code}-{Sequence}-{Year} e.g. N-01-26

    Uses atomic counter per tenant+warehouse+year to ensure uniqueness.
    """
    warehouse_code = get_warehouse_code(warehouse_name)
    year = datetime.now(timezone.utc).strftime("%y")

    counter_key = f"trip_seq_{tenant_id}_{warehouse_code}_{year}"

    counter_doc = await db.counters.find_one_and_update(
        {"key": counter_key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True
    )
    trip_sequence = counter_doc["value"]
    trip_prefix = f"{warehouse_code}-{str(trip_sequence).zfill(2)}-{year}"

    logger.info(f"Generated trip prefix: {trip_prefix} for tenant {tenant_id}")

    return {
        "warehouse_code": warehouse_code,
        "trip_sequence": trip_sequence,
        "year": year,
        "trip_prefix": trip_prefix,
        "trip_number": trip_prefix
    }


async def generate_invoice_number(tenant_id: str, trip_id: str = None) -> str:
    """
    Generate invoice number.
    
    If trip_id provided: Format {Trip_Prefix}-{Inv_Seq} e.g. N-01-26-001
    Otherwise: Fallback format INV-YYYY-NNN
    
    Uses optimistic concurrency for atomic invoice_seq increment.
    """
    if not trip_id:
        # Fallback to legacy format
        return await _generate_legacy_invoice_number(tenant_id)

    # Get the trip to obtain its prefix
    trip = await db.trips.find_one(
        {"id": trip_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not trip:
        return await _generate_legacy_invoice_number(tenant_id)

    trip_prefix = trip.get("trip_prefix") or trip.get("trip_number", "TRIP")

    # Atomically increment invoice_seq on the trip with retry for concurrency
    max_retries = 10
    for attempt in range(max_retries):
        current_seq = trip.get("invoice_seq", 0)
        new_seq = current_seq + 1

        result = await db.trips.find_one_and_update(
            {
                "id": trip_id,
                "tenant_id": tenant_id,
                "invoice_seq": current_seq  # optimistic lock
            },
            {"$set": {"invoice_seq": new_seq}},
            return_document=True
        )

        if result is not None:
            invoice_number = f"{trip_prefix}-{str(new_seq).zfill(3)}"
            logger.info(f"Generated invoice number: {invoice_number}")
            return invoice_number

        # Collision - re-fetch and retry
        trip = await db.trips.find_one(
            {"id": trip_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        if not trip:
            break

    # Fallback if retries exhausted
    logger.warning(f"Invoice sequence retry exhausted for trip {trip_id}, using legacy format")
    return await _generate_legacy_invoice_number(tenant_id)


async def _generate_legacy_invoice_number(tenant_id: str) -> str:
    """Legacy INV-YYYY-NNN format as fallback."""
    current_year = datetime.now(timezone.utc).year
    pattern = f"INV-{current_year}-"
    last_invoice = await db.invoices.find_one(
        {"tenant_id": tenant_id, "invoice_number": {"$regex": f"^{pattern}"}},
        {"_id": 0, "invoice_number": 1},
        sort=[("invoice_number", -1)]
    )
    if last_invoice:
        last_num = int(last_invoice["invoice_number"].split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    return f"INV-{current_year}-{next_num:03d}"
