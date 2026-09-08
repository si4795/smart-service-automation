"""
Smart Home Service Automation - Comprehensive Test Suite
BAUST CSE FEST 2026 Competitive Hackathon
"""
import unittest
from app import app
from services.mock_db import db, CATEGORIES, STATUS_FLOW
from services.matcher import calculate_match_score, rank_providers, auto_assign_emergency

class TestSmartServiceAutomation(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        db.reset()

    def test_score_calculation_normal(self):
        """Score = (Rating * 25) - (Distance * 6) - (Price * 0.015)"""
        provider = {
            "id": "test-1",
            "rating": 4.8,
            "distance_km": 2.0,
            "price": 600.0
        }
        # Expected: (4.8 * 25) - (2.0 * 6) - (600 * 0.015) = 120 - 12 - 9 = 99.0
        total, base, boost = calculate_match_score(provider, urgency="Normal")
        self.assertEqual(base, 99.0)
        self.assertEqual(boost, 0.0)
        self.assertEqual(total, 99.0)

    def test_score_calculation_emergency_boost(self):
        """Emergency Boost = (10 - Distance) * 20"""
        provider = {
            "id": "test-1",
            "rating": 4.8,
            "distance_km": 2.0,
            "price": 600.0
        }
        # Expected boost: (10 - 2.0) * 20 = 160.0
        # Total: 99.0 + 160.0 = 259.0
        total, base, boost = calculate_match_score(provider, urgency="Emergency")
        self.assertEqual(base, 99.0)
        self.assertEqual(boost, 160.0)
        self.assertEqual(total, 259.0)

    def test_double_booking_prevention(self):
        """Verify busy technician in requested slot is strictly excluded."""
        target_slot = "2026-09-08 10:00"
        providers = db.get_providers(category="Appliance & Gadget Repair")
        # prov-app-01 has 2026-09-08 10:00 in busy_slots
        available, busy = rank_providers(providers, category="Appliance & Gadget Repair", requested_slot=target_slot)
        
        available_ids = [c["id"] for c in available]
        busy_ids = [b["id"] for b in busy]

        self.assertNotIn("prov-app-01", available_ids)
        self.assertIn("prov-app-01", busy_ids)

    def test_workload_balancing_tiebreaker(self):
        """Technician with lower active jobs gets priority if score is tied."""
        p1 = {
            "id": "p1", "name": "Tech 1", "category": "Plumbing", "rating": 5.0,
            "distance_km": 1.0, "price": 500.0, "active_jobs_count": 3, "busy_slots": []
        }
        p2 = {
            "id": "p2", "name": "Tech 2", "category": "Plumbing", "rating": 5.0,
            "distance_km": 1.0, "price": 500.0, "active_jobs_count": 0, "busy_slots": []
        }
        ranked, _ = rank_providers([p1, p2], category="Plumbing", requested_slot="2026-09-08 11:00")
        # Both have same score, p2 has 0 active jobs vs p1 has 3 active jobs -> p2 should be first
        self.assertEqual(ranked[0]["id"], "p2")

    def test_one_click_emergency_auto_assignment(self):
        """Verify auto-assignment selects the top emergency candidate."""
        cat_providers = db.get_providers("Plumbing")
        best = auto_assign_emergency(cat_providers, "Plumbing", "2026-09-08 14:00")
        self.assertIsNotNone(best)
        self.assertIn("score", best)

    def test_state_machine_and_invoicing(self):
        """Verify strict sequential transition [Requested] -> [Accepted] -> [On the Way] -> [In Progress] -> [Completed]."""
        # Book a service
        resp = self.app.post("/book", data={
            "provider_id": "prov-plumb-01",
            "slot": "2026-09-08 19:00",
            "urgency": "Emergency",
            "client_name": "Hackathon Judge",
            "client_phone": "+880 1711-223344",
            "client_address": "BAUST Campus, Saidpur"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(resp.status_code, 200)
        b_id = resp.get_json()["booking"]["id"]

        # Attempt invalid jump: Requested -> In Progress (must fail 400)
        bad_resp = self.app.post(f"/update-status/{b_id}/In%20Progress", headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(bad_resp.status_code, 400)

        # Advance step by step
        for next_step in ["Accepted", "On the Way", "In Progress", "Completed"]:
            r = self.app.post(f"/update-status/{b_id}/{next_step}", headers={"X-Requested-With": "XMLHttpRequest"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["booking"]["status"], next_step)

        # Inspect invoice
        completed_booking = r.get_json()["booking"]
        inv = completed_booking["invoice"]
        self.assertIsNotNone(inv)
        self.assertGreater(inv["emergency_fee"], 0) # Emergency fee added
        self.assertGreater(inv["grand_total"], inv["base_price"])

if __name__ == "__main__":
    unittest.main()
