"""
Persistent SQLite database layer for SmartServe.
Provides schema management, relational tables, and parameterized queries using standard library sqlite3.
"""
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smartserve.db")

CATEGORIES = [
    "Electrical Engineering",
    "Plumbing & Pipefitting",
    "HVAC & Appliance Care",
    "Pest Control & Hygiene",
    "Carpentry & Woodwork",
    "Vehicle Maintenance"
]

CATEGORY_ALIASES = {
    "Appliance & Gadget Repair": "HVAC & Appliance Care",
    "Plumbing": "Plumbing & Pipefitting",
    "Electrical": "Electrical Engineering",
    "Cleaning & Pest Control": "Pest Control & Hygiene",
    "Home Maintenance": "Carpentry & Woodwork",
    "Car Care & Repair": "Vehicle Maintenance"
}

STATUS_FLOW = ["Requested", "Accepted", "On the Way", "In Progress", "Completed"]

INITIAL_USERS = [
    {
        "id": "usr-cust-01",
        "email": "customer@smartserve.local",
        "password": "pass123",
        "name": "Suaib Islam",
        "role": "customer",
        "phone": "+880 1711-223344",
        "address": "Quarter 12/B, Cantonment Housing, Saidpur",
        "avatar": "SI"
    },
    {
        "id": "usr-tech-01",
        "email": "tech@smartserve.local",
        "password": "pass123",
        "name": "Kazi Rashedul Karim",
        "role": "technician",
        "phone": "+880 1914-112233",
        "address": "Railgate Commercial Hub, Saidpur",
        "avatar": "KR"
    }
]

