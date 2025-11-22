"""
recommender_module.py
Recommender module for Hotel Recommendation POC

Provides:
- dataclasses: UserInput, Hotel
- functions: hard_filter, compute_price_fit, compute_rating_fit, compute_score,
             search_with_expansion, generate_mock_hotels
- JSON export functions: export_results_to_json, export_hotels_to_json
- constants for default parameters and purpose weights / rating floors

Usage:
>>> from recommender_module import UserInput, Hotel, generate_mock_hotels, search_with_expansion
>>> hotels = generate_mock_hotels(100)
>>> inp = UserInput(district="Quận 3", budget_min=900000, budget_max=1400000, purpose="business",
...                 check_in="2025-11-14", check_out="2025-11-15", topN=5)
>>> results, meta = search_with_expansion(hotels, inp, topN=5)
>>> export_results_to_json(results, meta, "results.json")
"""

from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Any
from datetime import datetime, date
import random
import json

# --------------------------- Utilities ---------------------------
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def parse_date(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()

# --------------------------- Data classes ---------------------------
@dataclass
class UserInput:
    district: str
    budget_min: float
    budget_max: float
    purpose: str  # leisure, business, family, budget, premium, long_term
    check_in: str
    check_out: str
    topN: int = 5

@dataclass
class Hotel:
    id: int
    name: str
    district: str
    price: float
    rating: float
    capacity: int = 1
    amenities: List[str] = field(default_factory=list)
    available_from: str = "2025-01-01"
    available_to: str = "2025-12-31"

# --------------------------- Default parameters ---------------------------
DEFAULT_LAMBDA = 0.25
DEFAULT_TAU_LOW = 200000.0   # scale for below-min penalty
DEFAULT_TAU_HIGH = 200000.0  # scale for above-max penalty

PURPOSE_WEIGHT = {
    "leisure": (0.4, 0.6),
    "family":  (0.4, 0.6),
    "premium": (0.4, 0.6),
    "business":(0.6, 0.4),
    "budget":  (0.7, 0.3),
    "long_term":(0.7, 0.3),
}

RATING_FLOOR = {
    "leisure": 7.0,
    "family": 7.0,
    "premium": 7.5,
    "business": 7.0,
    "budget": 6.0,
    "long_term": 6.0,
}

# --------------------------- Core algorithm functions ---------------------------
def is_available(h: Hotel, check_in: str, check_out: str) -> bool:
    try:
        a_from = parse_date(h.available_from)
        a_to = parse_date(h.available_to)
        ci = parse_date(check_in)
        co = parse_date(check_out)
    except Exception:
        # if dates invalid or missing, treat as available (validation should be done upstream)
        return True
    return (a_from <= ci) and (a_to >= co)

def hard_filter(hotels: List[Hotel], inp: UserInput) -> List[Hotel]:
    """
    Apply basic hard filters:
    - district must match
    - availability must cover check_in..check_out
    - rating must be >= rating floor for purpose
    """
    results = []
    floor = RATING_FLOOR.get(inp.purpose, 6.0)
    for h in hotels:
        if h.district != inp.district:
            continue
        if not is_available(h, inp.check_in, inp.check_out):
            continue
        if h.rating < floor:
            continue
        results.append(h)
    return results

def compute_price_fit(price: float, budget_min: float, budget_max: float,
                      lam: float = DEFAULT_LAMBDA,
                      tau_low: float = DEFAULT_TAU_LOW,
                      tau_high: float = DEFAULT_TAU_HIGH) -> float:
    """
    Compute price_fit in [0,1].
    - inside bucket: 1 - lam * (2 * |price - mid| / W)
      (mid = center, W = width; so value at edges = 1 - lam)
    - below bucket: linear penalty scaled by tau_low
    - above bucket: linear penalty scaled by tau_high
    """
    mid = (budget_min + budget_max) / 2.0
    W = max(1.0, budget_max - budget_min)
    if budget_min <= price <= budget_max:
        val = 1.0 - lam * (2.0 * abs(price - mid) / W)
    elif price < budget_min:
        val = 1.0 - (budget_min - price) / tau_low
    else:
        val = 1.0 - (price - budget_max) / tau_high
    return clamp(val, 0.0, 1.0)

def compute_rating_fit(rating: float) -> float:
    """Normalize rating (0..10) to [0,1]."""
    if rating is None:
        return 0.0
    return clamp(rating / 10.0, 0.0, 1.0)

def compute_score(h: Hotel, inp: UserInput,
                  lam: float = DEFAULT_LAMBDA,
                  tau_low: float = DEFAULT_TAU_LOW,
                  tau_high: float = DEFAULT_TAU_HIGH) -> float:
    w_price, w_rating = PURPOSE_WEIGHT.get(inp.purpose, (0.5, 0.5))
    pf = compute_price_fit(h.price, inp.budget_min, inp.budget_max, lam, tau_low, tau_high)
    rf = compute_rating_fit(h.rating)
    return w_price * pf + w_rating * rf

# --------------------------- Search with bucket expansion ---------------------------
def search_with_expansion(hotels: List[Hotel], inp: UserInput, topN: int = 5,
                          lam: float = DEFAULT_LAMBDA,
                          tau_low: float = DEFAULT_TAU_LOW,
                          tau_high: float = DEFAULT_TAU_HIGH,
                          max_attempts: int = 2) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run search; if no results, attempt up to max_attempts expansions:
      attempt 0 -> widen budget by ±50%·W
      attempt 1 -> relax tau_high (make over-budget penalty milder)
    Returns (results, meta)
    meta contains attempts, expanded flag, and final params
    """
    attempt = 0
    expanded = False
    W = max(1.0, inp.budget_max - inp.budget_min)
    current_min = inp.budget_min
    current_max = inp.budget_max
    current_tau_high = tau_high

    while True:
        candidates = hard_filter(hotels, inp)
        scored = []
        for h in candidates:
            # use current_min/current_max when computing score
            temp_input = UserInput(inp.district, current_min, current_max, inp.purpose, inp.check_in, inp.check_out)
            sc = compute_score(h, temp_input, lam=lam, tau_low=tau_low, tau_high=current_tau_high)
            if sc > 0:
                scored.append((h, sc))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:topN]

        if top:
            results = [{
                "id": h.id,
                "name": h.name,
                "district": h.district,
                "price": h.price,
                "rating": h.rating,
                "amenities": h.amenities,
                "score": round(sc, 4)
            } for h, sc in top]
            meta = {"attempts": attempt+1, "expanded": expanded, "current_min": current_min, "current_max": current_max, "tau_high": current_tau_high}
            return results, meta

        # no results; decide if we can expand
        if attempt >= max_attempts:
            return [], {"attempts": attempt, "expanded": expanded, "reason": "no_results"}

        if attempt == 0:
            # widen budget by ±50% of original W
            delta = 0.5 * W
            current_min = max(0.0, inp.budget_min - delta)
            current_max = inp.budget_max + delta
            expanded = True
        elif attempt == 1:
            # relax tau_high to be more permissive for over-budget results
            current_tau_high = current_tau_high * 1.5
        attempt += 1

# --------------------------- JSON Export Functions ---------------------------
def export_results_to_json(results: List[Dict[str, Any]], meta: Dict[str, Any], 
                           filepath: str, indent: int = 2) -> None:
    """
    Export search results and metadata to a JSON file.
    
    Args:
        results: List of hotel dictionaries from search_with_expansion
        meta: Metadata dictionary from search_with_expansion
        filepath: Path to output JSON file
        indent: JSON indentation (default: 2)
    """
    output = {
        "results": results,
        "meta": meta,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=indent)
    
    print(f"Results exported to {filepath}")

def export_hotels_to_json(hotels: List[Hotel], filepath: str, indent: int = 2) -> None:
    """
    Export a list of Hotel objects to a JSON file.
    
    Args:
        hotels: List of Hotel dataclass instances
        filepath: Path to output JSON file
        indent: JSON indentation (default: 2)
    """
    hotels_data = [asdict(h) for h in hotels]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(hotels_data, f, ensure_ascii=False, indent=indent)
    
    print(f"Hotels exported to {filepath}")

def load_hotels_from_json(filepath: str) -> List[Hotel]:
    """
    Load hotels from a JSON file.
    
    Args:
        filepath: Path to JSON file containing hotel data
    
    Returns:
        List of Hotel dataclass instances
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    hotels = [Hotel(**h) for h in data]
    print(f"Loaded {len(hotels)} hotels from {filepath}")
    return hotels

def rank_and_export(hotels: List[Hotel], user_inputs: List[UserInput], 
                    output_dir: str = ".", topN: int = 10) -> None:
    """
    Rank hotels for multiple user queries and export each result to JSON.
    
    Args:
        hotels: List of all available hotels
        user_inputs: List of UserInput queries to process
        output_dir: Directory to save JSON files (default: current directory)
        topN: Number of top results per query
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for idx, inp in enumerate(user_inputs, 1):
        results, meta = search_with_expansion(hotels, inp, topN=topN)
        
        # Create filename from query parameters
        filename = f"results_{idx}_{inp.district.replace(' ', '_')}_{inp.purpose}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Add query info to meta
        meta['query'] = asdict(inp)
        
        export_results_to_json(results, meta, filepath)

# --------------------------- Mock data generator (useful for testing) ---------------------------
def generate_mock_hotels(n: int = 50, seed: int = 1) -> List[Hotel]:
    random.seed(seed)
    centers = ["Quận 1", "Quận 3", "Bình Thạnh"]
    outer = ["Tân Phú", "Bình Tân", "Gò Vấp"]
    hotels = []
    idx = 1
    for _ in range(n):
        if random.random() < 0.45:
            d = random.choice(centers)
            price = random.randint(800000, 2000000)
        else:
            d = random.choice(outer)
            price = random.randint(300000, 800000)
        rating = round(random.uniform(5.0, 9.5), 1)
        amenities = random.sample(["wifi", "elevator", "parking", "breakfast", "pool", "gym"], k=random.randint(1, 3))
        hotels.append(Hotel(id=idx, name=f"Hotel {idx}", district=d, price=price, rating=rating, amenities=amenities))
        idx += 1
    return hotels

# --------------------------- Quick demo when run as script ---------------------------
if __name__ == "__main__":
    # Generate mock hotels
    hotels = generate_mock_hotels(120, seed=42)
    
    # Export all hotels to JSON
    export_hotels_to_json(hotels, "all_hotels.json")
    
    # Single query example
    inp = UserInput(
        district="Quận 3", 
        budget_min=900000, 
        budget_max=1400000, 
        purpose="business",
        check_in="2025-11-14", 
        check_out="2025-11-15", 
        topN=5
    )
    results, meta = search_with_expansion(hotels, inp, topN=5)
    
    # Export single result
    export_results_to_json(results, meta, "search_results.json")
    
    print("\nSearch meta:", meta)
    print(f"\nTop {len(results)} results:")
    for r in results:
        print(f"  {r['name']}: score={r['score']}, price={r['price']}, rating={r['rating']}")
    
    # Multiple queries example
    queries = [
        UserInput("Quận 1", 1000000, 1500000, "premium", "2025-12-01", "2025-12-03", 5),
        UserInput("Quận 3", 500000, 800000, "budget", "2025-12-10", "2025-12-12", 5),
        UserInput("Bình Thạnh", 800000, 1200000, "family", "2025-12-15", "2025-12-17", 5),
    ]
    
    rank_and_export(hotels, queries, output_dir="results", topN=10)
    print("\n✓ Multiple queries exported to 'results/' directory")