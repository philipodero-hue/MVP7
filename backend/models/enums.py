"""
Enum classes for Servex Holdings backend.
Defines all status types, categories, and classifications used throughout the system.
"""
from enum import Enum


class UserRole(str, Enum):
    # Tier-based roles (SESSION N Part 6.4)
    tier_1 = "tier_1"  # Admin - full access
    tier_2 = "tier_2"  # Manager - operations + finance
    tier_3 = "tier_3"  # Operations - warehouse + trips
    tier_4 = "tier_4"  # Finance - invoices + clients
    tier_5 = "tier_5"  # View Only
    # Legacy roles (kept for migration compatibility)
    owner = "owner"
    manager = "manager"
    warehouse = "warehouse"
    finance = "finance"
    driver = "driver"


# Tier descriptions for UI display
TIER_DESCRIPTIONS = {
    "tier_1": "Admin - Full system access, user management, all modules",
    "tier_2": "Manager - Operations and finance, no user management",
    "tier_3": "Operations - Warehouse, trips, parcel intake only",
    "tier_4": "Finance - Invoices, clients, rates only",
    "tier_5": "View Only - Read-only access to all modules",
}

# Tier permissions mapping
TIER_PERMISSIONS = {
    "tier_1": ["*"],  # All permissions
    "tier_2": ["dashboard", "parcel-intake", "warehouse", "clients", "loading", "trips", "finance", "fleet", "team", "edit_rates", "view_all_warehouses", "export_data"],
    "tier_3": ["dashboard", "parcel-intake", "warehouse", "loading", "trips"],
    "tier_4": ["dashboard", "clients", "finance", "edit_rates"],
    "tier_5": ["dashboard"],  # View only
    # Legacy
    "owner": ["*"],
    "manager": ["dashboard", "parcel-intake", "warehouse", "clients", "loading", "trips", "finance", "fleet", "team", "edit_rates", "view_all_warehouses", "export_data"],
    "warehouse": ["dashboard", "parcel-intake", "warehouse", "loading"],
    "finance": ["dashboard", "clients", "finance", "edit_rates"],
    "driver": ["dashboard", "trips"],
}


class UserStatus(str, Enum):
    active = "active"
    invited = "invited"
    suspended = "suspended"


class ClientStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    merged = "merged"


class RateType(str, Enum):
    per_kg = "per_kg"
    per_cbm = "per_cbm"
    flat_rate = "flat_rate"
    custom = "custom"


class ShipmentStatus(str, Enum):
    warehouse = "warehouse"
    staged = "staged"
    ready_to_load = "ready_to_load"
    loaded = "loaded"
    in_transit = "in_transit"
    arrived = "arrived"
    delivered = "delivered"
    collected = "collected"


class TripStatus(str, Enum):
    planning = "planning"
    loading = "loading"
    in_transit = "in_transit"
    delivered = "delivered"
    closed = "closed"


class ExpenseCategory(str, Enum):
    fuel = "fuel"
    tolls = "tolls"
    border_fees = "border_fees"
    repairs = "repairs"
    food = "food"
    accommodation = "accommodation"
    other = "other"


class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"


class PaymentMethod(str, Enum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    mobile_money = "mobile_money"
    other = "other"


class VehicleStatus(str, Enum):
    available = "available"
    in_transit = "in_transit"
    repair = "repair"
    inactive = "inactive"


class VehicleComplianceType(str, Enum):
    license_disk = "license_disk"
    insurance = "insurance"
    roadworthy = "roadworthy"
    service = "service"
    custom = "custom"


class DriverStatus(str, Enum):
    available = "available"
    on_trip = "on_trip"
    on_leave = "on_leave"
    inactive = "inactive"


class DriverComplianceType(str, Enum):
    license = "license"
    work_permit = "work_permit"
    medical = "medical"
    prdp = "prdp"
    custom = "custom"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    status_change = "status_change"


class NotificationType(str, Enum):
    mention = "mention"
    compliance = "compliance"
    system_event = "system_event"
    payment = "payment"
    invoice = "invoice"


class WhatsAppStatus(str, Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"