INITIAL_PROVIDERS = [
    # Electrical Engineering
    {
        "id": "prov-elec-01",
        "name": "Md. Tanvir Hossain",
        "category": "Electrical Engineering",
        "title": "Senior Industrial & Residential Electrician",
        "location": "Saidpur Cantonment Area",
        "rating": 4.9,
        "distance_km": 1.4,
        "price": 600.0,
        "busy_slots": ["2026-09-08 11:00"],
        "completed_count": 142,
        "active_jobs": 1,
        "phone": "+880 1712-345678",
        "specialty": "Distribution boards, industrial wiring, short-circuit recovery",
        "badge": "Top Rated"
    },
    {
        "id": "prov-elec-02",
        "name": "ElectroCare Engineering Ltd.",
        "category": "Electrical Engineering",
        "title": "Licensed Electrical Contractors",
        "location": "Shaheed Smrity Road",
        "rating": 4.4,
        "distance_km": 3.2,
        "price": 500.0,
        "busy_slots": ["2026-09-08 13:00", "2026-09-08 17:00"],
        "completed_count": 89,
        "active_jobs": 0,
        "phone": "+880 1819-876543",
        "specialty": "Backup generators, smart inverter setups, surge suppression",
        "badge": "Best Value"
    },
    {
        "id": "prov-elec-03",
        "name": "Kazi Rashedul Karim",
        "category": "Electrical Engineering",
        "title": "Certified Rapid-Response Wireman",
        "location": "Railgate Commercial Hub",
        "rating": 4.2,
        "distance_km": 0.8,
        "price": 420.0,
        "busy_slots": ["2026-09-08 10:00"],
        "completed_count": 58,
        "active_jobs": 0,
        "phone": "+880 1914-112233",
        "specialty": "Breaker replacements, switchgear repairs, appliance hookups",
        "badge": "Fastest Arrival"
    },
    # Plumbing & Pipefitting
    {
        "id": "prov-plumb-01",
        "name": "Engr. Kamrul Hasan",
        "category": "Plumbing & Pipefitting",
        "title": "Master Sanitary & Pipefitting Specialist",
        "location": "Airport Road, Saidpur",
        "rating": 4.8,
        "distance_km": 1.7,
        "price": 550.0,
        "busy_slots": ["2026-09-08 12:00"],
        "completed_count": 124,
        "active_jobs": 1,
        "phone": "+880 1723-456789",
        "specialty": "Pressure pumps, main supply leakages, sanitary fittings",
        "badge": "Top Rated"
    },
    {
        "id": "prov-plumb-02",
        "name": "Shafiqul Pipe Works",
        "category": "Plumbing & Pipefitting",
        "title": "Drainage & Sewerage Contractor",
        "location": "Central Bus Stand area",
        "rating": 4.3,
        "distance_km": 4.8,
        "price": 450.0,
        "busy_slots": ["2026-09-08 10:00", "2026-09-08 16:00"],
        "completed_count": 67,
        "active_jobs": 0,
        "phone": "+880 1834-567890",
        "specialty": "Underground pipeline clearing, sink clogs, valve replacements",
        "badge": "Best Value"
    },
    {
        "id": "prov-plumb-03",
        "name": "HydroFix Emergency Plumbers",
        "category": "Plumbing & Pipefitting",
        "title": "24/7 Rapid Emergency Response Team",
        "location": "BAUST Road Junction",
        "rating": 4.7,
        "distance_km": 0.7,
        "price": 680.0,
        "busy_slots": ["2026-09-08 14:00"],
        "completed_count": 103,
        "active_jobs": 0,
        "phone": "+880 1925-678901",
        "specialty": "Burst pipe isolation, overhead tank overflow, water filtration",
        "badge": "Fastest Arrival"
    },
    # HVAC & Appliance Care
    {
        "id": "prov-app-01",
        "name": "Ariful Islam",
        "category": "HVAC & Appliance Care",
        "title": "Certified Inverter AC & Refrigeration Technician",
        "location": "Cantonment Officers Quarter Zone",
        "rating": 4.9,
        "distance_km": 2.0,
        "price": 650.0,
        "busy_slots": ["2026-09-08 10:00", "2026-09-08 14:00"],
        "completed_count": 91,
        "active_jobs": 1,
        "phone": "+880 1736-789012",
        "specialty": "Inverter AC diagnostics, compressor repairs, gas charging",
        "badge": "Top Rated"
    },
    {
        "id": "prov-app-02",
        "name": "Apex Appliance Solutions",
        "category": "HVAC & Appliance Care",
        "title": "Authorized Multibrand Appliance Center",
        "location": "Railway Colony Main Rd",
        "rating": 4.6,
        "distance_km": 4.1,
        "price": 500.0,
        "busy_slots": ["2026-09-08 11:00"],
        "completed_count": 73,
        "active_jobs": 0,
        "phone": "+880 1847-890123",
        "specialty": "Washing machines, microwave ovens, deep freezers",
        "badge": "Best Value"
    },
    {
        "id": "prov-app-03",
        "name": "Tareq Smart Appliance Lab",
        "category": "HVAC & Appliance Care",
        "title": "Consumer Electronics Specialist",
        "location": "Saidpur Plaza Market",
        "rating": 3.9,
        "distance_km": 1.1,
        "price": 380.0,
        "busy_slots": ["2026-09-08 09:00", "2026-09-08 15:00"],
        "completed_count": 44,
        "active_jobs": 0,
        "phone": "+880 1958-901234",
        "specialty": "Water purifiers, induction cooktops, small smart devices",
        "badge": "Fastest Arrival"
    },
    # Pest Control & Hygiene
    {
        "id": "prov-clean-01",
        "name": "BioShield Pest Control Services",
        "category": "Pest Control & Hygiene",
        "title": "Public Health Fumigation & Hygiene Agency",
        "location": "Bangabandhu Road",
        "rating": 4.8,
        "distance_km": 2.5,
        "price": 1150.0,
        "busy_slots": ["2026-09-08 09:00", "2026-09-08 14:00"],
        "completed_count": 98,
        "active_jobs": 0,
        "phone": "+880 1749-012345",
        "specialty": "Eco-friendly termite barrier, odorless gel treatment, bedbugs",
        "badge": "Top Rated"
    },
    {
        "id": "prov-clean-02",
        "name": "CleanPro Environmental Sanitation",
        "category": "Pest Control & Hygiene",
        "title": "Commercial & Residential Hygiene Team",
        "location": "New Town Sector 2",
        "rating": 4.3,
        "distance_km": 3.6,
        "price": 900.0,
        "busy_slots": ["2026-09-08 15:00"],
        "completed_count": 62,
        "active_jobs": 0,
        "phone": "+880 1850-123456",
        "specialty": "Deep disinfection, kitchen grease extraction, water tank wash",
        "badge": "Best Value"
    },
    {
        "id": "prov-clean-03",
        "name": "Rapid Exterminators North",
        "category": "Pest Control & Hygiene",
        "title": "Emergency Rodent & Pest Dispatch",
        "location": "Saidpur Old Station area",
        "rating": 4.5,
        "distance_km": 1.2,
        "price": 1050.0,
        "busy_slots": ["2026-09-08 10:00"],
        "completed_count": 79,
        "active_jobs": 0,
        "phone": "+880 1961-234567",
        "specialty": "Mosquito thermal fogging, cockroach eradication, sanitization",
        "badge": "Fastest Arrival"
    },
    # Carpentry & Woodwork
    {
        "id": "prov-maint-01",
        "name": "Farhan Ahmed",
        "category": "Carpentry & Woodwork",
        "title": "Master Cabinetmaker & Structural Joiner",
        "location": "College Road, Saidpur",
        "rating": 4.7,
        "distance_km": 2.2,
        "price": 750.0,
        "busy_slots": ["2026-09-08 11:00"],
        "completed_count": 82,
        "active_jobs": 1,
        "phone": "+880 1772-345678",
        "specialty": "Door alignment, concealed cabinetry, solid teak refinishing",
        "badge": "Top Rated"
    },
    {
        "id": "prov-maint-02",
        "name": "Saidpur Wood Craft Co.",
        "category": "Carpentry & Woodwork",
        "title": "Architectural Woodwork Contractors",
        "location": "Kundal Market Yard",
        "rating": 4.4,
        "distance_km": 4.0,
        "price": 700.0,
        "busy_slots": ["2026-09-08 13:00"],
        "completed_count": 64,
        "active_jobs": 0,
        "phone": "+880 1883-456789",
        "specialty": "Furniture assembly, kitchen partitions, modular shelving",
        "badge": "Best Value"
    },
    {
        "id": "prov-maint-03",
        "name": "Al-Amin Door & Lock Solutions",
        "category": "Carpentry & Woodwork",
        "title": "Rapid Locksmith & Joinery Services",
        "location": "Thana Road Center",
        "rating": 4.2,
        "distance_km": 0.9,
        "price": 550.0,
        "busy_slots": ["2026-09-08 16:00"],
        "completed_count": 51,
        "active_jobs": 0,
        "phone": "+880 1994-567890",
        "specialty": "Digital door locks, mortise latch repairs, hinge re-hanging",
        "badge": "Fastest Arrival"
    },
    # Vehicle Maintenance
    {
        "id": "prov-car-01",
        "name": "Mahmudul Huq",
        "category": "Vehicle Maintenance",
        "title": "Lead Automotive Diagnostician",
        "location": "Dinajpur Highway Interchange",
        "rating": 4.9,
        "distance_km": 1.8,
        "price": 950.0,
        "busy_slots": ["2026-09-08 10:00", "2026-09-08 12:00"],
        "completed_count": 118,
        "active_jobs": 1,
        "phone": "+880 1785-678901",
        "specialty": "OBD-II computer diagnostics, hybrid inverter check, electricals",
        "badge": "Top Rated"
    },
    {
        "id": "prov-car-02",
        "name": "Precision Auto Care Hub",
        "category": "Vehicle Maintenance",
        "title": "General Mechanical & Lubrication Workshop",
        "location": "Bypass Circle",
        "rating": 4.3,
        "distance_km": 3.7,
        "price": 700.0,
        "busy_slots": ["2026-09-08 14:00"],
        "completed_count": 59,
        "active_jobs": 0,
        "phone": "+880 1896-789012",
        "specialty": "Brake shoe replacement, coolant flush, routine oil service",
        "badge": "Best Value"
    },
    {
        "id": "prov-car-03",
        "name": "RoadGuard Emergency Breakdown",
        "category": "Vehicle Maintenance",
        "title": "Mobile Roadside Assistance & Recovery",
        "location": "Saidpur Railgate Crossing",
        "rating": 4.7,
        "distance_km": 0.8,
        "price": 1100.0,
        "busy_slots": ["2026-09-08 15:00"],
        "completed_count": 87,
        "active_jobs": 0,
        "phone": "+880 1907-890123",
        "specialty": "Battery jumpstarts, on-site puncture vulcanizing, towing assistance",
        "badge": "Fastest Arrival"
    }
]

