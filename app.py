"""
Application routing, authentication, and HTTP handlers for SmartServe platform.
"""
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import Database, db, CATEGORIES, STATUS_FLOW, CATEGORY_ALIASES, CATEGORY_SLUGS

if db is None:
    db = Database()
from services.matcher import rank_providers, auto_assign_emergency

app = Flask(__name__)
app.secret_key = "smart-service-automation-key-2026"

SERVICE_CATEGORIES_METADATA: List[Dict[str, Any]] = [
    {
        "slug": "electrical",
        "name": "Electrical Engineering",
        "title": "Electrical Engineering",
        "icon": "⚡",
        "desc": "Industrial wiring, short circuit isolation, switchgear, backup generator setups",
        "base_rate": "৳420",
        "specialists_count": 3
    },
    {
        "slug": "plumbing",
        "name": "Plumbing & Pipefitting",
        "title": "Plumbing & Pipefitting",
        "icon": "🔧",
        "desc": "Master sanitary fittings, high-pressure pumps, main leaks, pipeline unblocking",
        "base_rate": "৳450",
        "specialists_count": 3
    },
    {
        "slug": "hvac",
        "name": "HVAC & Appliance Care",
        "title": "HVAC & AC Care",
        "icon": "❄️",
        "desc": "Inverter AC servicing, compressor restoration, precision gas charging, HVAC duct care",
        "base_rate": "৳500",
        "specialists_count": 3
    },
    {
        "slug": "appliances",
        "name": "HVAC & Appliance Care",
        "title": "Appliance Repair",
        "icon": "📱",
        "desc": "Washing machines, microwave ovens, water purifiers, deep freezers, smart gadgets",
        "base_rate": "৳380",
        "specialists_count": 3
    },
    {
        "slug": "carpentry",
        "name": "Carpentry & Woodwork",
        "title": "Carpentry & Woodwork",
        "icon": "🪚",
        "desc": "Bespoke cabinetry, hydraulic door alignments, mortise locks, solid wood refinishing",
        "base_rate": "৳550",
        "specialists_count": 3
    },
    {
        "slug": "painting",
        "name": "Pest Control & Hygiene",
        "title": "Home Painting & Hygiene",
        "icon": "🛡️",
        "desc": "Eco-friendly termite barriers, commercial fumigation, wall treatment, sanitization",
        "base_rate": "৳900",
        "specialists_count": 3
    }
]

@app.context_processor
def inject_current_user() -> Dict[str, Any]:
    """Provides current_user in all Jinja templates automatically."""
    user_id = session.get("user_id")
    user = db.get_user_by_id(user_id) if user_id else None
    return {
        "current_user": user,
        "global_categories": CATEGORIES,
        "global_categories_meta": SERVICE_CATEGORIES_METADATA
    }

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
        categories_metadata=SERVICE_CATEGORIES_METADATA,
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

@app.route("/services", methods=["GET"])
@app.route("/services/<category>", methods=["GET"])
@login_required
def services_by_category(category: str = "all"):
    """Full-width specialists search & filter catalog for a category or all categories."""
    selected_date = request.args.get("date", "2026-09-08")
    selected_time = request.args.get("time", "11:00")
    urgency = request.args.get("urgency", "Normal")
    slot = f"{selected_date} {selected_time}".strip()

    canonical_cat = None
    if category.lower() != "all":
        canonical_cat = CATEGORY_ALIASES.get(category) or CATEGORY_ALIASES.get(category.lower()) or category

    all_providers = db.get_providers(category=canonical_cat)
    ranked, busy = rank_providers(
        providers=all_providers,
        category=canonical_cat,
        requested_slot=slot,
        urgency=urgency
    )

    return render_template(
        "specialists.html",
        active_tab="specialists",
        category=category,
        canonical_category=canonical_cat or "All Categories",
        categories=CATEGORIES,
        categories_metadata=SERVICE_CATEGORIES_METADATA,
        selected_date=selected_date,
        selected_time=selected_time,
        selected_slot=slot,
        urgency=urgency,
        providers=ranked,
        busy_providers=busy,
        total_count=len(ranked) + len(busy)
    )

