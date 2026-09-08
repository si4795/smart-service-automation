"""
In-memory persistence layer and state manager for service automation.
Handles provider catalog, slot reservation calendars, booking lifecycles, and invoice generation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

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

INITIAL_PROVIDERS: List[Dict[str, Any]] = [
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
        "active_jobs_count": 1,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 1,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 1,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 1,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 1,
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
        "active_jobs_count": 0,
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
        "active_jobs_count": 0,
        "phone": "+880 1907-890123",
        "specialty": "Battery jumpstarts, on-site puncture vulcanizing, towing assistance",
        "badge": "Fastest Arrival"
    }
]

class MockDB:
    def __init__(self) -> None:
        self.providers: List[Dict[str, Any]] = []
        self.bookings: List[Dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        """Restores in-memory state to initial baseline catalog."""
        self.providers = []
        for p in INITIAL_PROVIDERS:
            cp = dict(p)
            cp["busy_slots"] = list(p["busy_slots"])
            self.providers.append(cp)
        self.bookings = []

    def get_providers(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if category:
            canonical = CATEGORY_ALIASES.get(category, category)
            return [
                p for p in self.providers
                if p["category"] == canonical or p["category"] == category
            ]
        return list(self.providers)

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        return next((p for p in self.providers if p["id"] == provider_id), None)

    def get_bookings(self) -> List[Dict[str, Any]]:
        return list(self.bookings)

    def get_booking(self, booking_id: str) -> Optional[Dict[str, Any]]:
        return next((b for b in self.bookings if b["id"] == booking_id), None)

    def is_slot_busy(self, provider_id: str, slot: str) -> bool:
        provider = self.get_provider(provider_id)
        if not provider:
            return True
        return slot in provider.get("busy_slots", [])

    def reserve_slot(self, provider_id: str, slot: str) -> bool:
        provider = self.get_provider(provider_id)
        if provider and slot not in provider.get("busy_slots", []):
            provider["busy_slots"].append(slot)
            provider["active_jobs_count"] = provider.get("active_jobs_count", 0) + 1
            return True
        return False

    def create_booking(
        self,
        provider_id: str,
        slot: str,
        urgency: str,
        client_name: str,
        client_phone: str,
        client_address: str,
        notes: str = ""
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        provider = self.get_provider(provider_id)
        if not provider:
            return None, "Technician record not found."

        if self.is_slot_busy(provider_id, slot):
            return None, f"Scheduling conflict: {provider['name']} is booked for {slot}."

        self.reserve_slot(provider_id, slot)

        booking_id = f"BK-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        booking: Dict[str, Any] = {
            "id": booking_id,
            "provider_id": provider["id"],
            "provider_name": provider["name"],
            "provider_title": provider.get("title", "Technician"),
            "provider_phone": provider["phone"],
            "category": provider["category"],
            "rating": provider["rating"],
            "price": provider["price"],
            "distance_km": provider["distance_km"],
            "slot": slot,
            "urgency": urgency,
            "client_name": client_name or "Client",
            "client_phone": client_phone or "+880 1700-000000",
            "client_address": client_address or "Saidpur, Nilphamari",
            "notes": notes or "Standard service dispatch requested.",
            "status": "Requested",
            "history": [
                {
                    "status": "Requested",
                    "timestamp": now_str,
                    "note": "Appointment confirmed. Technician reserved on calendar."
                }
            ],
            "created_at": now_str,
            "invoice": None
        }
        self.bookings.insert(0, booking)
        return booking, None

    def update_status(self, booking_id: str, new_status: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
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
        booking["status"] = new_status
        booking["history"].append({
            "status": new_status,
            "timestamp": now_str,
            "note": f"Service milestone transitioned to {new_status}."
        })

        if new_status == "Completed":
            provider = self.get_provider(booking["provider_id"])
            if provider:
                provider["completed_count"] = provider.get("completed_count", 0) + 1
                provider["active_jobs_count"] = max(0, provider.get("active_jobs_count", 1) - 1)
            booking["invoice"] = self.generate_invoice(booking)

        return booking, None

    def generate_invoice(self, booking: Dict[str, Any]) -> Dict[str, Any]:
        base_price = float(booking.get("price", 500.0))
        is_emergency = str(booking.get("urgency", "")).strip().lower() == "emergency"
        emergency_fee = 250.0 if is_emergency else 0.0
        platform_fee = 50.0
        subtotal = base_price + emergency_fee + platform_fee
        vat = round(subtotal * 0.05, 2)
        grand_total = round(subtotal + vat, 2)

        return {
            "invoice_no": f"INV-{booking['id'][-6:].upper()}",
            "issue_date": datetime.now().strftime("%d %b %Y, %H:%M"),
            "booking_id": booking["id"],
            "client_name": booking["client_name"],
            "client_phone": booking["client_phone"],
            "client_address": booking["client_address"],
            "provider_name": booking["provider_name"],
            "provider_title": booking.get("provider_title", "Technician"),
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

    def seed_demo_stages(self) -> int:
        """Populates realistic bookings across the 5 lifecycle states."""
        demo_profiles = [
            ("Completed", "prov-plumb-01", "Plumbing & Pipefitting", "2026-09-08 09:00", "Normal", "Prof. Dr. M. A. Rahman", "+880 1711-234567", "Faculty Quarter 4B, BAUST Campus"),
            ("In Progress", "prov-elec-01", "Electrical Engineering", "2026-09-08 10:00", "Emergency", "Tahmina Akter", "+880 1819-345678", "Officers Colony Road 3, Saidpur Cantonment"),
            ("On the Way", "prov-app-01", "HVAC & Appliance Care", "2026-09-08 11:00", "Emergency", "Syed Nazrul Islam", "+880 1912-456789", "Railway Officers Rest House, Station Rd"),
            ("Accepted", "prov-car-01", "Vehicle Maintenance", "2026-09-08 13:00", "Normal", "Nusrat Jahan", "+880 1723-567890", "Green Garden Housing, Airport Bypass"),
            ("Requested", "prov-clean-01", "Pest Control & Hygiene", "2026-09-08 15:00", "Normal", "Kazi Shahriar", "+880 1834-678901", "Shahid Smrity Bhaban, Central Area")
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        for status, prov_id, cat, slot, urg, c_name, c_phone, c_addr in demo_profiles:
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
                    "note": f"Milestone advanced to {s}."
                })

            booking: Dict[str, Any] = {
                "id": b_id,
                "provider_id": prov["id"],
                "provider_name": prov["name"],
                "provider_title": prov.get("title", "Technician"),
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
                "notes": "Urgent technical inspection requested.",
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
