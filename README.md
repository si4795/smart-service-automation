# SmartServe: On-Demand Home Service Lifecycle Management Platform

SmartServe is an on-demand trade service marketplace and automated dispatch management system. Built using a lightweight Python/Flask backend, persistent SQLite storage, and a responsive Tailwind CSS frontend, it manages the complete operational lifecycle of local home services—from customer discovery and heuristic pro matching to real-time dispatch tracking and automated digital invoicing.

---

## 1. System Architecture

The application follows a modular MVC design pattern separated into domain models, algorithmic match services, and HTTP routing layers:

```
smart_service_hackathon/
├── app.py                     # HTTP request routing, session auth & lifecycle endpoints
├── database.py                # SQLite schema management, relational foreign keys, & migrations
├── smartserve.db              # Persistent relational SQLite database file
├── services/
│   ├── __init__.py
│   ├── matcher.py             # Multi-factor ranking engine & emergency heuristic dispatcher
│   └── mock_db.py             # Database facade and category resolution interface
├── templates/
│   ├── base.html              # Core layout, navigation bar, auth modals, and print CSS
│   ├── landing.html           # Consumer landing portal, trust metrics, & category explorer
│   ├── specialists.html       # Full-width specialist catalog, filter bar, & media portfolio modal
│   ├── checkout.html          # Two-column customer details, slot scheduler, & fee breakdown
│   ├── order_status.html      # Real-time 5-stage milestone stepper & printable tax invoice
│   ├── index.html             # Customer dashboard search & scheduling interface
│   ├── provider.html          # Technician Kanban dispatch board (role-restricted)
│   ├── tracking.html          # Multi-order lookup & pipeline audit trail
│   ├── login.html             # Credential login & 1-click persona switch
│   └── signup.html            # User & technician registration portal
├── test_engine.py             # Automated unit and integration test suite (17 tests)
├── verify_demo.py             # 5-stage end-to-end demo pipeline verification runner
├── requirements.txt           # Minimal standard Python dependencies (Flask, Werkzeug)
└── README.md                  # System specification and documentation
```

### Architectural Principles
- **Zero Heavy Dependencies**: Pure standard library Python 3 with Flask and built-in `sqlite3`. No cumbersome ORM overhead or node compilation pipelines.
- **Relational Consistency**: Foreign key enforcement between bookings, technicians, users, and invoices.
- **Strict Role-Based Access Control (RBAC)**: Session-based route protection ensuring customer and technician views are compartmentalized.
- **Deterministic Scheduling**: Atomic collision checks ensure a specialist cannot be double-booked for the same time slot.

---

## 2. Multi-Page Sequential User Journey

SmartServe transitions users through five dedicated, single-purpose application views:

1. **Discovery & Category Selection (`GET /` - `landing.html`)**
   - Presents the consumer landing interface with trust metrics (100% background checks, upfront pricing).
   - Six trade categories: Electrical Engineering, Plumbing & Pipefitting, HVAC & Appliance Care, Appliance Repair, Carpentry & Woodwork, and Home Painting & Hygiene.
   - Quick 1-click evaluation buttons to switch between customer (`Suaib Islam`) and technician (`Kazi Rashedul Karim`) roles.

2. **Specialist Evaluation & Scheduling (`GET /services/<category>` - `specialists.html`)**
   - Full-width responsive specialist catalog with horizontal filtering (date picker, 1-hour time windows, urgent priority toggle).
   - Candidate cards displaying profile avatars, licensing badges, composite match scores, distance radius, and starting rates.
   - Interactive modal showcasing technician trade biographies, inspection photo galleries, and field demonstration videos.

3. **Booking Confirmation & Pricing Review (`GET /checkout/<technician_id>` - `checkout.html`)**
   - Two-column booking summary with automatic customer profile pre-fill (name, phone, address).
   - Real-time price breakdown: Specialist Base Rate + Platform Fee (৳50) + Urgent Surcharge (৳100 if Emergency) + 5% Government VAT.
   - Atomic pre-validation against technician calendar collisions prior to form submission (`POST /checkout`).

