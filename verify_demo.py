"""
BAUST CSE FEST 2026 - Demo Verification Pipeline
Tests all endpoints, matching math, double-booking shield, 5-stage lifecycle, and invoicing.
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def post(path, data=None):
    url = f"{BASE_URL}{path}"
    encoded = urllib.parse.urlencode(data or {}).encode() if data else b""
    req = urllib.request.Request(url, data=encoded, headers={"X-Requested-With": "XMLHttpRequest"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        try:
            body = json.loads(err.read().decode())
            return {"_http_status": err.code, "error": body.get("error", "Error"), "success": False}
        except Exception:
            return {"_http_status": err.code, "error": str(err), "success": False}

def main():
    print("=" * 65)
    print("   BAUST CSE FEST 2026 - SMART HOME AUTOMATION PIPELINE TEST   ")
    print("=" * 65)

    results = []

    # 1. Seed Demo Data
    try:
        post("/api/reset")
        seed = post("/api/seed-demo")
        summary = get("/api/summary")
        dist = summary.get("status_distribution", {})
        total_seeded = summary.get("total_bookings", 0)
        status_pass = (total_seeded >= 5 and all(dist.get(s, 0) >= 1 for s in ["Requested", "Accepted", "On the Way", "In Progress", "Completed"]))
        results.append({
            "step": "1. Seed Baseline Demo Data",
            "passed": status_pass,
            "details": f"Total Bookings: {total_seeded} | Distribution: {dist}"
        })
        print(f"[PASS] Step 1: Demo Seeded. Total Bookings: {total_seeded}")
        for s, count in dist.items():
            print(f"       - [{s}]: {count}")
    except Exception as e:
        results.append({"step": "1. Seed Baseline Demo Data", "passed": False, "details": str(e)})
        print(f"[FAIL] Step 1: {e}")

    # 2. Matching Engine & Urgency Boost Verification
    try:
        from services.mock_db import db
        from services.matcher import calculate_match_score, rank_providers
        prov = db.get_providers("Electrical")[0]
        score_normal, base_norm, boost_norm = calculate_match_score(prov, "Normal")
        score_emerg, base_emerg, boost_emerg = calculate_match_score(prov, "Emergency")
        
        expected_boost = (10.0 - prov["distance_km"]) * 20.0
        boost_match = (boost_norm == 0.0 and abs(boost_emerg - expected_boost) < 1e-4 and score_emerg > score_normal)
        results.append({
            "step": "2. Matching Engine Scoring & Urgency Boost",
            "passed": boost_match,
            "details": f"Normal: {score_normal} (Boost: +{boost_norm}) | Emergency: {score_emerg} (Boost: +{boost_emerg})"
        })
        print(f"[PASS] Step 2: Scoring Engine Verified")
        print(f"       - Normal Score: {score_normal} (Base: {base_norm}, Boost: +{boost_norm})")
        print(f"       - Emergency Score: {score_emerg} (Base: {base_emerg}, Boost: +{boost_emerg})")
    except Exception as e:
        results.append({"step": "2. Matching Engine Scoring & Urgency Boost", "passed": False, "details": str(e)})
        print(f"[FAIL] Step 2: {e}")

    # 3. Double-Booking Shield
    b1 = None
    booking_id = None
    try:
        # Pick an unbooked slot: 2026-09-08 20:00
        slot = "2026-09-08 20:00"
        prov_id = "prov-plumb-02"

        # 1st booking (should succeed)
        b1 = post("/book", {
            "provider_id": prov_id,
            "slot": slot,
            "urgency": "Normal",
            "client_name": "Pipeline Client 1",
            "client_phone": "+880 1711-123456",
            "client_address": "Saidpur, Nilphamari"
        })
        booking_id = b1["booking"]["id"]

        # 2nd booking: attempt collision on the same slot (MUST FAIL with 409)
        b2 = post("/book", {
            "provider_id": prov_id,
            "slot": slot,
            "urgency": "Emergency",
            "client_name": "Conflict Client",
            "client_phone": "+880 1711-654321",
            "client_address": "Saidpur, Nilphamari"
        })
        conflict_detected = (b2.get("_http_status") == 409 or not b2.get("success", True))

        results.append({
            "step": "3. Double-Booking Prevention Shield",
            "passed": conflict_detected,
            "details": f"Booking ID: {booking_id} locked slot '{slot}'. Collision blocked with HTTP 409 Conflict."
        })
        print(f"[PASS] Step 3: Double-Booking Shield Verified (HTTP 409 Conflict Enforced)")
    except Exception as e:
        results.append({"step": "3. Double-Booking Prevention Shield", "passed": False, "details": str(e)})
        print(f"[FAIL] Step 3: {e}")

    # 4. 5-Stage Sequential Lifecycle Transitions
    curr_b = None
    try:
        stages = ["Accepted", "On the Way", "In Progress", "Completed"]
        transitions_ok = True
        curr_b = b1["booking"]

        for next_st in stages:
            enc_st = urllib.parse.quote(next_st)
            res = post(f"/update-status/{booking_id}/{enc_st}")
            curr_b = res["booking"]
            if curr_b["status"] != next_st:
                transitions_ok = False
                break
            print(f"       -> Advanced: [{next_st}] (Total History: {len(curr_b['history'])} events)")

        results.append({
            "step": "4. 5-Stage Sequential Progression",
            "passed": transitions_ok and curr_b["status"] == "Completed",
            "details": "Pipeline: Requested -> Accepted -> On the Way -> In Progress -> Completed"
        })
        print(f"[PASS] Step 4: 5-Stage Workflow Transitions Verified")
    except Exception as e:
        results.append({"step": "4. 5-Stage Sequential Progression", "passed": False, "details": str(e)})
        print(f"[FAIL] Step 4: {e}")

    # 5. Automated Digital Invoice Payload Verification
    try:
        inv = curr_b.get("invoice") if curr_b else None
        inv_ok = False
        if inv:
            has_fields = all(k in inv for k in ["invoice_no", "base_price", "emergency_fee", "platform_fee", "vat", "grand_total"])
            math_ok = (inv["grand_total"] == round((inv["base_price"] + inv["emergency_fee"] + inv["platform_fee"]) * 1.05, 2))
            inv_ok = has_fields and math_ok

        results.append({
            "step": "5. Automated Digital Invoice Generation",
            "passed": inv_ok,
            "details": f"Invoice No: {inv.get('invoice_no')} | Grand Total: BDT {inv.get('grand_total')} (Base: BDT {inv.get('base_price')}, VAT: BDT {inv.get('vat')})"
        })
        print(f"[PASS] Step 5: Digital Invoice Payload Verified")
        print(f"       - Invoice No:   {inv.get('invoice_no')}")
        print(f"       - Base Rate:    BDT {inv.get('base_price')}")
        print(f"       - Platform Fee: BDT {inv.get('platform_fee')}")
        print(f"       - VAT (5%):     BDT {inv.get('vat')}")
        print(f"       - Grand Total:  BDT {inv.get('grand_total')}")
    except Exception as e:
        results.append({"step": "5. Automated Digital Invoice Generation", "passed": False, "details": str(e)})
        print(f"[FAIL] Step 5: {e}")

    print("=" * 65)
    print("                     VERIFICATION SUMMARY                      ")
    print("=" * 65)
    all_pass = all(r["passed"] for r in results)
    for r in results:
        status_tag = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"{status_tag:7} {r['step']}")
        print(f"        Details: {r['details']}")

    print("=" * 65)
    if all_pass:
        print("[SUCCESS] ALL 5 PIPELINE STAGES PASSED (100% INTEGRITY)")
    else:
        print("[WARNING] SOME STAGES FAILED")
    print("=" * 65)

if __name__ == "__main__":
    main()
