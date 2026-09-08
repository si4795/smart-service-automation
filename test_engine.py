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
        self.assertIn("Sign In to Portal", html)
        self.assertIn("Create Account", html)

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

    def test_sequential_user_journey_routes(self):
        """Verifies multi-page sequential flow: /services/<cat> -> /checkout/<id> -> /orders/<code>."""
        # Verify route guard redirects unauthenticated users
        unauth_resp = self.app.get("/services/electrical")
        self.assertEqual(unauth_resp.status_code, 302)
        self.assertIn("/login", unauth_resp.location)

        # Authenticate as Customer
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        # 1. Specialists Catalog
        resp_cat = self.app.get("/services/electrical?date=2026-09-08&time=14:00")
        self.assertEqual(resp_cat.status_code, 200)
        html_cat = resp_cat.get_data(as_text=True)
        self.assertIn("Available Specialists", html_cat)
        self.assertIn("Electrical Engineering", html_cat)

        # 2. Dedicated Checkout Page
        resp_checkout = self.app.get("/checkout/prov-elec-01?date=2026-09-08&time=14:00&urgency=Normal")
        self.assertEqual(resp_checkout.status_code, 200)
        html_checkout = resp_checkout.get_data(as_text=True)
        self.assertIn("Order Summary", html_checkout)
        self.assertIn("Total Payable", html_checkout)

        # 3. Post Checkout & Scheduling
        resp_post = self.app.post("/checkout", data={
            "provider_id": "prov-elec-01",
            "slot_date": "2026-09-08",
            "slot_time": "14:00",
            "urgency": "Normal",
            "client_name": "Sequential Flow Tester",
            "client_phone": "+880 1711-556677",
            "client_address": "Quarter 4, Cantonment Housing",
            "notes": "Testing sequential flow booking"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(resp_post.status_code, 200)
        booking_data = resp_post.get_json()
        self.assertIsNotNone(booking_data)
        assert booking_data is not None
        b_code = booking_data["booking"]["id"]

        # 4. Dedicated Order Tracking Page
        resp_order = self.app.get(f"/orders/{b_code}")
        self.assertEqual(resp_order.status_code, 200)
        html_order = resp_order.get_data(as_text=True)
        self.assertIn("Order #", html_order)
        self.assertIn("Request Submitted", html_order)
        self.assertIn("Sequential Flow Tester", html_order)

        # 5. Collision Shield enforcement on same slot
        resp_collision = self.app.post("/checkout", data={
            "provider_id": "prov-elec-01",
            "slot_date": "2026-09-08",
            "slot_time": "14:00",
            "urgency": "Normal",
            "client_name": "Conflict Client",
            "client_phone": "+880 1799-000000",
            "client_address": "Cantonment Area"
        }, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(resp_collision.status_code, 409)

    def test_user_profile_management(self):
        """Verifies GET/POST /profile authentication, field updates, and SQLite persistence."""
        # Unauthenticated redirect
        unauth = self.app.get("/profile")
        self.assertEqual(unauth.status_code, 302)
        self.assertIn("/login", unauth.location)

        # Authenticate as customer
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        # GET Profile
        resp = self.app.get("/profile")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Personal & Contact Details", html)
        self.assertIn("customer@smartserve.local", html)

        # POST Profile update
        post_resp = self.app.post("/profile", data={
            "action": "update_profile",
            "name": "Suaib Pro Islam",
            "phone": "+880 1711-998877",
            "address": "Cantonment Officers Quarter #10"
        }, follow_redirects=True)
        self.assertEqual(post_resp.status_code, 200)
        self.assertIn("Changes Saved", post_resp.get_data(as_text=True))

        # Direct database verification
        updated = db.get_user_by_id("usr-cust-01")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["name"], "Suaib Pro Islam")
        self.assertEqual(updated["phone"], "+880 1711-998877")
        self.assertEqual(updated["address"], "Cantonment Officers Quarter #10")
        self.assertEqual(updated["avatar"], "SP")

    def test_in_app_dispatch_chat(self):
        """Verifies customer and technician messaging, database persistence, and API endpoints."""
        booking, err = db.create_booking(
            provider_id="prov-elec-01",
            slot="2026-09-08 17:00",
            urgency="Normal",
            client_name="Chat Test Client",
            client_phone="+880 1700-554433",
            client_address="Saidpur Cantonment Gate 2"
        )
        self.assertIsNone(err)
        assert booking is not None
        b_code = booking["id"]

        # 1. Customer sends message
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        cust_resp = self.app.post(
            f"/orders/{b_code}/messages",
            json={"message": "Please use the west gate entrance."},
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(cust_resp.status_code, 200)
        cust_data = cust_resp.get_json()
        self.assertIsNotNone(cust_data)
        assert cust_data is not None
        self.assertTrue(cust_data["success"])
        self.assertEqual(cust_data["message"]["sender_role"], "customer")
        self.assertEqual(cust_data["message"]["message"], "Please use the west gate entrance.")

        # 2. Technician sends reply
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-tech-01"
            sess["user_role"] = "technician"

        tech_resp = self.app.post(
            f"/orders/{b_code}/messages",
            json={"message": "Acknowledged. Approaching west gate now."},
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(tech_resp.status_code, 200)
        tech_data = tech_resp.get_json()
        self.assertIsNotNone(tech_data)
        assert tech_data is not None
        self.assertEqual(tech_data["message"]["sender_role"], "technician")

        # 3. Fetch messages via GET
        get_resp = self.app.get(f"/orders/{b_code}/messages")
        self.assertEqual(get_resp.status_code, 200)
        thread = get_resp.get_json()
        self.assertIsNotNone(thread)
        assert thread is not None
        self.assertEqual(len(thread["messages"]), 2)
        self.assertEqual(thread["messages"][0]["message"], "Please use the west gate entrance.")
        self.assertEqual(thread["messages"][1]["message"], "Acknowledged. Approaching west gate now.")

        # 4. Direct SQLite verification
        db_messages = db.get_messages(b_code)
        self.assertEqual(len(db_messages), 2)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM messages WHERE booking_code = ?", (b_code,))
            row = cursor.fetchone()
            self.assertEqual(row["cnt"], 2)

    def test_password_rotation_security(self):
        """Verifies old password validation, minimum length check, and secure credential rotation."""
        with self.app.session_transaction() as sess:
            sess["user_id"] = "usr-cust-01"
            sess["user_role"] = "customer"

        # 1. Reject invalid old password
        bad_old = self.app.post("/profile", data={
            "action": "update_password",
            "old_password": "completely_wrong_pass",
            "new_password": "brandnewpassword123",
            "confirm_password": "brandnewpassword123"
        }, follow_redirects=True)
        self.assertEqual(bad_old.status_code, 200)
        self.assertIn("Current password does not match.", bad_old.get_data(as_text=True))
        # Ensure password unchanged
        self.assertIsNotNone(db.authenticate_user("customer@smartserve.local", "pass123"))

        # 2. Reject short new password (< 6 chars)
        short_pw = self.app.post("/profile", data={
            "action": "update_password",
            "old_password": "pass123",
            "new_password": "123",
            "confirm_password": "123"
        }, follow_redirects=True)
        self.assertEqual(short_pw.status_code, 200)
        self.assertIn("at least 6 characters", short_pw.get_data(as_text=True))

        # 3. Reject mismatched confirm password
        mismatch_pw = self.app.post("/profile", data={
            "action": "update_password",
            "old_password": "pass123",
            "new_password": "validnewpass123",
            "confirm_password": "differentpass123"
        }, follow_redirects=True)
        self.assertEqual(mismatch_pw.status_code, 200)
        self.assertIn("New passwords do not match.", mismatch_pw.get_data(as_text=True))

        # 4. Successful rotation with correct old password
        good_update = self.app.post("/profile", data={
            "action": "update_password",
            "old_password": "pass123",
            "new_password": "brandnewpassword123",
            "confirm_password": "brandnewpassword123"
        }, follow_redirects=True)
        self.assertEqual(good_update.status_code, 200)
        self.assertIn("Security credentials updated successfully.", good_update.get_data(as_text=True))

        # Verify authentication state
        self.assertIsNotNone(db.authenticate_user("customer@smartserve.local", "brandnewpassword123"))
        self.assertIsNone(db.authenticate_user("customer@smartserve.local", "pass123"))

        # Revert back to pass123 for other tests
        db.update_user_profile(
            user_id="usr-cust-01",
            password="pass123",
            old_password="brandnewpassword123"
        )

    def test_sqlite_messages_table_schema(self):
        """Verifies messages table exists in smartserve.db with expected column schema."""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(messages)")
            cols = {r["name"] for r in cursor.fetchall()}
            for col in ["id", "booking_code", "sender_id", "sender_role", "sender_name", "message", "created_at"]:
                self.assertIn(col, cols)

if __name__ == "__main__":
    unittest.main()


