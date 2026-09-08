"""
Smart Home Service Automation - In-Memory State & Database Manager
BAUST CSE FEST 2026 Competitive Hackathon
"""
import uuid
from datetime import datetime

CATEGORIES = [
    "Appliance & Gadget Repair",
    "Plumbing",
    "Electrical",
    "Cleaning & Pest Control",
    "Home Maintenance",
    "Car Care & Repair"
]

STATUS_FLOW = ["Requested", "Accepted", "On the Way", "In Progress", "Completed"]

INITIAL_PROVIDERS = [
    # Appliance & Gadget Repair
    {
        "id": "prov-app-01",
        "name": "Tanvir Rahman",
        "category": "Appliance & Gadget Repair",
        "rating": 4.9,
        "distance_km": 2.1,
        "price": 650.0,
        "busy_slots": ["2026-09-08 10:00", "2026-09-08 14:00"],
        "completed_count": 84,
        "active_jobs_count": 1,
        "phone": "+880 1711-234567",
        "specialty": "Inverter AC, Smart TV, Microwave",
        "badge": "Top Rated"
    },
    {
        "id": "prov-app-02",
        "name": "QuickFix Appliances Lab",
        "category": "Appliance & Gadget Repair",
        "rating": 4.6,
        "distance_km": 4.5,
        "price": 500.0,
        "busy_slots": ["2026-09-08 11:00"],
        "completed_count": 62,
        "active_jobs_count": 0,
        "phone": "+880 1822-345678",
        "specialty": "Refrigerator & Washing Machine",
        "badge": "Best Value"
    },
    {
        "id": "prov-app-03",
        "name": "Hasan Gadget Clinic",
        "category": "Appliance & Gadget Repair",
        "rating": 3.8,
        "distance_km": 1.2,
        "price": 400.0,
        "busy_slots": ["2026-09-08 09:00", "2026-09-08 15:00"],
        "completed_count": 39,
        "active_jobs_count": 0,
        "phone": "+880 1933-456789",
        "specialty": "Computers, Routers & Small Devices",
        "badge": "Fastest Arrival"
    },

    # Plumbing
    {
        "id": "prov-plumb-01",
        "name": "Kamrul Islam (HydroMaster)",
        "category": "Plumbing",
        "rating": 4.8,
        "distance_km": 1.8,
        "price": 550.0,
        "busy_slots": ["2026-09-08 12:00"],
        "completed_count": 112,
        "active_jobs_count": 1,
        "phone": "+880 1744-567890",
        "specialty": "Pipe Leakage, Water Pumps & Sanitary Fitting",
        "badge": "Top Rated"
    },
    {
        "id": "prov-plumb-02",
        "name": "Shafiq Pipe Solutions",
        "category": "Plumbing",
        "rating": 4.3,
        "distance_km": 5.0,
        "price": 450.0,
        "busy_slots": ["2026-09-08 10:00", "2026-09-08 16:00"],
        "completed_count": 53,
        "active_jobs_count": 0,
        "phone": "+880 1855-678901",
        "specialty": "Drainage Clearing & Kitchen Sinks",
        "badge": "Best Value"
    },
    {
        "id": "prov-plumb-03",
        "name": "Rapid Plumbers 24/7",
        "category": "Plumbing",
        "rating": 4.7,
        "distance_km": 0.8,
        "price": 700.0,
        "busy_slots": ["2026-09-08 14:00"],
        "completed_count": 97,
        "active_jobs_count": 0,
        "phone": "+880 1966-789012",
        "specialty": "Emergency Pipe Burst & Tank Overflow",
        "badge": "Fastest Arrival"
    },

    # Electrical
    {
        "id": "prov-elec-01",
        "name": "Arif Ahmed (VoltCare)",
        "category": "Electrical",
        "rating": 4.9,
        "distance_km": 1.5,
        "price": 600.0,
        "busy_slots": ["2026-09-08 11:00"],
        "completed_count": 140,
        "active_jobs_count": 1,
        "phone": "+880 1777-890123",
        "specialty": "Short Circuit Repair, DB Box & Circuit Breakers",
        "badge": "Top Rated"
    },
    {
        "id": "prov-elec-02",
        "name": "ElectroPower Engineering",
        "category": "Electrical",
        "rating": 4.4,
        "distance_km": 3.2,
        "price": 500.0,
        "busy_slots": ["2026-09-08 13:00", "2026-09-08 17:00"],
        "completed_count": 78,
        "active_jobs_count": 0,
        "phone": "+880 1888-901234",
        "specialty": "Ceiling Fan, Wiring & Generator/IPS",
        "badge": "Best Value"
    },
    {
        "id": "prov-elec-03",
        "name": "SparkSafe Solutions",
        "category": "Electrical",
        "rating": 3.9,
        "distance_km": 0.9,
        "price": 380.0,
        "busy_slots": ["2026-09-08 10:00"],
        "completed_count": 45,
        "active_jobs_count": 0,
        "phone": "+880 1999-012345",
        "specialty": "Switchboard, Socket & Light Fixtures",
        "badge": "Fastest Arrival"
    },

    # Cleaning & Pest Control
    {
        "id": "prov-clean-01",
        "name": "EcoClean & Pest Shield",
        "category": "Cleaning & Pest Control",
        "rating": 4.8,
        "distance_km": 2.8,
        "price": 1200.0,
        "busy_slots": ["2026-09-08 09:00", "2026-09-08 14:00"],
        "completed_count": 89,
        "active_jobs_count": 0,
        "phone": "+880 1700-112233",
        "specialty": "Deep Home Cleaning & Herbal Pest Fumigation",
        "badge": "Top Rated"
    },
    {
        "id": "prov-clean-02",
        "name": "Sparkle Cleaners Ltd.",
        "category": "Cleaning & Pest Control",
        "rating": 4.2,
        "distance_km": 3.5,
        "price": 950.0,
        "busy_slots": ["2026-09-08 15:00"],
        "completed_count": 64,
        "active_jobs_count": 0,
        "phone": "+880 1811-223344",
        "specialty": "Sofa, Carpet & Kitchen Degreasing",
        "badge": "Best Value"
    },
    {
        "id": "prov-clean-03",
        "name": "GreenLife Termite & Pest Control",
        "category": "Cleaning & Pest Control",
        "rating": 4.6,
        "distance_km": 1.1,
        "price": 1100.0,
        "busy_slots": ["2026-09-08 10:00"],
        "completed_count": 76,
        "active_jobs_count": 0,
        "phone": "+880 1922-334455",
        "specialty": "Bedbugs, Cockroaches & Termite Defense",
        "badge": "Fastest Arrival"
    },

    # Home Maintenance
    {
        "id": "prov-maint-01",
        "name": "Farhan Carpentry & Masonry",
        "category": "Home Maintenance",
        "rating": 4.7,
        "distance_km": 2.4,
        "price": 800.0,
        "busy_slots": ["2026-09-08 11:00"],
        "completed_count": 71,
        "active_jobs_count": 1,
        "phone": "+880 1733-445566",
        "specialty": "Furniture Repair, Door Locks & Tiles",
        "badge": "Top Rated"
    },
    {
        "id": "prov-maint-02",
        "name": "Apex Wall Painting & Renovation",
        "category": "Home Maintenance",
        "rating": 4.5,
        "distance_km": 4.2,
        "price": 850.0,
        "busy_slots": ["2026-09-08 13:00"],
        "completed_count": 58,
        "active_jobs_count": 0,
        "phone": "+880 1844-556677",
        "specialty": "Waterproofing, Wall Crack & Touchup Painting",
        "badge": "Best Value"
    },
    {
        "id": "prov-maint-03",
        "name": "Craftsman Handyman Services",
        "category": "Home Maintenance",
        "rating": 4.1,
        "distance_km": 0.7,
        "price": 600.0,
        "busy_slots": ["2026-09-08 16:00"],
        "completed_count": 48,
        "active_jobs_count": 0,
        "phone": "+880 1955-667788",
        "specialty": "Curtain Rods, Shelving, Drilling & Locks",
        "badge": "Fastest Arrival"
    },

    # Car Care & Repair
    {
        "id": "prov-car-01",
        "name": "AutoDoctor On-Demand",
        "category": "Car Care & Repair",
        "rating": 4.9,
        "distance_km": 1.9,
        "price": 1000.0,
        "busy_slots": ["2026-09-08 10:00", "2026-09-08 12:00"],
        "completed_count": 105,
        "active_jobs_count": 1,
        "phone": "+880 1766-778899",
        "specialty": "Battery Jumpstart, OBD Scanner & Oil Service",
        "badge": "Top Rated"
    },
    {
        "id": "prov-car-02",
        "name": "StreetSide Mechanic Co.",
        "category": "Car Care & Repair",
        "rating": 4.3,
        "distance_km": 3.8,
        "price": 750.0,
        "busy_slots": ["2026-09-08 14:00"],
        "completed_count": 52,
        "active_jobs_count": 0,
        "phone": "+880 1877-889900",
        "specialty": "Tire Puncture, Brake Pads & Radiator",
        "badge": "Best Value"
    },
    {
        "id": "prov-car-03",
        "name": "TurboShield Emergency Auto Care",
        "category": "Car Care & Repair",
        "rating": 4.7,
        "distance_km": 0.8,
        "price": 1200.0,
        "busy_slots": ["2026-09-08 15:00"],
        "completed_count": 83,
        "active_jobs_count": 0,
        "phone": "+880 1988-990011",
        "specialty": "Emergency Breakdown, Alternator & Towing",
        "badge": "Fastest Arrival"
    }
]

