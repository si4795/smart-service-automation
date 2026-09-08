"""
Smart Provider Matching Engine
BAUST CSE FEST 2026 Competitive Hackathon

Multi-factor scoring algorithm with:
- Double-booking prevention
- Base formula: Score = (Rating * 25) - (Distance * 6) - (Price * 0.015)
- Emergency routing boost: Score += (10 - Distance) * 20
- Workload balancing tie-breaker: Prioritizes lower active_jobs_count
- Dynamic comparison badges: "Top Rated", "Fastest Arrival", "Best Value"
"""

def calculate_match_score(provider, urgency="Normal"):
    """
    Computes multi-factor match score.
    Returns: (total_score, base_score, urgency_boost)
    """
    rating = float(provider.get("rating", 0.0))
    distance = float(provider.get("distance_km", 0.0))
    price = float(provider.get("price", 0.0))

    base_score = (rating * 25.0) - (distance * 6.0) - (price * 0.015)
    urgency_boost = 0.0

    is_emergency = str(urgency).strip().lower() in ["emergency", "high", "urgent"]
    if is_emergency:
        urgency_boost = (10.0 - distance) * 20.0

    total_score = base_score + urgency_boost
    return round(total_score, 2), round(base_score, 2), round(urgency_boost, 2)

def rank_providers(providers, category=None, requested_slot=None, urgency="Normal"):
    """
    Filters out unavailable / busy technicians (Double-booking shield),
    computes multi-factor scores, applies dynamic comparison badges,
    and sorts by:
      1. Total Score (Descending)
      2. Active Jobs Count (Ascending - Workload Balancing tie-breaker)
    """
    available_candidates = []
    busy_candidates = []

    for p in providers:
        # Category Filter
        if category and p.get("category") != category:
            continue

        # Double-booking guard
        if requested_slot and requested_slot in p.get("busy_slots", []):
            busy_candidates.append(dict(p))
            continue

        total_score, base_score, urgency_boost = calculate_match_score(p, urgency)
        cand = dict(p)
        cand["score"] = total_score
        cand["base_score"] = base_score
        cand["urgency_boost"] = urgency_boost
        cand["is_available"] = True
        available_candidates.append(cand)

    if not available_candidates:
        return [], busy_candidates

    # Compute Comparative Badges dynamically across available candidates
    best_rating = max(c["rating"] for c in available_candidates)
    min_dist = min(c["distance_km"] for c in available_candidates)
    min_price = min(c["price"] for c in available_candidates)

    for c in available_candidates:
        badges = []
        if c["rating"] == best_rating:
            badges.append("Top Rated")
        if c["distance_km"] == min_dist:
            badges.append("Fastest Arrival")
        if c["price"] == min_price:
            badges.append("Best Value")
        c["dynamic_badges"] = badges

    # Sort: Primary by score DESC, Secondary by active_jobs_count ASC (Workload Balancing)
    available_candidates.sort(
        key=lambda x: (x["score"], -x.get("active_jobs_count", 0)),
        reverse=True
    )

    return available_candidates, busy_candidates

def auto_assign_emergency(providers, category, requested_slot):
    """
    One-Click Emergency Auto-Assignment:
    Finds the absolute top ranked available technician under Emergency Priority.
    """
    available, _ = rank_providers(
        providers=providers,
        category=category,
        requested_slot=requested_slot,
        urgency="Emergency"
    )
    if available:
        return available[0]
    return None