4. **Real-Time Lifecycle Tracking (`GET /orders/<booking_code>` - `order_status.html`)**
   - Real-time customer tracking featuring a 5-stage visual milestone stepper:
     $$\text{Request Submitted} \longrightarrow \text{Pro Confirmed} \longrightarrow \text{En Route} \longrightarrow \text{Work in Progress} \longrightarrow \text{Completed}$$
   - Displays assigned technician contact details, transit status, and chronological audit log.
   - On completion, renders an official digital tax receipt with dedicated print stylesheet (`@media print`).

5. **Field Operations Board (`GET /provider` - `provider.html`)**
   - Restricted to authenticated technicians.
   - Kanban board organizing active work orders across five sequential workflow columns with single-click milestone advancement.

---

## 3. Algorithmic Dispatch Engine

Technician assignment and ranking are governed by multi-factor optimization formulas balancing customer proximity, verified trade ratings, upfront pricing, and current fleet workload:

### 3.1 Composite Match Score (Normal Dispatch)
For standard appointments, the ranking score evaluates trade reputation against distance and price penalties:

$$\text{Base Score} = (R \times 25.0) - (D \times 6.0) - (P \times 0.015)$$

Where:
- $R \in [1.0, 5.0]$ is the technician's verified historical rating.
- $D \ge 0$ is the radial distance in kilometers from the customer's Cantonment location.
- $P \ge 0$ is the base service inspection fee in Bangladeshi Taka (BDT).

### 3.2 Proximity Attenuation Boost (Emergency Dispatch)
When a request is designated as `Emergency`, arrival speed takes priority. An exponential proximity multiplier rewards technicians situated closest to the service site:

$$\text{Emergency Boost} = \max(0.0, (10.0 - D) \times 20.0)$$

$$\text{Total Score} = \text{Base Score} + \text{Emergency Boost}$$

### 3.3 Workload Balancing Tie-Breaker
When multiple candidates produce matching composite scores, the tie is broken deterministically by selecting the technician with the fewest active jobs:

$$\text{Precedence} = \arg\min (\text{active\_jobs\_count})$$

This distributes field workload evenly across available contractors and avoids dispatching overwhelmed technicians.

### 3.4 Concurrency-Safe Double-Booking Prevention
Before inserting a booking record or displaying a specialist as available, the engine runs an atomic SQL check:

```sql
SELECT COUNT(*) FROM bookings 
WHERE technician_id = ? 
  AND slot_date = ? 
  AND slot_time = ? 
  AND status != 'Cancelled';
```

If a collision is detected, candidate ranking partitions the technician into the `busy_candidates` bucket and blocks slot reservation with `HTTP 409 Conflict`.

---

## 4. Relational Database Schema (`smartserve.db`)

The database is built on four core normalized relational tables:

