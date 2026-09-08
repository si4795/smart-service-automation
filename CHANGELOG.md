# CHANGELOG - BAUST CSE FEST 2026 Hackathon

**Project Target**: "Smart Home Service Automation"  
**Team**: Full-Stack Elite Hackathon Finalists  
**Tech Stack**: Python 3.14 (MSYS2 UCRT64), Flask 3.1, Tailwind CSS CDN (Zero-Compiled C++ Wheels Architecture).

This changelog chronologically records all development milestones, features, and algorithmic solutions developed during the 8-hour hackathon window.

---

## [Milestone 4 - Hour 7-8] - Submission Polish & Documentation
### Added
- **Formal Hackathon Documentation**:
  - Detailed `CHANGELOG.md` documenting all functional modules, algorithms, and bonus features.
  - Comprehensive `README.md` with judge demo instructions, architectural diagrams, and rubric mapping.
- **Judge Presentation Fast-Track**:
  - `⚡ Pre-seed 5 Stages Demo`: Instant 1-click test populator that seeds realistic tickets across all 5 discrete workflow stages.
  - `🔄 Reset`: Flushes all state back to baseline.

---

## [Milestone 3 - Hour 5-6] - Provider Dashboard, Tracking Pipeline & Automated Invoicing
### Added
- **Technician Kanban Workflow Dashboard (`templates/provider.html`)**:
  - Live 5-column operational board tracking service tickets through:
    `[Requested] -> [Accepted] -> [On the Way] -> [In Progress] -> [Completed]`.
  - 1-click status advancement buttons with client details, contact links, and address verification.
- **Live Customer Tracking Timeline (`templates/tracking.html`)**:
  - Dynamic visual progress bar with gradient fill connecting completed stages.
  - Chronological audit event timeline with timestamps and step descriptions.
- **Automated Digital Invoice & Tax Receipt Engine**:
  - Triggered automatically upon transitioning to `Completed`.
  - Itemized calculation:
    - Base service rate (BDT)
    - 24/7 Emergency dispatch surcharge (if applicable)
    - Platform safety & convenience fee (৳50.00)
    - Government VAT (5%)
    - Grand Total (BDT)
  - Dedicated print styling (`@media print`) enabling 1-click PDF download or physical receipt printing.
- **Simulated Notification Toasts**:
  - Real-time animated toast alerts upon booking confirmation and stage advancement.

---

## [Milestone 2 - Hour 3-4] - Multi-Factor Smart Matching Engine & Double-Booking Prevention
### Added
- **Multi-Factor Provider Ranking Algorithm (`services/matcher.py`)**:
  $$\text{Base Score} = (\text{Rating} \times 25) - (\text{Distance} \times 6) - (\text{Price} \times 0.015)$$
- **Emergency Priority Weighting**:
  - If urgency == `"Emergency"`, applies proximity-maximizing formula:
    $$\text{Urgency Boost} = (10 - \text{Distance}) \times 20$$
- **Workload Balancing Tie-Breaker**:
  - When technicians tie on score, the algorithm automatically prioritizes the provider with the lowest `active_jobs_count`.
- **Dynamic Comparative Badges**:
  - Evaluates candidates across category to award `★ Top Rated`, `⚡ Fastest Arrival`, and `💎 Best Value` badges.
- **One-Click Emergency Auto-Assignment**:
  - `/auto-assign-emergency` endpoint automatically reserves and dispatches the optimal technician in a single click.
- **Double-Booking Shield & Slot Reservation**:
  - Dynamic calendar slot reservation in `busy_slots`.
  - Exclusion filter omits booked technicians from search results and returns `HTTP 409 Conflict` on conflict.
- **Automated Test Suite (`test_engine.py`)**:
  - 6 unit tests validating math formulas, emergency boosts, double-booking exclusion, workload balancing, auto-assignment, and state transitions.

---

## [Milestone 1 - Hour 1-2] - Modular Project Scaffold & Provider Mock Database
### Added
- **Modular Project Structure**:
  - `services/mock_db.py`: In-memory state manager, thread-safe provider catalogs, and booking repository.
  - `services/matcher.py`: Pure-Python algorithmic scoring engine.
  - `templates/base.html`: Common layout with Tailwind CSS CDN and responsive navigation.
  - `app.py`: Flask routing and API layer.
- **Comprehensive Service Catalog**:
  - 18 mock technicians across 6 core sectors:
    1. Appliance & Gadget Repair
    2. Plumbing
    3. Electrical
    4. Cleaning & Pest Control
    5. Home Maintenance
    6. Car Care & Repair
- **Zero-Compiled Environment Setup**:
  - Python 3.14 on MSYS2 UCRT64 with lightweight Flask.
  - Clean `.gitignore` excluding `venv/`, `__pycache__/`, `.env`.
