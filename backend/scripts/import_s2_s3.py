"""
Import S2.csv and S3.csv test data (CSV_IMPORT_ADDENDUM).
S2 → Nairobi trip (N-01-26)
S3 → Johannesburg trip (J-01-26)

Run: python backend/scripts/import_s2_s3.py
"""
import asyncio
import csv
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

# Resolve DB from environment (same as the app)
sys.path.insert(0, str(Path(__file__).parent.parent))

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
TENANT_ID = "default_tenant"


async def get_or_create_tenant(db):
    """Ensure default tenant exists and return tenant_id."""
    tenant = await db.tenants.find_one({"subdomain": "default"})
    if tenant:
        tid = tenant.get("id", TENANT_ID)
        print(f"Using existing tenant: {tid}")
        return tid

    # Try to find any tenant
    tenant = await db.tenants.find_one({})
    if tenant:
        tid = tenant.get("id", TENANT_ID)
        print(f"Using first tenant: {tid}")
        return tid

    # Use default_tenant
    print(f"Using default tenant ID: {TENANT_ID}")
    return TENANT_ID


async def import_csv_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    tenant_id = await get_or_create_tenant(db)

    print(f"\nStarting CSV import...")
    print(f"Database: {DB_NAME}")
    print(f"Tenant: {tenant_id}")

    # Create warehouses if they don't exist
    nairobi_wh = await db.warehouses.find_one({"name": "Nairobi Warehouse", "tenant_id": tenant_id})
    if not nairobi_wh:
        nairobi_wh = {
            "id": str(uuid4()),
            "name": "Nairobi Warehouse",
            "code": "N",
            "tenant_id": tenant_id,
            "location": "Nairobi, Kenya",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.warehouses.insert_one(nairobi_wh)
        print("Created Nairobi Warehouse")
    else:
        print("Nairobi Warehouse already exists")

    jhb_wh = await db.warehouses.find_one({"name": "Johannesburg Warehouse", "tenant_id": tenant_id})
    if not jhb_wh:
        jhb_wh = {
            "id": str(uuid4()),
            "name": "Johannesburg Warehouse",
            "code": "J",
            "tenant_id": tenant_id,
            "location": "Johannesburg, South Africa",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.warehouses.insert_one(jhb_wh)
        print("Created Johannesburg Warehouse")
    else:
        print("Johannesburg Warehouse already exists")

    # Find CSV files - try multiple locations
    script_dir = Path(__file__).parent
    possible_paths = [
        script_dir / "S2.csv",
        script_dir / "S3.csv",
        Path("/tmp/S2.csv"),
        Path("/tmp/S3.csv"),
        Path("/app/S2.csv"),
        Path("/app/S3.csv"),
    ]

    s2_path = None
    s3_path = None
    for p in possible_paths:
        if "S2" in p.name and p.exists():
            s2_path = p
        if "S3" in p.name and p.exists():
            s3_path = p

    if not s2_path or not s3_path:
        print(f"\nERROR: Could not find CSV files. Tried: {[str(p) for p in possible_paths]}")
        print("Please place S2.csv and S3.csv in /app/backend/scripts/ or /tmp/")
        return

    # Import S2.csv → Nairobi trip
    await import_csv_file(
        db,
        tenant_id,
        str(s2_path),
        nairobi_wh,
        "N",
        "Nairobi → Johannesburg"
    )

    # Import S3.csv → Johannesburg trip
    await import_csv_file(
        db,
        tenant_id,
        str(s3_path),
        jhb_wh,
        "J",
        "Johannesburg → Nairobi"
    )

    print("\n CSV import completed!")
    print("Check your database - you should see:")
    print("  - 2 trips (N-01-26, J-01-26)")
    print("  - ~550 parcels total")
    print("  - Unique clients from both CSVs")

    client.close()


async def import_csv_file(db, tenant_id, csv_path, warehouse, warehouse_code, route_name):
    """Import a single CSV file into a trip."""
    year = datetime.now().strftime("%y")

    # Get next trip sequence for this warehouse
    counter_key = f"trip_seq_{tenant_id}_{warehouse_code}_{year}"
    counter_doc = await db.counters.find_one_and_update(
        {"key": counter_key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True
    )
    trip_sequence = counter_doc["value"]
    trip_prefix = f"{warehouse_code}-{str(trip_sequence).zfill(2)}-{year}"

    # Create trip
    trip_data = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "trip_number": trip_prefix,
        "trip_prefix": trip_prefix,
        "warehouse_code": warehouse_code,
        "trip_sequence": trip_sequence,
        "year": year,
        "route": [warehouse["name"], route_name.split(" → ")[1]],
        "status": "loading",
        "departure_date": datetime.now(timezone.utc).isoformat(),
        "invoice_seq": 0,
        "created_by": "system-import",
        "locked_by": None,
        "locked_at": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.trips.insert_one(trip_data)
    print(f"\nCreated trip: {trip_prefix}")

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"  Found {len(rows)} parcels in CSV")

    # Track unique clients
    clients_map = {}
    inserted = 0

    for idx, row in enumerate(rows):
        sender_name = (row.get('Sent By') or row.get('sent_by') or row.get('Client') or '').strip()
        recipient_name = (row.get('Primary Recipient') or row.get('primary_recipient') or row.get('Recipient') or '').strip()

        if not sender_name:
            sender_name = f"Client {idx + 1}"

        # Create/get sender client
        if sender_name not in clients_map:
            # Check if client already exists in DB
            existing_client = await db.clients.find_one({
                "tenant_id": tenant_id,
                "name": sender_name
            })
            if existing_client:
                clients_map[sender_name] = existing_client
            else:
                client_data = {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id,
                    "name": sender_name,
                    "company_name": sender_name,
                    "phone": f"+254700{str(len(clients_map) + 1).zfill(6)}",
                    "email": f"{sender_name.lower().replace(' ', '.').replace(',', '')}@example.com",
                    "default_rate_type": "per_kg",
                    "default_rate_value": 20.0,
                    "default_currency": "ZAR",
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.clients.insert_one(client_data)
                clients_map[sender_name] = client_data

        client = clients_map[sender_name]

        # Parse dimensions (SESSION N expects length_cm, width_cm, height_cm)
        try:
            length = int(float(row.get('L') or row.get('length') or 0))
            width = int(float(row.get('W') or row.get('width') or 0))
            height = int(float(row.get('H') or row.get('height') or 0))

            if length > 0 and width > 0 and height > 0:
                volumetric_weight = round((length * width * height) / 5000, 2)
                cbm = round((length * width * height) / 1000000, 4)
            else:
                length = width = height = 0
                volumetric_weight = 0
                cbm = 0
        except (ValueError, TypeError):
            length = width = height = 0
            volumetric_weight = 0
            cbm = 0

        # Parse weight
        try:
            actual_weight = float(row.get('KG') or row.get('kg') or row.get('weight') or 0)
        except (ValueError, TypeError):
            actual_weight = 0

        shipping_weight = round(max(actual_weight, volumetric_weight), 2)

        # Parse quantity
        try:
            pieces = int(float(row.get('QTY') or row.get('qty') or row.get('quantity') or 1))
            if pieces < 1:
                pieces = 1
        except (ValueError, TypeError):
            pieces = 1

        description = (row.get('Description') or row.get('description') or '').strip()

        # Create parcel barcode
        parcel_barcode = f"SX{trip_prefix.replace('-', '')}{str(idx + 1).zfill(4)}"

        parcel_data = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "barcode": parcel_barcode,
            "client_id": client["id"],
            "trip_id": trip_data["id"],
            "warehouse_id": warehouse["id"],
            "warehouse_name": warehouse["name"],
            "destination": route_name.split(" → ")[1],
            "description": description,
            "recipient_name": recipient_name,
            "sender_name": sender_name,
            "pieces": pieces,
            "total_pieces": pieces,
            "total_weight": round(actual_weight, 2),
            "length_cm": length,
            "width_cm": width,
            "height_cm": height,
            "volumetric_weight": volumetric_weight,
            "shipping_weight": shipping_weight,
            "total_cbm": cbm,
            "status": "warehouse",
            "invoice_id": None,
            "invoice_number": None,
            "invoice_status": "uninvoiced",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.shipments.insert_one(parcel_data)
        inserted += 1

    print(f"  Imported {inserted} parcels")
    print(f"  Created/used {len(clients_map)} unique clients")

    return trip_data, clients_map


if __name__ == "__main__":
    asyncio.run(import_csv_data())