class MockDB:
    def __init__(self):
        self.reset()

    def reset(self):
        """Re-initializes fresh copy of providers and clear booking storage."""
        self.providers = []
        for p in INITIAL_PROVIDERS:
            cp = dict(p)
            cp["busy_slots"] = list(p["busy_slots"])
            self.providers.append(cp)
        self.bookings = []

    def get_providers(self, category=None):
        if category:
            return [p for p in self.providers if p["category"] == category]
        return list(self.providers)

    def get_provider(self, provider_id):
        return next((p for p in self.providers if p["id"] == provider_id), None)

    def get_bookings(self):
        return list(self.bookings)

    def get_booking(self, booking_id):
        return next((b for b in self.bookings if b["id"] == booking_id), None)

    def is_slot_busy(self, provider_id, slot):
        provider = self.get_provider(provider_id)
        if not provider:
            return True
        return slot in provider.get("busy_slots", [])

    def reserve_slot(self, provider_id, slot):
        provider = self.get_provider(provider_id)
        if provider and slot not in provider.get("busy_slots", []):
            provider["busy_slots"].append(slot)
            provider["active_jobs_count"] = provider.get("active_jobs_count", 0) + 1
            return True
        return False

    def create_booking(self, provider_id, slot, urgency, client_name, client_phone, client_address, notes=""):
        provider = self.get_provider(provider_id)
        if not provider:
            return None, "Provider not found."

        if self.is_slot_busy(provider_id, slot):
            return None, f"Double-booking conflict: {provider['name']} is already booked for {slot}."

        self.reserve_slot(provider_id, slot)

        booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        booking = {
            "id": booking_id,
            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_phone": provider["phone"],
            "category": provider["category"],
            "rating": provider["rating"],
            "price": provider["price"],
            "distance_km": provider["distance_km"],
            "slot": slot,
            "urgency": urgency,
            "client_name": client_name or "Customer",
            "client_phone": client_phone or "+880 1700-000000",
            "client_address": client_address or "Dhaka, Bangladesh",
            "notes": notes or "Service requested.",
            "status": "Requested",
            "history": [
                {
                    "status": "Requested",
                    "timestamp": now_str,
                    "note": "Service booked. Technician reserved in calendar."
                }
            ],
            "created_at": now_str,
            "invoice": None
        }
        self.bookings.insert(0, booking)
        return booking, None

    def update_status(self, booking_id, new_status):
        booking = self.get_booking(booking_id)
        if not booking:
            return None, "Booking not found."

        if new_status not in STATUS_FLOW:
            return None, f"Invalid status: {new_status}."

        curr_idx = STATUS_FLOW.index(booking["status"])
        new_idx = STATUS_FLOW.index(new_status)

        if new_idx != curr_idx + 1:
            return None, f"Illegal transition from '{booking['status']}' to '{new_status}'. Mandatory flow: {' -> '.join(STATUS_FLOW)}"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        booking["status"] = new_status
        booking["history"].append({
            "status": new_status,
            "timestamp": now_str,
            "note": f"Workflow stage advanced to {new_status}."
        })

        if new_status == "Completed":
            provider = self.get_provider(booking["provider_id"])
            if provider:
                provider["completed_count"] = provider.get("completed_count", 0) + 1
                provider["active_jobs_count"] = max(0, provider.get("active_jobs_count", 1) - 1)
            booking["invoice"] = self.generate_invoice(booking)

        return booking, None

    def generate_invoice(self, booking):
        base_price = float(booking.get("price", 500.0))
        is_emergency = str(booking.get("urgency", "")).strip().lower() == "emergency"
        emergency_fee = 250.0 if is_emergency else 0.0
        platform_fee = 50.0
        subtotal = base_price + emergency_fee + platform_fee
        vat = round(subtotal * 0.05, 2)
        grand_total = round(subtotal + vat, 2)

        return {
            "invoice_no": f"INV-{booking['id'][-6:].upper()}",
            "issue_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "booking_id": booking["id"],
            "client_name": booking["client_name"],
            "client_phone": booking["client_phone"],
            "client_address": booking["client_address"],
            "provider_name": booking["provider_name"],
            "category": booking["category"],
            "slot": booking["slot"],
            "urgency": booking["urgency"],
            "base_price": base_price,
            "emergency_fee": emergency_fee,
            "platform_fee": platform_fee,
            "subtotal": subtotal,
            "vat": vat,
            "grand_total": grand_total
        }

    def seed_demo_stages(self):
        """Seeds multi-stage demo bookings across all 5 workflow states for live presentation."""
        demo_stages = [
            ("Completed", "prov-plumb-01", "Plumbing", "2026-09-08 09:00", "Normal", "Prof. Dr. M. Rahman", "+880 1711-001122", "House 12, Road 4, Sector 7, Uttara"),
            ("In Progress", "prov-elec-01", "Electrical", "2026-09-08 10:00", "Emergency", "Tanima Chowdhury", "+880 1822-334455", "Flat 4B, Green Heritage, Dhanmondi"),
            ("On the Way", "prov-app-01", "Appliance & Gadget Repair", "2026-09-08 11:00", "Emergency", "Syed Farhan", "+880 1933-556677", "Block C, Bashundhara R/A"),
            ("Accepted", "prov-car-01", "Car Care & Repair", "2026-09-08 13:00", "Normal", "Nusrat Jahan", "+880 1744-778899", "Gulshan 2, Road 68"),
            ("Requested", "prov-clean-01", "Cleaning & Pest Control", "2026-09-08 15:00", "Normal", "Kazi Shahrier", "+880 1855-990011", "Mirpur DOHS, Avenue 3")
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for status, prov_id, cat, slot, urg, c_name, c_phone, c_addr in demo_stages:
            prov = self.get_provider(prov_id)
            if not prov:
                continue

            if slot not in prov["busy_slots"]:
                prov["busy_slots"].append(slot)

            b_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
            hist = []
            target_idx = STATUS_FLOW.index(status)
            for i in range(target_idx + 1):
                s = STATUS_FLOW[i]
                hist.append({
                    "status": s,
                    "timestamp": now_str,
                    "note": f"Workflow stage: {s}."
                })

            booking = {
                "id": b_id,
                "provider_id": prov["id"],
                "provider_name": prov["name"],
                "provider_phone": prov["phone"],
                "category": cat,
                "rating": prov["rating"],
                "price": prov["price"],
                "distance_km": prov["distance_km"],
                "slot": slot,
                "urgency": urg,
                "client_name": c_name,
                "client_phone": c_phone,
                "client_address": c_addr,
                "notes": "Fast assistance requested.",
                "status": status,
                "history": hist,
                "created_at": now_str,
                "invoice": None
            }
            if status == "Completed":
                booking["invoice"] = self.generate_invoice(booking)
            self.bookings.append(booking)

        return len(self.bookings)

db = MockDB()

