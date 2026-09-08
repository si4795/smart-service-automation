"""
Application routing, authentication, and HTTP handlers for SmartServe platform.
"""
from functools import wraps
from typing import Any, Dict, Optional, Tuple
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from services.mock_db import db, CATEGORIES, STATUS_FLOW
from services.matcher import rank_providers, auto_assign_emergency

app = Flask(__name__)
app.secret_key = "smart-service-automation-key-2026"

@app.context_processor
def inject_current_user() -> Dict[str, Any]:
    """Provides current_user in all Jinja templates automatically."""
    user_id = session.get("user_id")
    user = db.get_user_by_id(user_id) if user_id else None
    return {"current_user": user}

def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieves authenticated user from session if valid."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.get_user_by_id(user_id)

def login_required(f):
    """Decorator ensuring request has an active authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": "Authentication required.", "require_login": True}), 401
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role: str):
    """Decorator enforcing role-based access control (RBAC)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return redirect(url_for("login", next=request.url, error=f"Please sign in with a {role} account."))
            if user.get("role") != role:
                return redirect(url_for("login", next=request.url, error=f"Access restricted to {role} accounts."))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/", methods=["GET"])
def landing():
    """Consumer entry portal and landing page for SmartServe platform."""
    user = get_current_user()
    if user:
        if user.get("role") == "technician":
            return redirect(url_for("provider"))
        return redirect(url_for("dashboard"))
    all_providers = db.get_providers()
    return render_template(
        "landing.html",
        categories=CATEGORIES,
        total_providers=len(all_providers),
        providers=all_providers[:6]
    )

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
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

@app.route("/index", methods=["GET"])
def index():
    """Backward compatibility alias pointing to dashboard."""
    return redirect(url_for("dashboard"))

@app.route("/search", methods=["POST"])
def search():
    """Handles search form submissions and redirects with filtered query parameters."""
    category = request.form.get("category", CATEGORIES[0])
    slot_date = request.form.get("slot_date", "2026-09-08")
    slot_time = request.form.get("slot_time", "11:00")
    urgency = request.form.get("urgency", "Normal")
    return redirect(url_for("dashboard", category=category, date=slot_date, time=slot_time, urgency=urgency))

