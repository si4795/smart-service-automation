"""
Multi-factor technician matching and ranking engine.
Implements distance penalty, rating weighting, urgency multipliers, and workload balancing.
"""
from typing import Any, Dict, List, Optional, Tuple
from services.mock_db import CATEGORY_ALIASES

def calculate_match_score(provider: Dict[str, Any], urgency: str = "Normal") -> Tuple[float, float, float]:
    """
    Computes provider ranking score:
      Base Score = (Rating * 25) - (Distance * 6) - (Price * 0.015)
      Emergency Boost = (10 - Distance) * 20 (if Urgency == 'Emergency')
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

def rank_providers(
    providers: List[Dict[str, Any]],
    category: Optional[str] = None,
    requested_slot: Optional[str] = None,
    urgency: str = "Normal"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filters unavailable technicians, applies scoring weights, and sorts by:
      1. Composite match score (descending)
      2. Active jobs count (ascending workload balancing)
    """
    available_candidates: List[Dict[str, Any]] = []
    busy_candidates: List[Dict[str, Any]] = []

    canonical = CATEGORY_ALIASES.get(category, category) if category else None

    for p in providers:
        if canonical and p.get("category") != canonical and p.get("category") != category:
            continue

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

    best_rating = max(c["rating"] for c in available_candidates)
    min_dist = min(c["distance_km"] for c in available_candidates)
    min_price = min(c["price"] for c in available_candidates)

    for c in available_candidates:
        badges: List[str] = []
        if c["rating"] == best_rating:
            badges.append("Top Rated")
        if c["distance_km"] == min_dist:
            badges.append("Fastest Arrival")
        if c["price"] == min_price:
            badges.append("Best Value")
        c["dynamic_badges"] = badges

    available_candidates.sort(
        key=lambda x: (x["score"], -x.get("active_jobs_count", 0)),
        reverse=True
    )

    return available_candidates, busy_candidates

def auto_assign_emergency(
    providers: List[Dict[str, Any]],
    category: str,
    requested_slot: str
) -> Optional[Dict[str, Any]]:
    """Selects the highest scoring available technician for immediate emergency dispatch."""
    available, _ = rank_providers(
        providers=providers,
        category=category,
        requested_slot=requested_slot,
        urgency="Emergency"
    )
    return available[0] if available else None
