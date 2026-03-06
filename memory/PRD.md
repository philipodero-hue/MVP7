# Servex Holdings - Logistics Management SaaS PRD

**Last Updated:** 2026-03-06  
**Status:** Session Q, R, T Complete | Session S Excluded

---

## Problem Statement
Multi-tenant logistics SaaS for African freight companies. Implement Sessions Q, R, T features (leave out Session S - CraftMyPDF). Test and preview everything.

## Architecture
- **Frontend:** React + Tailwind CSS + Shadcn UI  
- **Backend:** FastAPI + Python  
- **Database:** MongoDB  
- **Auth:** Session/Cookie-based JWT

## User Personas
- Warehouse operators (intake parcels, print labels)
- Finance team (create invoices, record payments)
- Admin/owners (settings, exports, reports)

---

## Core Requirements (Static)

### Parcel Lifecycle
1. Intake → Staged → Loaded → In Transit → Arrived → Delivered/Collected

### Invoice Lifecycle
1. Draft → Sent → Partial → Paid

---

## What's Been Implemented

## What's Been Implemented

### Session Q (2026-03-06)
- ✅ **8-Digit Barcode Format** - Changed to `SX{sequence:08d}`, no annual reset. Migration run: 1080 existing parcels assigned SX barcodes. Warehouse now shows SX00000001 format.
- ✅ **Remove "Table View" Text** - Heading changed to "Parcel Intake"
- ✅ **Red Highlight for Parcels Without Trip** - `bg-red-50 border-l-4 border-l-red-400` in Warehouse.jsx
- ✅ **Save All & Print Working** - Fixed: `handleSaveAll` now returns `createdParcels`
- ✅ **Invoice Consolidation Toggle** - "Consolidate Identical" button groups identical items in InvoiceEditor view

### Session R (2026-03-06)
- ✅ **System Export** - GET `/api/data/system-export` returns ZIP with all tenant data
- ✅ **4-Hour Smart Emails** - Email alert backend routes + Settings > Email Alerts tab

### Session T (2026-03-06)
- ✅ **Payment Recording** - Fixed missing `@router.post` decorator
- ✅ **Destination Showing** - Shows "No Trip" in red when no trip_id; trip assignment updates destination
- ✅ **Invoice Totals Row** - TOTALS row with QTY, Weight, Vol Wt, Ship Wt, Amount
- ✅ **Scrollbar Colors** - Dark gray `#3C3F42` with `!important`

### Bug Fixes (2026-03-06)
- ✅ **CSV Import Column Parser** - Header-based parsing: correctly handles `Sent By, Primary Recipient, Description, QTY, KG, L, W, H` format
- ✅ **Rate Rounding** - `shipWeight` rounded to 2dp before `× rate` (25.22 × 36 = 907.92 not 907.80)
- ✅ **Finance Tabs Order** - Invoices | Client Statements | Trip Worksheets | Overdue | Payment History
- ✅ **Payment History Tab** - New tab in Finance showing all payments with recorder name, time, invoice, method
- ✅ **Barcode in Warehouse** - Column now shows `parcel.barcode` (SX format) not `parcel.id.slice(0,8)`
- ✅ **Barcode Migration** - Endpoint `/data/migrate-barcodes` retroactively assigned SX barcodes to 1080 existing parcels

---

## Files Modified (Session Q/R/T)
| File | Changes |
|------|---------|
| `backend/services/barcode_service.py` | 8-digit format, no annual reset |
| `backend/routes/invoice_routes.py` | Added @router.post decorator to record_invoice_payment |
| `backend/routes/warehouse_routes.py` | bulk_assign_trip now updates destination field |
| `backend/routes/trip_routes.py` | assign-shipment now updates destination from trip route |
| `backend/routes/data_routes.py` | Added system export endpoint + StreamingResponse imports |
| `backend/routes/email_alert_routes.py` | NEW - SMTP config, 4h email send, test endpoint |
| `backend/services/email_service.py` | NEW - SMTP email with CSV attachment |
| `backend/server.py` | Added email_alert_routes, scheduler coroutine |
| `backend/routes/__init__.py` | Added email_alert_routes export |
| `frontend/src/pages/ParcelIntake.jsx` | Remove Table View, fix Save & Print return value |
| `frontend/src/pages/Warehouse.jsx` | Red highlight no-trip, "No Trip" destination display |
| `frontend/src/components/InvoiceEditor.jsx` | TOTALS row, extended totals calculation |
| `frontend/src/pages/Settings.jsx` | System export button, Email Alerts tab/UI/functions |
| `frontend/src/index.css` | Scrollbar dark gray #3C3F42 |

---

## Prioritized Backlog

### P0 (Critical, blocking operations)
- None currently

### P1 (Important, next session)
- Session S: CraftMyPDF Integration & Quote Generation
- End-to-end barcode test with real parcel creation
- Invoice consolidation end-to-end verification (10 identical items → 1 row)

### P2 (Enhancement)
- Email alert scheduler: Consider using persistent cron vs in-memory asyncio loop
- Barcode scan testing with Honeywell IHS310X

---

## Next Tasks
1. Test with real data: create clients, parcels, trips, invoices
2. Verify barcode SX00000001 format on labels
3. Test payment recording on a real invoice
4. Test system export ZIP contents
5. Implement Session S (CraftMyPDF) when requested