### `users`
Stores customer and technician accounts with hashed passwords and role specifications.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(32)` | `PRIMARY KEY` | Unique user identifier (`usr-cust-01`) |
| `name` | `VARCHAR(100)` | `NOT NULL` | Full user name |
| `email` | `VARCHAR(120)` | `UNIQUE, NOT NULL` | Login email address |
| `password_hash`| `VARCHAR(255)` | `NOT NULL` | Credential hash |
| `role` | `VARCHAR(20)` | `NOT NULL` | Role (`customer` or `technician`) |
| `phone` | `VARCHAR(30)` | `NOT NULL` | Contact phone number |
| `address` | `TEXT` | `NOT NULL` | Default service address |
| `avatar` | `VARCHAR(10)` | `DEFAULT 'U'` | Initials badge |
| `created_at` | `VARCHAR(30)` | `NOT NULL` | Registration timestamp |

### `technicians`
Stores licensed trade professionals, base rates, portfolio assets, and metrics.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(32)` | `PRIMARY KEY` | Unique provider identifier (`prov-elec-01`) |
| `name` | `VARCHAR(100)` | `NOT NULL` | Professional name |
| `title` | `VARCHAR(150)` | `NOT NULL` | Trade title / specialty |
| `category` | `VARCHAR(100)` | `NOT NULL` | Trade discipline |
| `location` | `VARCHAR(150)` | `NOT NULL` | Local operating base |
| `rating` | `FLOAT` | `NOT NULL` | Verified rating average (out of 5.0) |
| `distance_km` | `FLOAT` | `NOT NULL` | Proximity to Cantonment hub |
| `base_price` | `FLOAT` | `NOT NULL` | Standard inspection fee in BDT |
| `completed_tasks`| `INTEGER` | `DEFAULT 0` | Total completed work orders |
| `active_jobs` | `INTEGER` | `DEFAULT 0` | Currently active concurrent jobs |
| `baseline_busy_slots`| `TEXT` | `DEFAULT '[]'` | JSON array of locked time slots |
| `phone` | `VARCHAR(30)` | `NOT NULL` | Technician direct mobile line |
| `badge` | `VARCHAR(50)` | `NULL` | Distinction badge (`Top Rated`, etc.) |
| `avatar_url` | `TEXT` | `NOT NULL` | Technician profile photo URL |
| `portfolio_photos` | `TEXT` | `NOT NULL` | JSON array of field inspection photos |
| `portfolio_video` | `TEXT` | `NOT NULL` | Field demonstration video URL |
| `bio` | `TEXT` | `NOT NULL` | Trade biography & experience |
| `certifications`| `TEXT` | `NOT NULL` | JSON array of trade certifications |

### `bookings`
Tracks appointment lifecycle states, assigned technicians, customer contact, and audit history.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(32)` | `PRIMARY KEY` | Booking code (`BK-XXXXXX`) |
| `booking_code` | `VARCHAR(32)` | `UNIQUE, NOT NULL` | Customer tracking reference |
| `user_id` | `VARCHAR(32)` | `REFERENCES users(id)` | Associated customer account |
| `technician_id`| `VARCHAR(32)` | `REFERENCES technicians(id)`| Assigned specialist |
| `category` | `VARCHAR(100)` | `NOT NULL` | Service category |
| `slot_date` | `VARCHAR(20)` | `NOT NULL` | Scheduled date (`YYYY-MM-DD`) |
| `slot_time` | `VARCHAR(10)` | `NOT NULL` | 1-Hour window (`HH:MM`) |
| `urgency` | `VARCHAR(20)` | `DEFAULT 'Normal'` | Urgency (`Normal` or `Emergency`) |
| `client_name` | `VARCHAR(100)` | `NOT NULL` | Service recipient name |
| `client_phone` | `VARCHAR(30)` | `NOT NULL` | On-site contact phone |
| `client_address`| `TEXT` | `NOT NULL` | Physical premises address |
| `notes` | `TEXT` | `NULL` | Issue description |
| `status` | `VARCHAR(30)` | `DEFAULT 'Requested'`| Lifecycle milestone |
| `history` | `TEXT` | `NOT NULL` | JSON chronological audit trail |
| `created_at` | `VARCHAR(30)` | `NOT NULL` | Reservation timestamp |

### `invoices`
Issued automatically upon milestone completion with tax breakdown and billing references.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(32)` | `PRIMARY KEY` | Invoice identifier (`INV-XXXXXX`) |
| `booking_id` | `VARCHAR(32)` | `REFERENCES bookings(id)` | Parent booking record |
| `invoice_code` | `VARCHAR(32)` | `NOT NULL` | Billing reference number |
| `base_price` | `FLOAT` | `NOT NULL` | Base trade rate |
| `emergency_fee`| `FLOAT` | `DEFAULT 0.0` | Urgent dispatch fee |
| `platform_fee` | `FLOAT` | `DEFAULT 50.0` | Insurance and safety fee |
| `vat_amount` | `FLOAT` | `NOT NULL` | 5% Government VAT |
| `total_amount` | `FLOAT` | `NOT NULL` | Net grand total in BDT |
| `issued_at` | `VARCHAR(30)` | `NOT NULL` | Generation timestamp |

---

## 5. State Machine & Lifecycle Transitions

Tickets advance sequentially through a strict five-stage deterministic state machine. Skipping stages or invalid backwards transitions are rejected with `HTTP 400 Bad Request`:

