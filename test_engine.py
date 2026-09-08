"""
Automated unit and integration test suite for service matching, scheduling, and workflow state machine.
"""
import unittest
from app import app
from services.mock_db import db, CATEGORIES, STATUS_FLOW
from services.matcher import calculate_match_score, rank_providers, auto_assign_emergency

class TestSmartServiceAutomation(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.app = app.test_client()
        db.reset()

    def test_score_calculation_normal(self):
        """Validates base formula: Score = (Rating * 25) - (Distance * 6) - (Price * 0.015)"""
        provider = {
            "id": "test-1",
            "rating": 4.8,
            "distance_km": 2.0,
            "price": 600.0
        }
        total, base, boost = calculate_match_score(provider, urgency="Normal")
        self.assertEqual(base, 99.0)
        self.assertEqual(boost, 0.0)
        self.assertEqual(total, 99.0)

    def test_score_calculation_emergency_boost(self):
        """Validates emergency weighting: Urgency Boost = (10 - Distance) * 20"""
        provider = {
            "id": "test-1",
            "rating": 4.8,
            "distance_km": 2.0,
            "price": 600.0
        }
        total, base, boost = calculate_match_score(provider, urgency="Emergency")
        self.assertEqual(base, 99.0)
        self.assertEqual(boost, 160.0)
        self.assertEqual(total, 259.0)

    def test_double_booking_prevention(self):
        """Ensures technicians with conflicting calendar reservations are excluded."""
        target_slot = "2026-09-08 10:00"
        providers = db.get_providers(category="HVAC & Appliance Care")
        available, busy = rank_providers(providers, category="HVAC & Appliance Care", requested_slot=target_slot)
        
        available_ids = [c["id"] for c in available]
        busy_ids = [b["id"] for b in busy]

        self.assertNotIn("prov-app-01", available_ids)
        self.assertIn("prov-app-01", busy_ids)

    def test_workload_balancing_tiebreaker(self):
        """Verifies technician with lower active load receives precedence when scores tie."""
        p1 = {
            "id": "p1", "name": "Tech 1", "category": "Plumbing & Pipefitting", "rating": 5.0,
            "distance_km": 1.0, "price": 500.0, "active_jobs_count": 3, "busy_slots": []
        }
        p2 = {
            "id": "p2", "name": "Tech 2", "category": "Plumbing & Pipefitting", "rating": 5.0,
            "distance_km": 1.0, "price": 500.0, "active_jobs_count": 0, "busy_slots": []
        }
        ranked, _ = rank_providers([p1, p2], category="Plumbing & Pipefitting", requested_slot="2026-09-08 11:00")
        self.assertEqual(ranked[0]["id"], "p2")

    def test_one_click_emergency_auto_assignment(self):
        """Verifies automated dispatch selects the optimal available technician."""
        cat_providers = db.get_providers("Plumbing & Pipefitting")
        best = auto_assign_emergency(cat_providers, "Plumbing & Pipefitting", "2026-09-08 14:00")
        self.assertIsNotNone(best)
        assert best is not None
        self.assertIn("score", best)

    def test_state_machine_and_invoicing(self):
        """Verifies strict progression: Requested -> Accepted -> On the Way -> In Progress -> Completed."""
        resp = self.app.post("/book", data={
            "provider_id": "prov-plumb-01",
            "slot": "2026-09-08 19:00",
            "urgency": "Emergency",
            "client_name": "Audit Verification Client",
            "client_phone": "+880 1711-223344",
            "client_address": "Saidpur Cantonment Area"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(resp.status_code, 200)
        json_data = resp.get_json()
        assert json_data is not None
        b_id = json_data["booking"]["id"]

        # Disallow illegal progression skipping
        bad_resp = self.app.post(f"/update-status/{b_id}/In%20Progress", headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(bad_resp.status_code, 400)

        # Sequential step execution
        for next_step in ["Accepted", "On the Way", "In Progress", "Completed"]:
            r = self.app.post(f"/update-status/{b_id}/{next_step}", headers={"X-Requested-With": "XMLHttpRequest"})
            self.assertEqual(r.status_code, 200)
            step_data = r.get_json()
            assert step_data is not None
            self.assertEqual(step_data["booking"]["status"], next_step)

        # Confirm digital invoice generated upon completion
        completed_data = r.get_json()
        assert completed_data is not None
        completed_booking = completed_data["booking"]
        inv = completed_booking["invoice"]
        self.assertIsNotNone(inv)
        assert inv is not None
        self.assertGreater(inv["emergency_fee"], 0)
        self.assertGreater(inv["grand_total"], inv["base_price"])

    def test_user_authentication_success(self):
        """Validates 1-click and standard credential logins for Customer & Technician personas."""
        # 1-Click Customer
        resp_cust = self.app.post("/login", data={"demo_role": "customer"})
        self.assertEqual(resp_cust.status_code, 302)

        # 1-Click Technician
        resp_tech = self.app.post("/login", data={"demo_role": "technician"})
        self.assertEqual(resp_tech.status_code, 302)

        # Direct Credential Check
        cust_user = db.authenticate_user("customer@smartserve.local", "pass123")
        self.assertIsNotNone(cust_user)
        assert cust_user is not None
        self.assertEqual(cust_user["role"], "customer")

        tech_user = db.authenticate_user("tech@smartserve.local", "pass123")
        self.assertIsNotNone(tech_user)
        assert tech_user is not None
        self.assertEqual(tech_user["role"], "technician")

    def test_user_authentication_invalid(self):
        """Ensures invalid credentials are rejected with proper status."""
        resp = self.app.post("/login", data={
            "email": "wrong@example.com",
            "password": "badpassword"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(resp.status_code, 401)

    def test_technician_route_guard_unauthorized(self):
        """Verifies unauthenticated users and customers cannot access /provider."""
        # Unauthenticated request redirects to /login
        unauth_resp = self.app.get("/provider")
        self.assertEqual(unauth_resp.status_code, 302)
        self.assertIn("/login", unauth_resp.location)

        # Logged in as Customer attempting to access /provider
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        cust_resp = self.app.get("/provider")
        self.assertEqual(cust_resp.status_code, 302)
        self.assertIn("/login", cust_resp.location)

    def test_technician_route_guard_authorized(self):
        """Verifies technician role grants access to /provider operations board."""
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-tech-01"
            sess["user_role"] = "technician"

        tech_resp = self.app.get("/provider")
        self.assertEqual(tech_resp.status_code, 200)

    def test_user_registration(self):
        """Verifies new customer registration creates session and persists user."""
        resp = self.app.post("/signup", data={
            "name": "Mahmudur Rahman",
            "email": "mahmud@example.com",
            "password": "securepass123",
            "role": "customer",
            "phone": "+880 1711-998877",
            "address": "Saidpur Cantonment"
        })
        self.assertEqual(resp.status_code, 302)
        created = db.get_user_by_email("mahmud@example.com")
        self.assertIsNotNone(created)
        assert created is not None
        self.assertEqual(created["name"], "Mahmudur Rahman")

    def test_sqlite_persistence_file_and_schema(self):
        """Verifies smartserve.db file exists on disk and standard 4 tables are present."""
        import os
        from database import DB_PATH
        self.assertTrue(os.path.exists(DB_PATH))
        self.assertGreater(os.path.getsize(DB_PATH), 0)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r["name"] for r in cursor.fetchall()]
            for expected_tbl in ["users", "technicians", "bookings", "invoices"]:
                self.assertIn(expected_tbl, tables)

    def test_sqlite_relational_invoices_table(self):
        """Verifies completion of booking inserts an official record in invoices table."""
        booking, err = db.create_booking(
            provider_id="prov-elec-01",
            slot="2026-09-08 18:00",
            urgency="Emergency",
            client_name="SQLite Tester",
            client_phone="+880 1700-112233",
            client_address="Saidpur Cantonment"
        )
        self.assertIsNone(err)
        assert booking is not None
        b_id = booking["id"]

        # Advance through all stages
        for s in ["Accepted", "On the Way", "In Progress", "Completed"]:
            db.update_status(b_id, s)

        # Directly query invoices table in SQLite
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM invoices WHERE booking_id = ?", (b_id,))
            inv_row = cursor.fetchone()
            self.assertIsNotNone(inv_row)
            assert inv_row is not None
            self.assertEqual(inv_row["booking_id"], b_id)
            self.assertGreater(inv_row["total_amount"], 0)

    def test_consumer_landing_page_and_redirects(self):
        """Verifies GET / serves landing page for anonymous users and redirects logged in users."""
        # Unauthenticated: gets landing page
        resp = self.app.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Home repairs and maintenance", html)
        self.assertIn("Explore as Customer", html)

        # Authenticated Customer: redirects to /dashboard
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        resp_cust = self.app.get("/")
        self.assertEqual(resp_cust.status_code, 302)
        self.assertIn("/dashboard", resp_cust.location)

    def test_guarded_dashboard_access(self):
        """Verifies GET /dashboard is session-guarded by login_required."""
        # Unauthenticated: redirects to login
        unauth = self.app.get("/dashboard")
        self.assertEqual(unauth.status_code, 302)
        self.assertIn("/login", unauth.location)

        # Authenticated Customer: loads multi-panel dashboard
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        auth_resp = self.app.get("/dashboard")
        self.assertEqual(auth_resp.status_code, 200)
        html = auth_resp.get_data(as_text=True)
        self.assertIn("Available Specialists", html)
        self.assertIn("Filter & Schedule", html)

    def test_technician_portfolio_media_columns(self):
        """Verifies SQLite technicians table contains portfolio photos, video, avatar, and completed_tasks."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(technicians)")
            cols = {r["name"] for r in cursor.fetchall()}
            for expected_col in ["completed_tasks", "avatar_url", "portfolio_photos", "portfolio_video", "bio", "certifications"]:
                self.assertIn(expected_col, cols)

        # Ensure providers fetched have populated portfolio attributes
        prov = db.get_providers()[0]
        self.assertIn("portfolio_photos", prov)
        self.assertIsInstance(prov["portfolio_photos"], list)
        self.assertIn("portfolio_video", prov)
        self.assertTrue(prov["portfolio_video"].startswith("http"))
        self.assertIn("completed_tasks", prov)

if __name__ == "__main__":
    unittest.main()