@app.route("/checkout/<technician_id>", methods=["GET"])
@login_required
def checkout_view(technician_id: str):
    """Dedicated booking confirmation and scheduling step."""
    tech = db.get_provider(technician_id)
    if not tech:
        return redirect(url_for("services_by_category", category="all"))

    selected_date = request.args.get("date", "2026-09-08")
    selected_time = request.args.get("time", "11:00")
    urgency = request.args.get("urgency", "Normal")
    slot = f"{selected_date} {selected_time}".strip()
    error_msg = request.args.get("error")

    is_busy = db.is_slot_busy(technician_id, slot)

    base_price = float(tech.get("price", tech.get("base_price", 500.0)))
    platform_fee = 50.0
    is_emergency = str(urgency).strip().lower() in ["emergency", "urgent", "high"]
    emergency_fee = 100.0 if is_emergency else 0.0
    subtotal = base_price + platform_fee + emergency_fee
    vat_amount = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + vat_amount, 2)

    pricing = {
        "base_price": base_price,
        "platform_fee": platform_fee,
        "emergency_fee": emergency_fee,
        "subtotal": subtotal,
        "vat_amount": vat_amount,
        "grand_total": grand_total
    }

    user = get_current_user()

    return render_template(
        "checkout.html",
        active_tab="specialists",
        technician=tech,
        selected_date=selected_date,
        selected_time=selected_time,
        selected_slot=slot,
        urgency=urgency,
        is_busy=is_busy,
        pricing=pricing,
        user=user,
        error=error_msg
    )

@app.route("/checkout", methods=["POST"])
@login_required
def checkout_post():
    """Handles appointment confirmation submission, guards double-booking, and creates booking."""
    user = get_current_user()
    provider_id = request.form.get("provider_id", "").strip()
    slot_date = request.form.get("slot_date", "2026-09-08").strip()
    slot_time = request.form.get("slot_time", "11:00").strip()
    slot = f"{slot_date} {slot_time}".strip()
    urgency = request.form.get("urgency", "Normal").strip()
    client_name = request.form.get("client_name", "").strip()
    client_phone = request.form.get("client_phone", "").strip()
    client_address = request.form.get("client_address", "").strip()
    notes = request.form.get("notes", "").strip()

    if user:
        if not client_name:
            client_name = user.get("name", "Valued Customer")
        if not client_phone:
            client_phone = user.get("phone", "+880 1700-000000")
        if not client_address:
            client_address = user.get("address", "Saidpur Cantonment Area")
    else:
        if not client_name:
            client_name = "Guest Customer"
        if not client_phone:
            client_phone = "+880 1700-000000"
        if not client_address:
            client_address = "Saidpur Cantonment Area"

    if not provider_id or not slot:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": False, "error": "Provider ID and appointment slot are required."}), 400
        return redirect(url_for("services_by_category", category="all"))

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
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": False, "error": err or "Booking reservation failed."}), 409
        return redirect(url_for("checkout_view", technician_id=provider_id, date=slot_date, time=slot_time, urgency=urgency, error=err or "Scheduling conflict."))

    booking_id = str(booking.get("id") or booking.get("booking_code", ""))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "success": True,
            "booking": booking,
            "redirect": url_for("order_status", booking_code=booking_id)
        })

    return redirect(url_for("order_status", booking_code=booking_id))

@app.route("/orders/<booking_code>", methods=["GET"])
@login_required
def order_status(booking_code: str):
    """Real-time customer tracking page with 5-stage milestone stepper and printable invoice."""
    booking = db.get_booking(booking_code)
    if not booking:
        return redirect(url_for("tracking"))

    tech = db.get_provider(booking.get("provider_id", ""))

    current_status = booking.get("status", "Requested")
    try:
        step_index = STATUS_FLOW.index(current_status)
    except ValueError:
        step_index = 0

    messages = db.get_messages(booking_code)

    return render_template(
        "order_status.html",
        active_tab="tracking",
        booking=booking,
        technician=tech,
        messages=messages,
        status_flow=STATUS_FLOW,
        step_index=step_index,
        current_status=current_status
    )

