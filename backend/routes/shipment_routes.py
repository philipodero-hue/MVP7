"""
Shipment routes for Servex Holdings backend.
Handles shipment/parcel CRUD operations and piece management.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from datetime import datetime, timezone

from database import db
from dependencies import get_current_user, get_tenant_id, build_warehouse_filter, check_warehouse_access
from models.schemas import Shipment, ShipmentCreate, ShipmentUpdate, ShipmentPiece, ShipmentPieceCreate, ShipmentPieceBase, create_audit_log
from models.enums import ShipmentStatus, AuditAction
from services.barcode_service import generate_barcode, generate_parcel_barcode

router = APIRouter()


@router.get("/shipments/for-invoice")
async def get_shipments_for_invoice(
    trip_id: Optional[str] = None,
    client_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    search: Optional[str] = None,
    not_invoiced: Optional[str] = "true",
    limit: Optional[int] = 500,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Get shipments available to add to an invoice.
    SESSION N Part 4: Proper filtering by trip_id, client_id, warehouse_id, search.
    Excludes already-invoiced parcels by default.
    """
    query = {"tenant_id": tenant_id}

    # CRITICAL FIX: filter by trip_id when provided
    if trip_id and trip_id != "all":
        query["trip_id"] = trip_id

    # Filter by client
    if client_id and client_id != "all":
        query["client_id"] = client_id

    # Filter by warehouse
    if warehouse_id and warehouse_id != "all":
        query["warehouse_id"] = warehouse_id

    # Exclude already-invoiced parcels by default
    if not_invoiced == "true":
        query["$or"] = [
            {"invoice_id": None},
            {"invoice_id": {"$exists": False}}
        ]

    # Exclude non-processable statuses
    if "status" not in query:
        query["status"] = {"$nin": ["quoted", "cancelled"]}

    # Search by barcode, description, recipient
    if search:
        search_cond = [
            {"barcode": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"recipient_name": {"$regex": search, "$options": "i"}},
            {"sender_name": {"$regex": search, "$options": "i"}},
        ]
        if "$or" in query:
            # Merge with existing $or using $and
            existing_or = query.pop("$or")
            query["$and"] = [
                {"$or": existing_or},
                {"$or": search_cond}
            ]
        else:
            query["$or"] = search_cond

    shipments = await db.shipments.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

    if not shipments:
        return shipments

    # Enrich with client names
    client_ids = list(set(s.get("client_id") for s in shipments if s.get("client_id")))
    client_docs = await db.clients.find(
        {"id": {"$in": client_ids}},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(len(client_ids))
    client_map = {c["id"]: c["name"] for c in client_docs}

    for s in shipments:
        s["client_name"] = client_map.get(s.get("client_id"), "Unknown")
        # Normalise field names: length/width/height → length_cm/width_cm/height_cm
        if s.get("length") and not s.get("length_cm"):
            s["length_cm"] = s["length"]
        if s.get("width") and not s.get("width_cm"):
            s["width_cm"] = s["width"]
        if s.get("height") and not s.get("height_cm"):
            s["height_cm"] = s["height"]
        # Ensure total_weight is set
        if not s.get("total_weight") and s.get("shipping_weight"):
            s["total_weight"] = s["shipping_weight"]
        if not s.get("total_weight"):
            s["total_weight"] = 0

    # Enrich with trip numbers
    trip_ids = list(set(s.get("trip_id") for s in shipments if s.get("trip_id")))
    if trip_ids:
        trip_docs = await db.trips.find(
            {"id": {"$in": trip_ids}},
            {"_id": 0, "id": 1, "trip_number": 1, "trip_prefix": 1}
        ).to_list(len(trip_ids))
        trip_map = {t["id"]: (t.get("trip_prefix") or t.get("trip_number", "N/A")) for t in trip_docs}
        for s in shipments:
            s["trip_number"] = trip_map.get(s.get("trip_id"), "")

    return shipments


@router.get("/shipments")
async def list_shipments(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    trip_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    not_invoiced: Optional[str] = None,
    limit: Optional[int] = 1000,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """List all shipments with optional filters.
    
    SECURITY: Applies warehouse-based filtering for restricted users.
    """
    query = {"tenant_id": tenant_id}
    
    # SECURITY: Apply warehouse-based access control
    warehouse_filter = build_warehouse_filter(user)
    if warehouse_filter:
        if warehouse_id:
            # Check if requested warehouse is allowed
            await check_warehouse_access(user, warehouse_id)
            query["warehouse_id"] = warehouse_id
        else:
            # Apply warehouse filter
            query.update(warehouse_filter)
    elif warehouse_id:
        query["warehouse_id"] = warehouse_id
    
    # Support comma-separated statuses
    if status:
        statuses = [s.strip() for s in status.split(',')]
        if len(statuses) == 1:
            query["status"] = statuses[0]
        else:
            query["status"] = {"$in": statuses}
    
    # Filter for parcels without invoice
    if not_invoiced == 'true':
        query["$or"] = [
            {"invoice_id": None},
            {"invoice_id": {"$exists": False}}
        ]
    
    shipments = await db.shipments.find(query, {"_id": 0}).to_list(limit)
    
    # Enrich with invoice numbers if available
    if shipments:
        shipment_ids = [s["id"] for s in shipments]
        
        # Get invoice_ids from shipments directly
        shipment_invoice_ids = list(set(s.get("invoice_id") for s in shipments if s.get("invoice_id")))
        
        # Also check invoice line items that reference these shipments
        line_items = await db.invoice_line_items.find(
            {"shipment_id": {"$in": shipment_ids}},
            {"_id": 0, "shipment_id": 1, "invoice_id": 1}
        ).to_list(1000)
        
        # Combine all invoice_ids
        line_item_invoice_ids = list(set(li["invoice_id"] for li in line_items if li.get("invoice_id")))
        all_invoice_ids = list(set(shipment_invoice_ids + line_item_invoice_ids))
        
        # Get invoice numbers and statuses for these invoice_ids
        invoices = {}
        if all_invoice_ids:
            invoice_docs = await db.invoices.find(
                {"id": {"$in": all_invoice_ids}},
                {"_id": 0, "id": 1, "invoice_number": 1, "status": 1}
            ).to_list(1000)
            invoices = {inv["id"]: {"invoice_number": inv["invoice_number"], "status": inv.get("status")} for inv in invoice_docs}
        
        # Map shipment_id to invoice data via line items
        shipment_invoice_map = {}
        for li in line_items:
            if li.get("shipment_id") and li.get("invoice_id"):
                inv_data = invoices.get(li["invoice_id"], {})
                shipment_invoice_map[li["shipment_id"]] = inv_data
        
        # Enrich shipments with invoice data
        for s in shipments:
            # First check direct invoice_id on shipment
            if s.get("invoice_id") and s["invoice_id"] in invoices:
                inv_data = invoices[s["invoice_id"]]
                s["invoice_number"] = inv_data.get("invoice_number")
                s["invoice_status"] = inv_data.get("status")
            # Fall back to line items mapping
            elif s["id"] in shipment_invoice_map:
                s["invoice_number"] = shipment_invoice_map[s["id"]].get("invoice_number")
                s["invoice_status"] = shipment_invoice_map[s["id"]].get("status")
            else:
                s["invoice_number"] = None
                s["invoice_status"] = None
        
        # Enrich with client names (batch fetch to avoid N+1)
        client_ids = list(set(s.get("client_id") for s in shipments if s.get("client_id")))
        if client_ids:
            client_docs = await db.clients.find(
                {"id": {"$in": client_ids}},
                {"_id": 0, "id": 1, "name": 1}
            ).to_list(len(client_ids))
            client_name_map = {c["id"]: c["name"] for c in client_docs}
        else:
            client_name_map = {}
        
        for s in shipments:
            s["client_name"] = client_name_map.get(s.get("client_id"), "")
    
    return shipments

@router.get("/shipments/{shipment_id}")
async def get_shipment(shipment_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single shipment with pieces"""
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    pieces = await db.shipment_pieces.find({"shipment_id": shipment_id}, {"_id": 0}).to_list(100)
    
    return {**shipment, "pieces": pieces}

@router.post("/shipments", response_model=Shipment)
async def create_shipment(
    request: Request,
    shipment_data: ShipmentCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new shipment with short scannable barcode"""
    # Verify client belongs to tenant
    client = await db.clients.find_one(
        {"id": shipment_data.client_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Generate short barcode (SX format)
    barcode = await generate_parcel_barcode(tenant_id)
    
    # Determine status based on trip assignment
    status = shipment_data.status
    if status is None:
        status = ShipmentStatus.staged if shipment_data.trip_id else ShipmentStatus.warehouse
    
    # Build shipment data
    shipment_dict = shipment_data.model_dump(exclude={'status'})
    shipment = Shipment(
        **shipment_dict,
        barcode=barcode,  # Use new short barcode
        status=status,
        tenant_id=tenant_id,
        created_by=user["id"]
    )
    
    doc = shipment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.shipments.insert_one(doc)
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.create,
        table_name="shipments",
        record_id=shipment.id,
        new_value=doc,
        ip_address=request.client.host if request.client else None
    )
    
    return shipment

@router.put("/shipments/{shipment_id}")
async def update_shipment(
    request: Request,
    shipment_id: str,
    update_data: ShipmentUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update shipment"""
    # Get old value for audit
    old_shipment = await db.shipments.find_one({"id": shipment_id, "tenant_id": tenant_id})
    if not old_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Check if parcel is locked (collected)
    if old_shipment.get("locked", False):
        raise HTTPException(
            status_code=403,
            detail="Cannot edit collected parcel. Contact admin to unlock if needed."
        )
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Determine action type
    action = AuditAction.status_change if "status" in update_dict else AuditAction.update
    
    if update_dict:
        result = await db.shipments.update_one(
            {"id": shipment_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Shipment not found")
    
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=action,
        table_name="shipments",
        record_id=shipment_id,
        old_value=old_shipment,
        new_value=shipment,
        ip_address=request.client.host if request.client else None
    )
    
    return shipment

@router.patch("/shipments/{shipment_id}")
async def patch_shipment(
    request: Request,
    shipment_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Partial update shipment - supports clearing invoice_id"""
    # Get old value
    old_shipment = await db.shipments.find_one({"id": shipment_id, "tenant_id": tenant_id})
    if not old_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get JSON body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # Build update dict - explicitly handle null values
    update_dict = {}
    for key, value in body.items():
        if key == "invoice_id" and value is None:
            update_dict["invoice_id"] = None
        elif value is not None:
            update_dict[key] = value
    
    if not update_dict:
        return old_shipment
    
    # Update shipment
    await db.shipments.update_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"$set": update_dict}
    )
    
    # Get updated shipment
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    
    return shipment

@router.delete("/shipments/{shipment_id}")
async def delete_shipment(
    request: Request,
    shipment_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete shipment and its pieces"""
    # Get old value for audit
    old_shipment = await db.shipments.find_one({"id": shipment_id, "tenant_id": tenant_id})
    if not old_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    result = await db.shipments.delete_one({"id": shipment_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Delete associated pieces
    await db.shipment_pieces.delete_many({"shipment_id": shipment_id})
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.delete,
        table_name="shipments",
        record_id=shipment_id,
        old_value=old_shipment,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Shipment deleted"}

# ============ SHIPMENT VERIFICATION ROUTES ============

@router.put("/shipments/{shipment_id}/verify")
async def verify_shipment(
    request: Request,
    shipment_id: str,
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a shipment as verified or unverified"""
    verified = data.get("verified", False)
    
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    update_dict = {
        "verified": verified,
        "verified_by": user["id"] if verified else None,
        "verified_at": datetime.now(timezone.utc).isoformat() if verified else None
    }
    
    await db.shipments.update_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"$set": update_dict}
    )
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.update,
        table_name="shipments",
        record_id=shipment_id,
        old_value={"verified": shipment.get("verified", False)},
        new_value={"verified": verified},
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": f"Shipment {'verified' if verified else 'verification removed'}"}

# ============ SHIPMENT PIECES ROUTES ============

@router.post("/shipments/{shipment_id}/pieces", response_model=ShipmentPiece)
async def create_shipment_piece(
    shipment_id: str,
    piece_data: ShipmentPieceBase,
    tenant_id: str = Depends(get_tenant_id)
):
    """Add a piece to shipment"""
    # Verify shipment belongs to tenant
    shipment = await db.shipments.find_one(
        {"id": shipment_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Get trip number if assigned
    trip_number = None
    if shipment.get("trip_id"):
        trip = await db.trips.find_one({"id": shipment["trip_id"]}, {"_id": 0})
        if trip:
            trip_number = trip.get("trip_number")
    
    # Count existing shipments for sequence number
    shipment_count = await db.shipments.count_documents({
        "tenant_id": tenant_id,
        "trip_id": shipment.get("trip_id")
    })
    
    # Generate barcode
    barcode = generate_barcode(trip_number, shipment_count, piece_data.piece_number)
    
    piece = ShipmentPiece(
        **piece_data.model_dump(),
        shipment_id=shipment_id,
        barcode=barcode
    )
    
    doc = piece.model_dump()
    if doc.get('loaded_at'):
        doc['loaded_at'] = doc['loaded_at'].isoformat()
    await db.shipment_pieces.insert_one(doc)
    
    return piece

@router.get("/pieces/scan/{barcode}")
async def scan_barcode(barcode: str, tenant_id: str = Depends(get_tenant_id)):
    """Scan a barcode or parcel ID and return piece + shipment info
    
    Supports multiple lookup methods:
    1. Full barcode (e.g., S123-001-01)
    2. Partial shipment ID (e.g., E1DF9124 - first 8 chars)
    3. Full shipment ID (UUID format)
    """
    piece = None
    shipment = None
    
    # First, try to find by exact barcode match in shipment_pieces
    piece = await db.shipment_pieces.find_one({"barcode": barcode}, {"_id": 0})
    
    if piece:
        # Found by barcode, get the shipment
        shipment = await db.shipments.find_one(
            {"id": piece["shipment_id"], "tenant_id": tenant_id},
            {"_id": 0}
        )
    else:
        # Try to find shipment by ID (partial or full)
        barcode_upper = barcode.upper().strip()
        barcode_lower = barcode.lower().strip()
        
        # Try full ID match first
        shipment = await db.shipments.find_one(
            {"id": barcode_lower, "tenant_id": tenant_id},
            {"_id": 0}
        )
        
        # If not found, try partial ID match (first 8 characters)
        if not shipment:
            # Search for shipment where ID starts with the input
            shipments = await db.shipments.find(
                {"tenant_id": tenant_id},
                {"_id": 0, "id": 1}
            ).to_list(10000)
            
            for s in shipments:
                if s["id"][:8].upper() == barcode_upper or s["id"].upper().startswith(barcode_upper):
                    shipment = await db.shipments.find_one(
                        {"id": s["id"], "tenant_id": tenant_id},
                        {"_id": 0}
                    )
                    break
        
        # If shipment found, get the first piece
        if shipment:
            piece = await db.shipment_pieces.find_one(
                {"shipment_id": shipment["id"]},
                {"_id": 0}
            )
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Barcode or parcel not found")
    
    client = await db.clients.find_one({"id": shipment["client_id"]}, {"_id": 0})
    
    return {
        "piece": piece,
        "shipment": shipment,
        "client": client
    }

@router.put("/pieces/{piece_id}/load")
async def mark_piece_loaded(piece_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Mark a piece as loaded"""
    piece = await db.shipment_pieces.find_one({"id": piece_id}, {"_id": 0})
    if not piece:
        raise HTTPException(status_code=404, detail="Piece not found")
    
    # Verify shipment belongs to tenant
    shipment = await db.shipments.find_one(
        {"id": piece["shipment_id"], "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not shipment:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.shipment_pieces.update_one(
        {"id": piece_id},
        {"$set": {"loaded_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Piece marked as loaded"}


# SESSION G: Collection Workflow Endpoints

@router.get("/shipments/ready-for-collection")
async def get_ready_for_collection(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get all parcels ready for collection by client (SESSION G)"""
    parcels = await db.shipments.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "status": "arrived"
    }, {"_id": 0}).to_list(500)
    
    return {
        "count": len(parcels),
        "client_id": client_id,
        "parcels": [
            {
                "id": p["id"],
                "barcode": p.get("barcode"),
                "description": p.get("description"),
                "weight": p.get("weight"),
                "arrived_at": p.get("updated_at"),
                "invoice_id": p.get("invoice_id"),
                "is_invoiced": p.get("invoice_id") is not None
            }
            for p in parcels
        ]
    }

@router.post("/shipments/mark-collected")
async def mark_parcels_collected(
    parcel_ids: List[str],
    override: bool = False,
    override_reason: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark parcels as collected (SESSION G)"""
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.shipments.update_many(
        {
            "tenant_id": tenant_id,
            "id": {"$in": parcel_ids}
        },
        {
            "$set": {
                "status": "collected",
                "collected_at": now,
                "collected_by": user["id"],
                "collection_override": override,
                "collection_override_reason": override_reason if override else None,
                "updated_at": now
            }
        }
    )
    
    return {
        "message": f"Marked {result.modified_count} parcels as collected",
        "count": result.modified_count,
        "override_used": override
    }