```
[1. Requested] ──────> [2. Accepted] ──────> [3. On the Way] ──────> [4. In Progress] ──────> [5. Completed]
  • Slot Reserved        • Specialist           • Field Travel        • Diagnostics          • Active Job -1
  • Ticket Created         Acknowledged           Initiated             Active                 • Invoice Issued
```

### Invoicing Trigger
Transitioning a booking into `Completed`:
1. Decrements the technician's `active_jobs` counter by 1.
2. Increments `completed_tasks` by 1.
3. Automatically computes tax line items and persists a record to the `invoices` table.

---

## 6. REST API Endpoints

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Consumer entry portal | `200`, `302` |
| `GET` | `/services/<category>` | Specialist catalog & filter interface | `200` |
| `GET` | `/checkout/<technician_id>` | Dedicated checkout and cost calculation | `200`, `302` |
| `POST`| `/checkout` | Reserve slot & create booking record | `200`, `302`, `409` |
| `GET` | `/orders/<booking_code>` | Real-time order tracking & printable receipt | `200`, `302` |
| `POST`| `/book` | Backward-compatible booking endpoint | `200`, `409` |
| `POST`| `/auto-assign-emergency` | Instant heuristic technician dispatch | `200`, `409` |
| `POST`| `/update-status/<id>/<status>`| Advance lifecycle milestone | `200`, `400` |
| `POST`| `/login` | Authenticate customer or technician | `200`, `302`, `401` |
| `POST`| `/signup` | Register new account | `200`, `302`, `400` |
| `GET` | `/logout` | Terminate session | `302` |
| `GET` | `/api/summary` | Service metrics & status distribution | `200` |
| `POST`| `/api/seed-demo` | Populate demo tickets across all 5 stages | `200` |
| `POST`| `/api/reset` | Flush bookings and restore default state | `200` |

---

## 7. Local Setup & Verification Guide

### 7.1 Environment Initialization
Clone the repository and create an isolated virtual environment:

```bash
# Navigate to project directory
cd smart_service_hackathon

# Initialize virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (Git Bash / MSYS2):
source venv/bin/activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 7.2 Database Setup & Schema Inspection
Initialize the SQLite schema and populate pre-seeded technicians and demo accounts:

```bash
python database.py
```

*Expected Output:*
```
[INIT] Initializing and verifying SmartServe SQLite Database...
======================================================================
DATABASE TABLES IN smartserve.db
======================================================================
  * Table: bookings         | Row Count: 0
  * Table: invoices         | Row Count: 0
  * Table: technicians      | Row Count: 18
  * Table: users            | Row Count: 2
...
```

### 7.3 Automated Unit & Integration Tests
Execute the test suite to verify scoring formulas, double-booking prevention, state progression, and RBAC guards:

```bash
python test_engine.py
```

*Expected Output:*
```
----------------------------------------------------------------------
Ran 17 tests in 0.310s

OK
```

### 7.4 5-Stage Demo Pipeline Verification
Run the end-to-end simulation script verifying seed data, emergency boost heuristics, collision blocking, milestone progression, and digital tax invoice issuance:

```bash
python verify_demo.py
```

*Expected Output:*
```
[PASS] 1. Seed Baseline Demo Data
[PASS] 2. Matching Engine Scoring & Urgency Boost
[PASS] 3. Double-Booking Prevention Shield
[PASS] 4. 5-Stage Sequential Progression
[PASS] 5. Automated Digital Invoice Generation
[SUCCESS] ALL 5 PIPELINE STAGES PASSED (100% INTEGRITY)
```

### 7.5 Starting the Application
Start the local Flask development server:

```bash
python app.py
```

Access the application in your browser at `http://127.0.0.1:5000`.

### Pre-Configured Demo Credentials
| Persona | Email | Password | Access Rights |
| :--- | :--- | :--- | :--- |
| **Customer** | `customer@smartserve.local` | `pass123` | Booking catalog, checkout, order tracking |
| **Technician** | `tech@smartserve.local` | `pass123` | Operations Kanban, milestone advancement |