@app.route("/orders/<booking_code>/messages", methods=["GET", "POST"])
@login_required
def order_messages(booking_code: str):
    """In-app order direct messaging between customer and assigned specialist."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    if request.method == "POST":
        message_text = request.form.get("message", "").strip()
        if not message_text and request.is_json:
            data = request.get_json(silent=True) or {}
            message_text = str(data.get("message", "")).strip()

        if not message_text:
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        msg = db.send_message(
            booking_code=booking_code,
            sender_id=str(user["id"]),
            sender_role=str(user.get("role", "customer")),
            sender_name=str(user.get("name", "User")),
            message=message_text
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": True, "message": msg})

        referrer = request.referrer or ""
        if "tracking" in referrer:
            return redirect(url_for("tracking", active_id=booking_code))
        return redirect(url_for("order_status", booking_code=booking_code))

    messages = db.get_messages(booking_code)
    return jsonify({"success": True, "booking_code": booking_code, "messages": messages})

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
@login_required
def tracking():
    """Live ticket pipeline view with audit timeline and automated digital invoice."""
    bookings = db.get_bookings()
    active_id = request.args.get("active_id")
    active_booking = None
    if active_id:
        active_booking = db.get_booking(active_id)
    if not active_booking and bookings:
        active_booking = bookings[0]

    messages = db.get_messages(active_booking["id"]) if active_booking else []

    return render_template(
        "tracking.html",
        active_tab="tracking",
        bookings=bookings,
        active_booking=active_booking,
        messages=messages,
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
    if "orders" in referrer:
        return redirect(url_for("order_status", booking_code=booking_id))
    if "tracking" in referrer:
        return redirect(url_for("tracking", active_id=booking_id))
    return redirect(url_for("provider"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile management, personal settings, and contact information."""
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    user_id = str(user["id"])

    success_msg = None
    error_msg = None

    if request.method == "POST":
        action = request.form.get("action", "update_profile").strip()

        if action == "update_password":
            old_password = request.form.get("old_password", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()

            if not old_password:
                error_msg = "Current password is required."
            elif not new_password:
                error_msg = "Please enter a new password."
            elif len(new_password) < 6:
                error_msg = "New password must be at least 6 characters long."
            elif new_password != confirm_password:
                error_msg = "New passwords do not match."
            else:
                updated_user, err = db.update_user_profile(
                    user_id=user_id,
                    password=new_password,
                    old_password=old_password
                )
                if err or not updated_user:
                    error_msg = err or "Failed to update password."
                else:
                    user = updated_user
                    success_msg = "Security credentials updated successfully."
        else:
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            address = request.form.get("address", "").strip()

            if not name:
                error_msg = "Full name cannot be empty."
            else:
                updated_user, err = db.update_user_profile(
                    user_id=user_id,
                    name=name,
                    phone=phone,
                    address=address
                )
                if err or not updated_user:
                    error_msg = err or "Failed to update profile."
                else:
                    user = updated_user
                    session["user_name"] = user["name"]
                    success_msg = "Profile details updated successfully."

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            if error_msg:
                return jsonify({"success": False, "error": error_msg}), 400
            stats = db.get_user_stats(user_id)
            return jsonify({"success": True, "message": success_msg, "user": user, "stats": stats})

    stats = db.get_user_stats(user_id)
    return render_template(
        "profile.html",
        active_tab="profile",
        user=user,
        stats=stats,
        success=success_msg,
        error=error_msg
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    """Authentication route supporting credentials and 1-click persona logins."""
    user = get_current_user()
    if user and request.method == "GET":
        if user.get("role") == "technician":
            return redirect(url_for("provider"))
        return redirect(url_for("dashboard"))

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
    user = get_current_user()
    if user and request.method == "GET":
        if user.get("role") == "technician":
            return redirect(url_for("provider"))
        return redirect(url_for("dashboard"))

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
