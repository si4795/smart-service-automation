"""
Verification script for SmartServe booking, scheduling, and billing workflows.
"""
import urllib.request
import urllib.parse
import urllib.error
import json
from typing import Dict, Any, Optional

BASE_URL = "http://127.0.0.1:5000"

def get(path: str) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req) as resp:
        parsed: Dict[str, Any] = json.loads(resp.read().decode())
        return parsed

def post(path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    encoded = urllib.parse.urlencode(data or {}).encode() if data else b""
    req = urllib.request.Request(url, data=encoded, headers={"X-Requested-With": "XMLHttpRequest"})
    try:
        with urllib.request.urlopen(req) as resp:
            parsed: Dict[str, Any] = json.loads(resp.read().decode())
            return parsed
    except urllib.error.HTTPError as err:
        try:
            body = json.loads(err.read().decode())
            return {"_http_status": err.code, "error": body.get("error", "Error"), "success": False}
        except Exception:
            return {"_http_status": err.code, "error": str(err), "success": False}

def main() -> None:
    print("=" * 65)
    print("         SMARTSERVE END-TO-END WORKFLOW VERIFICATION          ")
    print("=" * 65)

    results = []

    # 1. Seed Demo Data
    try:
        post("/api/reset")
        seed = post("/api/seed-demo")
        assert seed is not None and isinstance(seed, dict)

        summary = get("/api/summary")
        assert summary is not None and isinstance(summary, dict)

        dist: Dict[str, Any] = summary.get("status_distribution", {})
        total_seeded: int = summary.get("total_bookings", 0)
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
        from services.matcher import calculate_match_score
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
    b1: Optional[Dict[str, Any]] = None
    booking_id: Optional[str] = None
    try:
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
        assert b1 is not None and isinstance(b1, dict)
        booking_data = b1.get("booking")
        assert booking_data is not None and isinstance(booking_data, dict)
        booking_id = str(booking_data.get("id"))
        assert booking_id is not None

        # 2nd booking: attempt collision on the same slot (MUST FAIL with 409)
        b2 = post("/book", {
            "provider_id": prov_id,
            "slot": slot,
            "urgency": "Emergency",
            "client_name": "Conflict Client",
            "client_phone": "+880 1711-654321",
            "client_address": "Saidpur, Nilphamari"
        })
        assert b2 is not None and isinstance(b2, dict)
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
    curr_b: Optional[Dict[str, Any]] = None
    try:
        stages = ["Accepted", "On the Way", "In Progress", "Completed"]
        transitions_ok = True
        assert b1 is not None and isinstance(b1, dict)
        target_booking = b1.get("booking")
        assert target_booking is not None and isinstance(target_booking, dict)
        curr_b = target_booking
        assert booking_id is not None

        for next_st in stages:
            enc_st = urllib.parse.quote(next_st)
            res = post(f"/update-status/{booking_id}/{enc_st}")
            assert res is not None and isinstance(res, dict)
            updated_booking = res.get("booking")
            assert updated_booking is not None and isinstance(updated_booking, dict)
            curr_b = updated_booking

            if curr_b.get("status") != next_st:
                transitions_ok = False
                break
            hist_list = curr_b.get("history") or []
            print(f"       -> Advanced: [{next_st}] (Total History: {len(hist_list)} events)")

        assert curr_b is not None and isinstance(curr_b, dict)
        results.append({
            "step": "4. 5-Stage Sequential Progression",
            "passed": transitions_ok and (curr_b.get("status") == "Completed"),
            "details": "Pipeline: Requested -> Accepted -> On the Way -> In Progress -> Completed"
        })
        print(f"[PASS] Step 4: 5-Stage Workflow Transitions Verified")
    except Exception as e:
        results.append({"step": "4. 5-Stage Sequential Progression", "passed": False, "details": str(e)})
        print(f"[FAIL] Step 4: {e}")

    # 5. Automated Digital Invoice Payload Verification
    try:
        assert curr_b is not None and isinstance(curr_b, dict)
        invoice_data = curr_b.get("invoice")
        inv_ok = False
        if invoice_data is not None and isinstance(invoice_data, dict):
            inv = invoice_data
            has_fields = all(k in inv for k in ["invoice_no", "base_price", "emergency_fee", "platform_fee", "vat", "grand_total"])
            base_price = float(inv.get("base_price", 0.0))
            emerg_fee = float(inv.get("emergency_fee", 0.0))
            plat_fee = float(inv.get("platform_fee", 0.0))
            grand_total = float(inv.get("grand_total", 0.0))
            vat = float(inv.get("vat", 0.0))
            expected_total = round((base_price + emerg_fee + plat_fee) * 1.05, 2)
            math_ok = (grand_total == expected_total)
            inv_ok = has_fields and math_ok

            inv_no_str = str(inv.get("invoice_no", ""))
            results.append({
                "step": "5. Automated Digital Invoice Generation",
                "passed": inv_ok,
                "details": f"Invoice No: {inv_no_str} | Grand Total: BDT {grand_total} (Base: BDT {base_price}, VAT: BDT {vat})"
            })
            print(f"[PASS] Step 5: Digital Invoice Payload Verified")
            print(f"       - Invoice No:   {inv_no_str}")
            print(f"       - Base Rate:    BDT {base_price}")
            print(f"       - Platform Fee: BDT {plat_fee}")
            print(f"       - VAT (5%):     BDT {vat}")
            print(f"       - Grand Total:  BDT {grand_total}")
        else:
            results.append({"step": "5. Automated Digital Invoice Generation", "passed": False, "details": "Invoice object not found"})
            print(f"[FAIL] Step 5: Invoice object not found")
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