TRADE_PORTFOLIO_ASSETS = {
    "Electrical Engineering": {
        "photos": [
            "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80"
        ],
        "video": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "certifications": ["Certified Industrial Electrician (Grade A)", "NFPA 70 National Electrical Code Compliant", "High-Voltage Safety Certified"],
        "bio": "Over 10+ years specializing in residential power distribution, three-phase load balancing, and rapid short-circuit mitigation across Saidpur Cantonment."
    },
    "Plumbing & Pipefitting": {
        "photos": [
            "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80"
        ],
        "video": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "certifications": ["Master Sanitary Inspector License", "Underground Hydro-Jetting Certified", "Commercial Pressure System Specialist"],
        "bio": "Expert pipefitter adept at complex high-pressure pump installations, concealed leakage pinpointing, and municipal drainage restoration."
    },
    "HVAC & Appliance Care": {
        "photos": [
            "https://images.unsplash.com/photo-1631545806609-b42551a37c95?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1585338107529-13afc5f02586?auto=format&fit=crop&w=800&q=80"
        ],
        "video": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "certifications": ["EPA Section 608 Universal Certification", "Inverter Refrigeration Specialist", "Commercial Air Handling Certified"],
        "bio": "Certified HVAC technician with deep expertise in modern variable refrigerant flow (VRF) systems, multi-split inverter ACs, and high-efficiency heat exchangers."
    },
    "Pest Control & Hygiene": {
        "photos": [
            "https://images.unsplash.com/photo-1584820927498-cfe5211fd8bf?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1585832770485-e68a5dbfad52?auto=format&fit=crop&w=800&q=80"
        ],
        "video": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "certifications": ["WHO/FAO Vector Management Certified", "GreenPest Eco-Shield Operator", "Commercial Food Safety Sanitation"],
        "bio": "Public health sanitation expert providing hospital-grade disinfection, odorless non-toxic gel applications, and subterranean termite barrier systems."
    },
    "Carpentry & Woodwork": {
        "photos": [
            "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1505798577917-a65157d3320a?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80"
        ],
        "video": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "certifications": ["Guild of Master Craftsmen Member", "Architectural Joinery & Millwork Certified", "Smart Lock & Security Hardware Installer"],
        "bio": "Veteran carpenter specialized in precision bespoke cabinetry, silent hydraulic soft-close installations, and high-security architectural door fittings."
    },
    "Vehicle Maintenance": {
        "photos": [
            "https://images.unsplash.com/photo-1486006920555-c77dce18193b?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=800&q=80"
        ],
        "video": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "certifications": ["ASE Certified Master Automobile Technician", "Hybrid & EV Battery Diagnostic Specialist", "Bosch Advanced Electronic Injection"],
        "bio": "Master automotive diagnostician specializing in fast mobile roadside triage, computerized engine scan fault recovery, and brake safety overhaul."
    }
}

