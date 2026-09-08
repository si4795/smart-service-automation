"""
Smart Home Service Automation - Application Entry Point & Flask Router
BAUST CSE FEST 2026 Competitive Hackathon
"""
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from services.mock_db import db, CATEGORIES, STATUS_FLOW
from services.matcher import rank_providers, calculate_match_score, auto_assign_emergency

app = Flask(__name__)
app.secret_key = "baust-cse-fest-2026-smart-home-service-key"

@app.route("/", methods=["GET"])
def index():
    """Customer Booking & Smart Recommendation Portal (Tab 1)."""
    selected_category = request.args.get("category", CATEGORIES[0])
    selected_date = request.args.get("date", "2026-09-08")
    selected_time = request.args.get("time", "11:00")
    urgency = request.args.get("urgency", "Normal")
    slot = f"{selected_date} {selected_time}".strip()

    all_providers = db.get_providers(category=selected_category)
    ranked, busy = rank_providers(
        providers=all_providers,
        category=selected_category,
        requested_slot=slot,
        urgency=urgency
    )

    return render_template(
        "index.html",
        active_tab="customer",
        categories=CATEGORIES,
        selected_category=selected_category,
        selected_date=selected_date,
        selected_time=selected_time,
        selected_slot=slot,
        urgency=urgency,
        providers=ranked,
        busy_providers=busy,
        total_bookings=len(db.get_bookings()),
        status_flow=STATUS_FLOW
    )

@app.route("/search", methods=["POST"])
def search():
    """Processes search filters and redirects to index with query parameters."""
    category = request.form.get("category", CATEGORIES[0])
    slot_date = request.form.get("slot_date", "2026-09-08")
    slot_time = request.form.get("slot_time", "11:00")
    urgency = request.form.get("urgency", "Normal")
    return redirect(url_for("index", category=category, date=slot_date, time=slot_time, urgency=urgency))

@app.route("/book", methods=["POST"])
def book():
    """
    Validates slot availability (Double-booking shield),
    reserves technician slot, and creates a booking in 'Requested' state.
    """
    provider_id = request.form.get("provider_id")
    slot = request.form.get("slot")
    urgency = request.form.get("urgency", "Normal")
    client_name = request.form.get("client_name", "Valued Customer").strip()
    client_phone = request.form.get("client_phone", "+880 1700-000000").strip()
    client_address = request.form.get("client_address", "Dhaka, Bangladesh").strip()
    notes = request.form.get("notes", "").strip()

    if not provider_id or not slot:
        return jsonify({"success": False, "error": "Provider and Slot are mandatory."}), 400

    booking, err = db.create_booking(
        provider_id=provider_id,
        slot=slot,
        urgency=urgency,
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        notes=notes
    )

    if err:
        return jsonify({"success": False, "error": err}), 409

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"success": True, "booking": booking})

    return redirect(url_for("tracking", active_id=booking["id"]))

@app.route("/auto-assign-emergency", methods=["POST"])
def auto_assign():
    """
    Special Feature: One-Click Emergency Auto-Assignment
    Automatically selects and books the highest-ranked available technician for immediate dispatch.
    """
    category = request.form.get("category", CATEGORIES[0])
    slot_date = request.form.get("slot_date", "2026-09-08")
    slot_time = request.form.get("slot_time", "11:00")
    slot = f"{slot_date} {slot_time}".strip()
    client_name = request.form.get("client_name", "Emergency Client").strip()
    client_phone = request.form.get("client_phone", "+880 1799-998877").strip()
    client_address = request.form.get("client_address", "Dhaka, Bangladesh").strip()
    notes = request.form.get("notes", "🚨 CRITICAL EMERGENCY - IMMEDIATE ASSISTANCE NEEDED").strip()

    all_cat_providers = db.get_providers(category=category)
    best_candidate = auto_assign_emergency(all_cat_providers, category, slot)

    if not best_candidate:
        return jsonify({
            "success": False,
            "error": f"No technicians currently available for {category} at {slot} due to existing bookings."
        }), 409

    booking, err = db.create_booking(
        provider_id=best_candidate["id"],
        slot=slot,
        urgency="Emergency",
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        notes=notes
    )

    if err:
        return jsonify({"success": False, "error": err}), 409

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "success": True,
            "booking": booking,
            "assigned_provider": best_candidate["name"]
        })

    return redirect(url_for("tracking", active_id=booking["id"]))

@app.route("/provider", methods=["GET"])
def provider():
    """Technician Kanban Operations Board (Tab 2)."""
    bookings = db.get_bookings()
    kanban = {s: [] for s in STATUS_FLOW}
    for b in bookings:
        kanban.setdefault(b["status"], []).append(b)

    return render_template(
        "provider.html",
        active_tab="provider",
        bookings=bookings,
        kanban=kanban,
        status_flow=STATUS_FLOW,
        total_bookings=len(bookings)
    )

@app.route("/tracking", methods=["GET"])
def tracking():
    """Customer Live Tracking & Digital Invoicing (Tab 3)."""
    bookings = db.get_bookings()
    active_id = request.args.get("active_id")
    active_booking = None
    if active_id:
        active_booking = db.get_booking(active_id)
    if not active_booking and bookings:
        active_booking = bookings[0]

    return render_template(
        "tracking.html",
        active_tab="tracking",
        bookings=bookings,
        active_booking=active_booking,
        status_flow=STATUS_FLOW,
        total_bookings=len(bookings)
    )

@app.route("/update-status/<booking_id>/<new_status>", methods=["POST", "GET"])
def update_status(booking_id, new_status):
    """
    Advances state through the mandatory sequence:
    [Requested] -> [Accepted] -> [On the Way] -> [In Progress] -> [Completed]
    """
    booking, err = db.update_status(booking_id, new_status)
    if err:
        return jsonify({"success": False, "error": err}), 400

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"success": True, "booking": booking})

    referrer = request.referrer or ""
    if "tracking" in referrer:
        return redirect(url_for("tracking", active_id=booking_id))
    return redirect(url_for("provider"))

@app.route("/api/summary", methods=["GET"])
def api_summary():
    """Returns complete real-time JSON metrics for validation and tests."""
    bookings = db.get_bookings()
    providers = db.get_providers()
    return jsonify({
        "status": "online",
        "competition": "BAUST CSE FEST 2026",
        "challenge": "Smart Home Service Automation",
        "total_providers": len(providers),
        "categories": CATEGORIES,
        "total_bookings": len(bookings),
        "status_distribution": {
            s: len([b for b in bookings if b.get("status") == s]) for s in STATUS_FLOW
        },
        "recent_bookings": bookings[:5]
    })

@app.route("/api/seed-demo", methods=["POST", "GET"])
def api_seed_demo():
    """Fast-track judge demo: seeds realistic bookings across all 5 stages."""
    count = db.seed_demo_stages()
    return jsonify({"success": True, "message": "Demo stages seeded successfully.", "total_bookings": count})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Resets mock database to pristine baseline state."""
    db.reset()
    return jsonify({"success": True, "message": "Database reset to defaults."})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
