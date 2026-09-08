"""
Application routing and HTTP handlers for Smart Home Service Automation platform.
"""
from typing import Any, Dict
from flask import Flask, render_template, request, jsonify, redirect, url_for
from services.mock_db import db, CATEGORIES, STATUS_FLOW
from services.matcher import rank_providers, auto_assign_emergency

app = Flask(__name__)
app.secret_key = "smart-service-automation-key-2026"

@app.route("/", methods=["GET"])
def index():
    """Customer booking portal with dynamic recommendation rankings."""
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
    """Handles search form submissions and redirects with filtered query parameters."""
    category = request.form.get("category", CATEGORIES[0])
    slot_date = request.form.get("slot_date", "2026-09-08")
    slot_time = request.form.get("slot_time", "11:00")
    urgency = request.form.get("urgency", "Normal")
    return redirect(url_for("index", category=category, date=slot_date, time=slot_time, urgency=urgency))

@app.route("/book", methods=["POST"])
def book():
    """Reserves appointment slot and registers initial booking in Requested status."""
    provider_id = request.form.get("provider_id")
    slot = request.form.get("slot")
    urgency = request.form.get("urgency", "Normal")
    client_name = request.form.get("client_name", "Valued Customer").strip()
    client_phone = request.form.get("client_phone", "+880 1700-000000").strip()
    client_address = request.form.get("client_address", "Saidpur, Nilphamari").strip()
    notes = request.form.get("notes", "").strip()

    if not provider_id or not slot:
        return jsonify({"success": False, "error": "Provider ID and appointment slot are required."}), 400

    booking, err = db.create_booking(
        provider_id=provider_id,
        slot=slot,
        urgency=urgency,
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        notes=notes
    )

    if err or booking is None:
        return jsonify({"success": False, "error": err or "Booking reservation failed."}), 409

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"success": True, "booking": booking})

    booking_id = booking.get("id") if (booking is not None and isinstance(booking, dict)) else ""
    return redirect(url_for("tracking", active_id=booking_id))

@app.route("/auto-assign-emergency", methods=["POST"])
def auto_assign():
    """Automatically selects and dispatches the optimal technician for emergency requests."""
    category = request.form.get("category", CATEGORIES[0])
    slot_date = request.form.get("slot_date", "2026-09-08")
    slot_time = request.form.get("slot_time", "11:00")
    slot = f"{slot_date} {slot_time}".strip()
    client_name = request.form.get("client_name", "Emergency Dispatch Client").strip()
    client_phone = request.form.get("client_phone", "+880 1799-998877").strip()
    client_address = request.form.get("client_address", "Saidpur Cantonment Area").strip()
    notes = request.form.get("notes", "Priority Emergency Dispatch").strip()

    all_cat_providers = db.get_providers(category=category)
    best_candidate = auto_assign_emergency(all_cat_providers, category, slot)

    if best_candidate is None or not isinstance(best_candidate, dict):
        return jsonify({
            "success": False,
            "error": f"No technicians currently available in '{category}' for slot {slot}."
        }), 409

    booking, err = db.create_booking(
        provider_id=best_candidate.get("id", ""),
        slot=slot,
        urgency="Emergency",
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        notes=notes
    )

    if err or booking is None:
        return jsonify({"success": False, "error": err or "Failed to reserve emergency booking."}), 409

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "success": True,
            "booking": booking,
            "assigned_provider": best_candidate.get("name", "Assigned Technician")
        })

    booking_id = booking.get("id") if (booking is not None and isinstance(booking, dict)) else ""
    return redirect(url_for("tracking", active_id=booking_id))

@app.route("/provider", methods=["GET"])
def provider():
    """Operations Kanban dashboard organizing tickets across 5 sequential stages."""
    bookings = db.get_bookings()
    kanban: Dict[str, list] = {s: [] for s in STATUS_FLOW}
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
    """Live ticket pipeline view with audit timeline and automated digital invoice."""
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
def update_status(booking_id: str, new_status: str):
    """Advances ticket lifecycle through: Requested -> Accepted -> On the Way -> In Progress -> Completed."""
    booking, err = db.update_status(booking_id, new_status)
    if err or booking is None:
        return jsonify({"success": False, "error": err or "Appointment record not found."}), 400

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"success": True, "booking": booking})

    referrer = request.referrer or ""
    if "tracking" in referrer:
        return redirect(url_for("tracking", active_id=booking_id))
    return redirect(url_for("provider"))

@app.route("/api/summary", methods=["GET"])
def api_summary():
    """Returns service summary metrics and status distributions."""
    bookings = db.get_bookings()
    providers = db.get_providers()
    return jsonify({
        "status": "online",
        "service": "Smart Home Service Automation",
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
    """Pre-seeds operational data across all 5 workflow stages."""
    count = db.seed_demo_stages()
    return jsonify({"success": True, "message": "Demo data populated.", "total_bookings": count})

@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Flushes in-memory booking storage and resets provider schedules."""
    db.reset()
    return jsonify({"success": True, "message": "State reset to defaults."})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