PROVIDER_AVATARS = {
    "prov-elec-01": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80",
    "prov-elec-02": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=256&q=80",
    "prov-elec-03": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=256&q=80",
    "prov-plumb-01": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=256&q=80",
    "prov-plumb-02": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=256&q=80",
    "prov-plumb-03": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=256&q=80",
    "prov-app-01": "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=256&q=80",
    "prov-app-02": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=256&q=80",
    "prov-app-03": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=256&q=80",
    "prov-clean-01": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=256&q=80",
    "prov-clean-02": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=256&q=80",
    "prov-clean-03": "https://images.unsplash.com/photo-1566492031773-4f4e44671857?auto=format&fit=crop&w=256&q=80",
    "prov-maint-01": "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?auto=format&fit=crop&w=256&q=80",
    "prov-maint-02": "https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?auto=format&fit=crop&w=256&q=80",
    "prov-maint-03": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=256&q=80",
    "prov-car-01": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=256&q=80",
    "prov-car-02": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=256&q=80",
    "prov-car-03": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=256&q=80"
}

class Database:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initializes tables and seeds initial data if tables are empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'customer',
                    phone TEXT,
                    address TEXT,
                    avatar TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # 2. technicians table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS technicians (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    rating REAL NOT NULL DEFAULT 5.0,
                    base_price REAL NOT NULL DEFAULT 500.0,
                    location TEXT NOT NULL,
                    distance_km REAL NOT NULL DEFAULT 1.0,
                    active_jobs INTEGER NOT NULL DEFAULT 0,
                    phone TEXT,
                    completed_count INTEGER NOT NULL DEFAULT 0,
                    completed_tasks INTEGER NOT NULL DEFAULT 0,
                    specialty TEXT,
                    badge TEXT,
                    avatar_url TEXT,
                    portfolio_photos TEXT,
                    portfolio_video TEXT,
                    bio TEXT,
                    certifications TEXT,
                    baseline_busy_slots TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
            """)

            # Migrate missing columns if technicians table already exists
            cursor.execute("PRAGMA table_info(technicians)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col_name, col_def in [
                ("completed_tasks", "INTEGER NOT NULL DEFAULT 0"),
                ("avatar_url", "TEXT"),
                ("portfolio_photos", "TEXT"),
                ("portfolio_video", "TEXT"),
                ("bio", "TEXT"),
                ("certifications", "TEXT"),
            ]:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE technicians ADD COLUMN {col_name} {col_def};")

            # 3. bookings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id TEXT PRIMARY KEY,
                    booking_code TEXT NOT NULL,
                    user_id TEXT,
                    technician_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    slot_date TEXT NOT NULL,
                    slot_time TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'Normal',
                    status TEXT NOT NULL DEFAULT 'Requested',
                    client_name TEXT NOT NULL,
                    client_phone TEXT NOT NULL,
                    client_address TEXT NOT NULL,
                    notes TEXT,
                    history_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (technician_id) REFERENCES technicians(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)

            # 4. invoices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    booking_id TEXT UNIQUE NOT NULL,
                    invoice_code TEXT NOT NULL,
                    base_price REAL NOT NULL,
                    emergency_fee REAL NOT NULL DEFAULT 0.0,
                    platform_fee REAL NOT NULL DEFAULT 50.0,
                    vat_amount REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    client_name TEXT NOT NULL,
                    client_phone TEXT NOT NULL,
                    client_address TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    provider_title TEXT,
                    category TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    FOREIGN KEY (booking_id) REFERENCES bookings(id)
                );
            """)
            conn.commit()

            # Seed if technicians table is empty
            cursor.execute("SELECT COUNT(*) FROM technicians")
            tech_count = cursor.fetchone()[0]
            if tech_count == 0:
                self._seed_initial_data(conn)

    def _seed_initial_data(self, conn: sqlite3.Connection) -> None:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = conn.cursor()

        # Seed users
        for u in INITIAL_USERS:
            cursor.execute("""
                INSERT OR IGNORE INTO users (id, name, email, password_hash, role, phone, address, avatar, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                u["id"], u["name"], u["email"], u["password"], u["role"],
                u.get("phone", ""), u.get("address", ""), u.get("avatar", "U"), now_str
            ))

        # Seed technicians
        for p in INITIAL_PROVIDERS:
            cat_assets = TRADE_PORTFOLIO_ASSETS.get(p["category"], {})
            avatar_url = p.get("avatar_url") or PROVIDER_AVATARS.get(p["id"], "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80")
            photos = p.get("portfolio_photos") or cat_assets.get("photos", [])
            video = p.get("portfolio_video") or cat_assets.get("video", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4")
            bio = p.get("bio") or cat_assets.get("bio", "Certified trade specialist with years of field experience in Saidpur.")
            certs = p.get("certifications") or cat_assets.get("certifications", ["Certified Professional Specialist"])
            completed = p.get("completed_count", 0)

            cursor.execute("""
                INSERT OR IGNORE INTO technicians 
                (id, name, title, category, rating, base_price, location, distance_km, active_jobs, phone, completed_count, completed_tasks, specialty, badge, avatar_url, portfolio_photos, portfolio_video, bio, certifications, baseline_busy_slots, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["name"], p["title"], p["category"], p["rating"], p["price"],
                p["location"], p["distance_km"], p.get("active_jobs", 0), p.get("phone", ""),
                completed, completed, p.get("specialty", ""), p.get("badge", ""),
                avatar_url, json.dumps(photos), video, bio, json.dumps(certs),
                json.dumps(p.get("busy_slots", [])), now_str
            ))
        conn.commit()

    def reset(self) -> None:
        """Wipes and resets the SQLite database to baseline seeded state."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM invoices;")
            cursor.execute("DELETE FROM bookings;")
            cursor.execute("DELETE FROM technicians;")
            cursor.execute("DELETE FROM users;")
            conn.commit()
            self._seed_initial_data(conn)

    # ------------------ Technicians / Providers ------------------ #

    def _hydrate_technician_dict(self, t: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches technician dictionary with decoded portfolio media, avatars, and aliases."""
        cat_assets = TRADE_PORTFOLIO_ASSETS.get(t.get("category", ""), {})
        
        # Portfolio photos
        photos = t.get("portfolio_photos")
        if isinstance(photos, str):
            try:
                t["portfolio_photos"] = json.loads(photos)
            except Exception:
                t["portfolio_photos"] = cat_assets.get("photos", [])
        elif not photos:
            t["portfolio_photos"] = cat_assets.get("photos", [])

        # Certifications
        certs = t.get("certifications")
        if isinstance(certs, str):
            try:
                t["certifications"] = json.loads(certs)
            except Exception:
                t["certifications"] = cat_assets.get("certifications", ["Certified Professional Specialist"])
        elif not certs:
            t["certifications"] = cat_assets.get("certifications", ["Certified Professional Specialist"])

        # Avatar
        if not t.get("avatar_url"):
            t["avatar_url"] = PROVIDER_AVATARS.get(t.get("id", ""), "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80")

        # Video
        if not t.get("portfolio_video"):
            t["portfolio_video"] = cat_assets.get("video", "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4")

        # Bio
        if not t.get("bio"):
            t["bio"] = cat_assets.get("bio", "Certified professional trade technician in Saidpur.")

        # Numbers
        t["price"] = float(t.get("base_price", 500.0))
        t["active_jobs_count"] = int(t.get("active_jobs", 0))
        t["completed_count"] = int(t.get("completed_count", 0))
        t["completed_tasks"] = int(t.get("completed_tasks") if t.get("completed_tasks") is not None else t["completed_count"])
        return t

    def get_providers(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all technicians, optionally filtered by category, with dynamic busy slots."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if category:
                canonical = CATEGORY_ALIASES.get(category, category)
                cursor.execute("""
                    SELECT * FROM technicians 
                    WHERE category = ? OR category = ?
                    ORDER BY rating DESC
                """, (canonical, category))
            else:
                cursor.execute("SELECT * FROM technicians ORDER BY rating DESC")
            
            rows = cursor.fetchall()
            technicians: List[Dict[str, Any]] = []

            for row in rows:
                t = dict(row)
                tech_id = t["id"]

                # Baseline busy slots from technician definition
                baseline = json.loads(t.get("baseline_busy_slots") or "[]")

                # Active booking reservations for this technician
                cursor.execute("""
                    SELECT slot_date || ' ' || slot_time AS full_slot 
                    FROM bookings 
                    WHERE technician_id = ? AND status != 'Cancelled'
                """, (tech_id,))
                active_booking_slots = [r["full_slot"] for r in cursor.fetchall()]

                # Merge and preserve order/uniqueness
                combined_busy = list(dict.fromkeys(baseline + active_booking_slots))
                t["busy_slots"] = combined_busy

                # Hydrate portfolio assets, avatars, and numbers
                t = self._hydrate_technician_dict(t)
                technicians.append(t)

            return technicians

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single technician record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM technicians WHERE id = ?", (provider_id,))
            row = cursor.fetchone()
            if not row:
                return None
            t = dict(row)
            baseline = json.loads(t.get("baseline_busy_slots") or "[]")
            cursor.execute("""
                SELECT slot_date || ' ' || slot_time AS full_slot 
                FROM bookings 
                WHERE technician_id = ? AND status != 'Cancelled'
            """, (provider_id,))
            active_booking_slots = [r["full_slot"] for r in cursor.fetchall()]
            t["busy_slots"] = list(dict.fromkeys(baseline + active_booking_slots))
            t = self._hydrate_technician_dict(t)
            return t

    def is_slot_busy(self, provider_id: str, slot: str) -> bool:
        """Checks if technician has a conflicting booking or baseline reservation for slot."""
        parts = slot.strip().split(" ", 1)
        slot_date = parts[0]
        slot_time = parts[1] if len(parts) > 1 else ""

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Check active bookings table collision
            cursor.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE technician_id = ? AND slot_date = ? AND slot_time = ? AND status != 'Cancelled'
            """, (provider_id, slot_date, slot_time))
            if cursor.fetchone()[0] > 0:
                return True

            # 2. Check baseline busy slots
            cursor.execute("SELECT baseline_busy_slots FROM technicians WHERE id = ?", (provider_id,))
            row = cursor.fetchone()
            if row:
                baseline = json.loads(row[0] or "[]")
                if slot in baseline:
                    return True

            return False

    # ------------------ Bookings & Lifecycle ------------------ #

    def create_booking(
        self,
        provider_id: str,
        slot: str,
        urgency: str,
        client_name: str,
        client_phone: str,
        client_address: str,
        notes: str = "",
        user_id: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Creates a booking record and reserves the technician calendar slot."""
        tech = self.get_provider(provider_id)
        if not tech:
            return None, "Technician record not found."

        if self.is_slot_busy(provider_id, slot):
            return None, f"Scheduling conflict: {tech['name']} is booked for {slot}."

        parts = slot.strip().split(" ", 1)
        slot_date = parts[0]
        slot_time = parts[1] if len(parts) > 1 else ""

        booking_code = f"BK-{uuid.uuid4().hex[:6].upper()}"
        booking_id = booking_code
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        history = [
            {
                "status": "Requested",
                "timestamp": now_str,
                "note": "Appointment confirmed. Technician reserved on calendar."
            }
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bookings 
                (id, booking_code, user_id, technician_id, category, slot_date, slot_time, priority, status, client_name, client_phone, client_address, notes, history_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Requested', ?, ?, ?, ?, ?, ?)
            """, (
                booking_id, booking_code, user_id, provider_id, tech["category"],
                slot_date, slot_time, urgency, client_name or "Client", client_phone or "+880 1700-000000",
                client_address or "Saidpur, Nilphamari", notes or "Standard service dispatch requested.",
                json.dumps(history), now_str
            ))

            # Increment technician active jobs
            cursor.execute("UPDATE technicians SET active_jobs = active_jobs + 1 WHERE id = ?", (provider_id,))
            conn.commit()

        booking = self.get_booking(booking_id)
        return booking, None

    def update_status(self, booking_id: str, new_status: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Advances booking lifecycle through the sequential 5-stage pipeline."""
        booking = self.get_booking(booking_id)
        if not booking:
            return None, "Appointment record not found."

        if new_status not in STATUS_FLOW:
            return None, f"Unsupported workflow state: {new_status}."

        curr_idx = STATUS_FLOW.index(booking["status"])
        new_idx = STATUS_FLOW.index(new_status)

        if new_idx != curr_idx + 1:
            return None, f"Invalid state transition: '{booking['status']}' cannot advance directly to '{new_status}'."

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        history = list(booking.get("history", []))
        history.append({
            "status": new_status,
            "timestamp": now_str,
            "note": f"Service milestone transitioned to {new_status}."
        })

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bookings 
                SET status = ?, history_json = ? 
                WHERE id = ?
            """, (new_status, json.dumps(history), booking_id))

            if new_status == "Completed":
                tech_id = booking["provider_id"]
                cursor.execute("""
                    UPDATE technicians 
                    SET completed_count = completed_count + 1,
                        completed_tasks = completed_tasks + 1,
                        active_jobs = MAX(0, active_jobs - 1)
                    WHERE id = ?
                """, (tech_id,))

                # Generate and insert official tax invoice
                invoice_data = self.generate_invoice(booking)
                cursor.execute("""
                    INSERT OR REPLACE INTO invoices
                    (id, booking_id, invoice_code, base_price, emergency_fee, platform_fee, vat_amount, total_amount, client_name, client_phone, client_address, provider_name, provider_title, category, slot, urgency, issued_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_data["invoice_no"], booking_id, invoice_data["invoice_code"],
                    invoice_data["base_price"], invoice_data["emergency_fee"], invoice_data["platform_fee"],
                    invoice_data["vat"], invoice_data["grand_total"], invoice_data["client_name"],
                    invoice_data["client_phone"], invoice_data["client_address"], invoice_data["provider_name"],
                    invoice_data["provider_title"], invoice_data["category"], invoice_data["slot"],
                    invoice_data["urgency"], invoice_data["issue_date"]
                ))
            conn.commit()

        updated_booking = self.get_booking(booking_id)
        return updated_booking, None

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a single booking with joined technician details and generated invoice."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.*, t.name AS provider_name, t.title AS provider_title, 
                       t.phone AS provider_phone, t.rating, t.base_price, t.distance_km
                FROM bookings b
                LEFT JOIN technicians t ON b.technician_id = t.id
                WHERE b.id = ? OR b.booking_code = ?
            """, (booking_id, booking_id))
            row = cursor.fetchone()
            if not row:
                return None

            b = dict(row)
            b["provider_id"] = b["technician_id"]
            b["slot"] = f"{b['slot_date']} {b['slot_time']}".strip()
            b["urgency"] = b["priority"]
            b["price"] = float(b.get("base_price") or 500.0)
            b["history"] = json.loads(b.get("history_json") or "[]")

            # Check invoice
            cursor.execute("SELECT * FROM invoices WHERE booking_id = ?", (b["id"],))
            inv_row = cursor.fetchone()
            if inv_row:
                inv = dict(inv_row)
                b["invoice"] = {
                    "invoice_no": inv["invoice_code"],
                    "invoice_code": inv["invoice_code"],
                    "issue_date": inv["issued_at"],
                    "issued_at": inv["issued_at"],
                    "booking_id": inv["booking_id"],
                    "client_name": inv["client_name"],
                    "client_phone": inv["client_phone"],
                    "client_address": inv["client_address"],
                    "provider_name": inv["provider_name"],
                    "provider_title": inv.get("provider_title", "Technician"),
                    "category": inv["category"],
                    "slot": inv["slot"],
                    "urgency": inv["urgency"],
                    "base_price": float(inv["base_price"]),
                    "emergency_fee": float(inv["emergency_fee"]),
                    "platform_fee": float(inv["platform_fee"]),
                    "subtotal": float(inv["base_price"]) + float(inv["emergency_fee"]) + float(inv["platform_fee"]),
                    "vat": float(inv["vat_amount"]),
                    "vat_amount": float(inv["vat_amount"]),
                    "grand_total": float(inv["total_amount"]),
                    "total_amount": float(inv["total_amount"])
                }
            else:
                b["invoice"] = None

            return b

    def get_bookings(self) -> List[Dict[str, Any]]:
        """Returns all bookings ordered by creation date descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM bookings ORDER BY created_at DESC, rowid DESC")
            booking_ids = [r["id"] for r in cursor.fetchall()]

        results: List[Dict[str, Any]] = []
        for b_id in booking_ids:
            b = self.get_booking(b_id)
            if b:
                results.append(b)
        return results

    def generate_invoice(self, booking: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates invoice financial line items."""
        base_price = float(booking.get("price", booking.get("base_price", 500.0)))
        is_emergency = str(booking.get("urgency", booking.get("priority", ""))).strip().lower() == "emergency"
        emergency_fee = 250.0 if is_emergency else 0.0
        platform_fee = 50.0
        subtotal = base_price + emergency_fee + platform_fee
        vat = round(subtotal * 0.05, 2)
        grand_total = round(subtotal + vat, 2)
        code = f"INV-{booking['id'][-6:].upper()}"

        return {
            "invoice_no": code,
            "invoice_code": code,
            "issue_date": datetime.now().strftime("%d %b %Y, %H:%M"),
            "issued_at": datetime.now().strftime("%d %b %Y, %H:%M"),
            "booking_id": booking["id"],
            "client_name": booking["client_name"],
            "client_phone": booking["client_phone"],
            "client_address": booking["client_address"],
            "provider_name": booking.get("provider_name", "Technician"),
            "provider_title": booking.get("provider_title", "Specialist"),
            "category": booking["category"],
            "slot": booking.get("slot", f"{booking.get('slot_date', '')} {booking.get('slot_time', '')}".strip()),
            "urgency": booking.get("urgency", booking.get("priority", "Normal")),
            "base_price": base_price,
            "emergency_fee": emergency_fee,
            "platform_fee": platform_fee,
            "subtotal": subtotal,
            "vat": vat,
            "vat_amount": vat,
            "grand_total": grand_total,
            "total_amount": grand_total
        }

    def seed_demo_stages(self) -> int:
        """Seeds 5 demo bookings across the 5 lifecycle states in SQLite."""
        demo_profiles = [
            ("Completed", "prov-plumb-01", "Plumbing & Pipefitting", "2026-09-08 09:00", "Normal", "Prof. Dr. M. A. Rahman", "+880 1711-234567", "Faculty Quarter 4B, BAUST Campus"),
            ("In Progress", "prov-elec-01", "Electrical Engineering", "2026-09-08 10:00", "Emergency", "Tahmina Akter", "+880 1819-345678", "Officers Colony Road 3, Saidpur Cantonment"),
            ("On the Way", "prov-app-01", "HVAC & Appliance Care", "2026-09-08 11:00", "Emergency", "Syed Nazrul Islam", "+880 1912-456789", "Railway Officers Rest House, Station Rd"),
            ("Accepted", "prov-car-01", "Vehicle Maintenance", "2026-09-08 13:00", "Normal", "Nusrat Jahan", "+880 1723-567890", "Green Garden Housing, Airport Bypass"),
            ("Requested", "prov-clean-01", "Pest Control & Hygiene", "2026-09-08 15:00", "Normal", "Kazi Shahriar", "+880 1834-678901", "Shahid Smrity Bhaban, Central Area")
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for status, prov_id, cat, slot, urg, c_name, c_phone, c_addr in demo_profiles:
                tech = self.get_provider(prov_id)
                if not tech:
                    continue

                parts = slot.split(" ", 1)
                slot_date = parts[0]
                slot_time = parts[1] if len(parts) > 1 else ""
                b_id = f"BK-{uuid.uuid4().hex[:6].upper()}"

                hist = []
                target_idx = STATUS_FLOW.index(status)
                for i in range(target_idx + 1):
                    s = STATUS_FLOW[i]
                    hist.append({
                        "status": s,
                        "timestamp": now_str,
                        "note": f"Milestone advanced to {s}."
                    })

                cursor.execute("""
                    INSERT INTO bookings
                    (id, booking_code, user_id, technician_id, category, slot_date, slot_time, priority, status, client_name, client_phone, client_address, notes, history_json, created_at)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    b_id, b_id, prov_id, cat, slot_date, slot_time, urg, status,
                    c_name, c_phone, c_addr, "Demo verification work order.",
                    json.dumps(hist), now_str
                ))

                if status == "Completed":
                    # Generate invoice row
                    booking_dict = {
                        "id": b_id,
                        "price": tech["price"],
                        "urgency": urg,
                        "client_name": c_name,
                        "client_phone": c_phone,
                        "client_address": c_addr,
                        "provider_name": tech["name"],
                        "provider_title": tech["title"],
                        "category": cat,
                        "slot": slot
                    }
                    inv = self.generate_invoice(booking_dict)
                    cursor.execute("""
                        INSERT OR REPLACE INTO invoices
                        (id, booking_id, invoice_code, base_price, emergency_fee, platform_fee, vat_amount, total_amount, client_name, client_phone, client_address, provider_name, provider_title, category, slot, urgency, issued_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        inv["invoice_no"], b_id, inv["invoice_code"],
                        inv["base_price"], inv["emergency_fee"], inv["platform_fee"],
                        inv["vat"], inv["grand_total"], c_name, c_phone, c_addr,
                        tech["name"], tech["title"], cat, slot, urg, inv["issue_date"]
                    ))

            conn.commit()

        return len(self.get_bookings())

    # ------------------ Users & Authentication ------------------ #

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (clean_email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_email(email)
        if user and user.get("password_hash") == password:
            return user
        return None

    def create_user(
        self,
        email: str,
        password: str,
        name: str,
        role: str = "customer",
        phone: str = "",
        address: str = ""
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            return None, "A valid email address is required."
        if not password or len(password) < 4:
            return None, "Password must be at least 4 characters."
        if not name.strip():
            return None, "Name is required."
        if role not in ("customer", "technician"):
            role = "customer"

        if self.get_user_by_email(clean_email):
            return None, f"An account with email '{clean_email}' already exists."

        parts = name.strip().split()
        initials = "".join([p[0].upper() for p in parts[:2]]) if parts else "U"
        user_id = f"usr-{uuid.uuid4().hex[:6]}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, name, email, password_hash, role, phone, address, avatar, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, name.strip(), clean_email, password, role,
                phone.strip() or "+880 1700-000000",
                address.strip() or "Saidpur Cantonment Area",
                initials, now_str
            ))
            conn.commit()

        return self.get_user_by_id(user_id), None

db = Database()
