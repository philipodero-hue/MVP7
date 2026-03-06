"""
Database connection module for Servex Holdings backend.
Manages MongoDB connection using motor async driver.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, DB_NAME

# MongoDB client and database instances
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections (for reference and type hints)
users_collection = db['users']
clients_collection = db['clients']
client_rates_collection = db['client_rates']
shipments_collection = db['shipments']
shipment_pieces_collection = db['shipment_pieces']
trips_collection = db['trips']
invoices_collection = db['invoices']
invoice_line_items_collection = db['invoice_line_items']
invoice_adjustments_collection = db['invoice_adjustments']
payments_collection = db['payments']
expenses_collection = db['expenses']
vehicles_collection = db['vehicles']
drivers_collection = db['drivers']
warehouses_collection = db['warehouses']
audit_logs_collection = db['audit_logs']
notifications_collection = db['notifications']
settings_collection = db['settings']
counters_collection = db['counters']


async def setup_indexes():
    """Setup database indexes including barcode uniqueness."""
    try:
        # Drop existing barcode index if it exists (without sparse option)
        await db.shipments.drop_index("barcode_1_tenant_id_1")
        print("Dropped existing barcode index")
    except Exception as e:
        print(f"No existing barcode index to drop or error: {e}")
    
    # Create sparse unique index to allow multiple null values
    await db.shipments.create_index([
        ("barcode", 1),
        ("tenant_id", 1)
    ], unique=True, sparse=True)  # sparse=True allows multiple null values

    # Ensure counter keys are unique
    try:
        await db.counters.create_index([("key", 1)], unique=True)
    except Exception as e:
        print(f"Counter index already exists or error: {e}")

    print("Database indexes ensured: shipments (barcode, tenant_id) unique sparse, counters (key) unique.")
