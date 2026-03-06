# Servex Holdings - Logistics Management Platform

## Original Problem Statement
Build a comprehensive full-stack logistics management application for African freight companies. Multi-tenant SaaS platform with React frontend, FastAPI backend, and MongoDB database.

## Core Requirements
- Parcel intake (manual + CSV import) with 8-digit SX-format barcodes
- Warehouse management with barcode scanning
- Trip planning and loading/unloading workflow
- Multi-feature invoicing, finance section (client statements, payment history)
- User/team management with tier-based permissions
- System settings, data export, and smart email alerts

## User Personas
- **Tier 1 (Admin/Owner)**: Full system access, manages team and settings
- **Tier 2 (Manager)**: Operations and finance, no settings
- **Tier 3 (Operations)**: Parcel intake, warehouse, loading
- **Tier 4 (Finance)**: Dashboard, clients, finance
- **Tier 5 (View Only)**: Dashboard and trips only

## Architecture
- **Frontend**: React, Tailwind CSS, Shadcn UI, lucide-react icons
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic models
- **Database**: MongoDB
- **Auth**: Session-based (cookies), role-based permissions

## What's Been Implemented

### Sessions Q, R, T (Complete)
- 8-digit barcode format (SX...) with migration
- System Export feature
- 4-Hour Smart Emails with background scheduler
- Invoice Totals Row, payment recording fixes
- Trip assignment updates parcel destination
- Standardized scrollbar colors

### Bug Fix Rounds 1-3 (Complete)
- CSV import parcel count, rate rounding, barcode generation
- Finance tab reordering, Payment History tab
- Invoice line item consolidation with toggle
- Invoice status "sent" → "finalized", overpayment support
- PDF barcodes wider for scannability
- Login/Landing page dark color scheme

### Latest Bug Fix Round (Complete - Feb 2026)
1. **Create Trip button** - Fixed nested Dialog bug, Create Trip modal now opens correctly
2. **Action button repositioning** - Moved to header, colored green/blue/red
3. **Manual barcode generation** - Added barcode field to Shipment model (was missing)
4. **Tier rename** - Roles renamed to Tier 1-5 across frontend (Team, Layout, NotesPanel, Settings, etc.)
5. **Loading/Unloading dark theme** - Updated to match Finance page (#3C3F42 + #E8DC88)
6. **WhatsApp fix** - Added phone fallback when whatsapp field is null
7. **Auto-populate moved** - Removed from Trip Worksheets, kept in Invoices tab
8. **Payment History search/filter** - Added search bar + trip filter dropdown

## Prioritized Backlog

### P2 - Future
- Session S implementation (explicitly deferred by user)

## Key Files
- `frontend/src/pages/ParcelIntake.jsx` - Parcel intake with CSV/manual
- `frontend/src/pages/Finance.jsx` - Finance tabs (dashboard, worksheets, statements, invoices, payment history)
- `frontend/src/pages/LoadingStaging.jsx` - Loading/unloading workflow
- `frontend/src/pages/Team.jsx` - Team management with tier roles
- `frontend/src/components/Layout.jsx` - Navigation with role-based filtering
- `frontend/src/components/InvoiceEditor.jsx` - Invoice management
- `backend/routes/shipment_routes.py` - Shipment CRUD
- `backend/routes/invoice_routes.py` - Invoice/payment CRUD
- `backend/services/barcode_service.py` - SX barcode generation
- `backend/dependencies.py` - Auth + tier-based permissions

## Test Credentials
- Email: admin@servex.com
- Password: Servex2026!