@app.route("/book", methods=["POST"])
def book():
    """Reserves appointment slot and registers initial booking in Requested status."""
    user = get_current_user()
    provider_id = request.form.get("provider_id")
    slot = request.form.get("slot")
    urgency = request.form.get("urgency", "Normal")
    client_name = request.form.get("client_name", "").strip()
    client_phone = request.form.get("client_phone", "").strip()
    client_address = request.form.get("client_address", "").strip()
    notes = request.form.get("notes", "").strip()

    if user:
        if not client_name:
            client_name = user["name"]
        if not client_phone:
            client_phone = user.get("phone", "+880 1700-000000")
        if not client_address:
            client_address = user.get("address", "Saidpur Cantonment Area")
    else:
        # Prompt authentication for unauthenticated browser flows
        if not client_name or client_name == "Valued Customer":
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({
                    "success": False,
                    "error": "Please sign in to confirm your booking.",
                    "require_login": True
                }), 401
            return redirect(url_for("login", next=url_for("dashboard")))
        if not client_phone:
            client_phone = "+880 1700-000000"
        if not client_address:
            client_address = "Saidpur, Nilphamari"

    if not provider_id or not slot:
        return jsonify({"success": False, "error": "Provider ID and appointment slot are required."}), 400

    user_id = user["id"] if user else None
    booking, err = db.create_booking(
        provider_id=provider_id,
        slot=slot,
        urgency=urgency,
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        notes=notes,
        user_id=user_id
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
    user = get_current_user()
    category = request.form.get("category", CATEGORIES[0])
    slot_date = request.form.get("slot_date", "2026-09-08")
    slot_time = request.form.get("slot_time", "11:00")
    slot = f"{slot_date} {slot_time}".strip()

    client_name = request.form.get("client_name", "").strip()
    client_phone = request.form.get("client_phone", "").strip()
    client_address = request.form.get("client_address", "").strip()
    notes = request.form.get("notes", "Priority Emergency Dispatch").strip()

    if user:
        if not client_name:
            client_name = user["name"]
        if not client_phone:
            client_phone = user.get("phone", "+880 1700-000000")
        if not client_address:
            client_address = user.get("address", "Saidpur Cantonment Area")
    else:
        if not client_name:
            client_name = "Emergency Dispatch Client"
        if not client_phone:
            client_phone = "+880 1799-998877"
        if not client_address:
            client_address = "Saidpur Cantonment Area"

    all_cat_providers = db.get_providers(category=category)
    best_candidate = auto_assign_emergency(all_cat_providers, category, slot)

    if best_candidate is None or not isinstance(best_candidate, dict):
        return jsonify({
            "success": False,
            "error": f"No technicians currently available in '{category}' for slot {slot}."
        }), 409

    user_id = user["id"] if user else None
    booking, err = db.create_booking(
        provider_id=best_candidate.get("id", ""),
        slot=slot,
        urgency="Emergency",
        client_name=client_name,
        client_phone=client_phone,
        client_address=client_address,
        notes=notes,
        user_id=user_id
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
@role_required("technician")
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

@app.route("/login", methods=["GET", "POST"])
def login():
    """Authentication route supporting credentials and 1-click persona logins."""
    next_url = request.args.get("next") or request.form.get("next") or ""
    error_msg = request.args.get("error")

    if request.method == "POST":
        demo_role = request.form.get("demo_role", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user: Optional[Dict[str, Any]] = None
        if demo_role == "customer":
            user = db.authenticate_user("customer@smartserve.local", "pass123")
        elif demo_role == "technician":
            user = db.authenticate_user("tech@smartserve.local", "pass123")
        elif email:
            user = db.authenticate_user(email, password)

        if not user:
            err = "Invalid email or password. Please check your credentials."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err}), 401
            return render_template("login.html", error=err, next=next_url)

        session["user_id"] = user["id"]
        session["user_role"] = user["role"]
        session["user_name"] = user["name"]
        session.permanent = True

        target_redirect = next_url if (next_url and next_url.startswith("/")) else (
            url_for("provider") if user["role"] == "technician" else url_for("dashboard")
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": True, "redirect": target_redirect, "user": user})

        return redirect(target_redirect)

    return render_template("login.html", next=next_url, error=error_msg)

@app.route("/api/quick-login", methods=["POST"])
def api_quick_login():
    """AJAX 1-click login endpoint for in-modal authentication."""
    role = request.form.get("role", "customer").strip()
    email = "tech@smartserve.local" if role == "technician" else "customer@smartserve.local"
    user = db.authenticate_user(email, "pass123")

    if not user:
        return jsonify({"success": False, "error": "Demo account unavailable."}), 500

    session["user_id"] = user["id"]
    session["user_role"] = user["role"]
    session["user_name"] = user["name"]
    session.permanent = True

    return jsonify({"success": True, "user": user})

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Registration endpoint for new customer or technician accounts."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "customer").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        user, err = db.create_user(
            email=email,
            password=password,
            name=name,
            role=role,
            phone=phone,
            address=address
        )

        if err or not user:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err or "Registration failed."}), 400
            return render_template(
                "signup.html",
                error=err,
                name=name,
                email=email,
                role=role,
                phone=phone,
                address=address
            )

        session["user_id"] = user["id"]
        session["user_role"] = user["role"]
        session["user_name"] = user["name"]
        session.permanent = True

        target_redirect = url_for("provider") if user["role"] == "technician" else url_for("dashboard")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": True, "redirect": target_redirect, "user": user})

        return redirect(target_redirect)

    return render_template("signup.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Terminates session and redirects to homepage."""
    session.clear()
    return redirect(url_for("landing"))

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
