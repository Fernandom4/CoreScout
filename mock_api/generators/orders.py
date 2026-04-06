import random
from datetime import date, timedelta
import bisect

from config import (
    BASE_SEED,
    BUYER_PROTECTION_RATE,
    CARRIERS,
    HOUR_WEIGHTS,
    ITEMS_PER_ORDER_DIST,
    LAUNCH_DATE,
    MARKETS,
    PAYMENT_METHODS,
    PAYMENT_PROCESSING_RATE,
    RATING_WEIGHTS_NORMAL,
    RATING_WEIGHTS_RETURNED,
    REGIONS,
    RETURN_RATES,
    RETURN_REASONS,
    REVIEW_RATE,
    SELLER_TIERS,
    SHIPPING_PARAMS,
)
from generators.helpers import (
    build_cum_weights_uniform,
    build_cum_weights_zipf,
    get_daily_order_count,
    paginate,
    stable_id,
)
from generators.reference import (
    get_buyer_list,
    get_product_list,
    get_seller_list,
)


# ---------------------------------------------------------------------------
# Entity pools
#
# For a given date we need the set of buyers and sellers that existed on
# that date. We also need per-region pools so we can enforce the region
# constraint — buyers only purchase from sellers in the same region.
#
# Seller pools are Zipf-weighted so popular sellers get more orders.
# Buyer pools are also Zipf-weighted so frequent shoppers buy more often.
# ---------------------------------------------------------------------------
def _build_pools(event_date: date) -> dict:
    """Build buyer and seller pools per region for a given date.

    Returns a dict with structure:
    {
        "region_name": {
            "sellers": [seller_dict, ...],
            "seller_zipf": [cumulative_weights, ...],
            "seller_products": {seller_id: [product_dict, ...]},
            "buyers": [buyer_dict, ...],
            "buyer_zipf": [cumulative_weights, ...],
        }
    }
    """
    all_sellers = get_seller_list(event_date)
    all_buyers = get_buyer_list(event_date)
    all_products = get_product_list(event_date)

    # Index products by seller_id for fast lookup
    products_by_seller = {}
    for product in all_products:
        sid = product["seller_id"]
        if sid not in products_by_seller:
            products_by_seller[sid] = []
        products_by_seller[sid].append(product)

    # Build per-region pools
    pools = {}
    for region in REGIONS:
        region_sellers = [s for s in all_sellers if s["region"] == region]
        region_buyers = [b for b in all_buyers if b["region"] == region]

        # Only include sellers that have at least one product
        region_sellers = [s for s in region_sellers if s["seller_id"] in products_by_seller]

        if not region_sellers or not region_buyers:
            continue

        pools[region] = {
            "sellers": region_sellers,
            "seller_zipf": build_cum_weights_zipf(len(region_sellers)),
            "seller_products": {
                s["seller_id"]: products_by_seller[s["seller_id"]] for s in region_sellers
            },
            "buyers": region_buyers,
            "buyer_zipf": build_cum_weights_zipf(len(region_buyers)),
        }

    return pools


# ---------------------------------------------------------------------------
# Timestamp generation
#
# Orders get a realistic timestamp based on HOUR_WEIGHTS. Peak at 19:00,
# dead between 1-5am. The date is fixed (the event_date), only the time
# varies.
# ---------------------------------------------------------------------------
def _generate_timestamp(event_date: date, rng: random.Random) -> str:
    """Generate a realistic datetime string for an order on a given date.

    Args:
        event_date: the date of the order
        rng:        seeded random instance
    """
    # Pick hour using cumulative weights
    cum_weights = []
    total = sum(HOUR_WEIGHTS)
    running = 0.0
    for w in HOUR_WEIGHTS:
        running += w / total
        cum_weights.append(running)

    hour = bisect.bisect_left(cum_weights, rng.random())
    hour = min(hour, 23)

    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)

    return f"{event_date.isoformat()}T{hour:02d}:{minute:02d}:{second:02d}"


# ---------------------------------------------------------------------------
# Order generation
#
# Generates all orders for a given date across all markets.
# Each order has two levels:
#   - Order-level: carrier, shipping dates, payment method (shared across items)
#   - Item-level: product, quantity, price, fees, returns, reviews (per item)
#
# All lifecycle events are determined at order creation time using a
# deterministic seed so the same date always produces the same orders.
# ---------------------------------------------------------------------------
def _generate_order(
    idx: int,
    event_date: date,
    rng: random.Random,
    pools: dict,
    region: str,
) -> dict:
    """Generate a single order for a given date and region.

    Args:
        idx:        order index for stable_id generation
        event_date: the date of the order
        rng:        seeded random instance
        pools:      entity pools from _build_pools()
        region:     region to generate the order in
    """
    pool = pools[region]

    # Pick buyer and seller via Zipf
    buyer_idx = bisect.bisect_left(pool["buyer_zipf"], rng.random())
    buyer_idx = min(buyer_idx, len(pool["buyers"]) - 1)
    buyer = pool["buyers"][buyer_idx]

    seller_idx = bisect.bisect_left(pool["seller_zipf"], rng.random())
    seller_idx = min(seller_idx, len(pool["sellers"]) - 1)
    seller = pool["sellers"][seller_idx]

    # Pick number of items
    items_cum = build_cum_weights_uniform(ITEMS_PER_ORDER_DIST)
    n_items = bisect.bisect_left(items_cum, rng.random()) + 1
    n_items = min(n_items, 5)

    # Pick products from seller catalog (with replacement allowed)
    seller_products = pool["seller_products"][seller["seller_id"]]
    selected_products = [rng.choice(seller_products) for _ in range(n_items)]

    # Order-level shipping
    market = seller["country"]
    carrier = rng.choice(CARRIERS[market])
    shipped_days = rng.randint(0, 3)
    shipped_date = event_date + timedelta(days=shipped_days)
    delivery_days = rng.randint(*SHIPPING_PARAMS[market]["days_range"])
    delivered_date = shipped_date + timedelta(days=delivery_days)

    # Pick payment method
    payment_cum = build_cum_weights_uniform(PAYMENT_METHODS)
    payment_idx = bisect.bisect_left(payment_cum, rng.random())
    payment_method = list(PAYMENT_METHODS.keys())[min(payment_idx, 2)]

    # Generate timestamp
    timestamp = _generate_timestamp(event_date, rng)

    # Build items
    items = []
    for product in selected_products:
        subcategory = product["subcategory"]
        cost_range = SHIPPING_PARAMS[market]["cost_range"]
        mid_cost = (cost_range[0] + cost_range[1]) / 2

        # Shipping cost based on parcel size
        if product["parcel_size"] == "small":
            shipping_cost = round(rng.uniform(cost_range[0], mid_cost), 2)
        else:
            shipping_cost = round(rng.uniform(mid_cost, cost_range[1]), 2)

        # Fee rates snapshot at purchase time
        seller_tier = seller["seller_tier"]
        commission_rate = SELLER_TIERS[seller_tier]["commission_rate"]

        # Return status
        is_returned = rng.random() < RETURN_RATES.get(subcategory, 0.05)
        return_date = None
        return_reason = None
        if is_returned:
            return_days = rng.randint(1, 14)
            return_date = (delivered_date + timedelta(days=return_days)).isoformat()
            return_reasons_cum = build_cum_weights_uniform(RETURN_REASONS)
            reason_idx = bisect.bisect_left(return_reasons_cum, rng.random())
            return_reason = list(RETURN_REASONS.keys())[min(reason_idx, 4)]

        # Review status
        has_review = rng.random() < REVIEW_RATE
        review_date = None
        review_rating = None
        if has_review:
            review_days = rng.randint(1, 14)
            review_date = (delivered_date + timedelta(days=review_days)).isoformat()
            rating_weights = RATING_WEIGHTS_RETURNED if is_returned else RATING_WEIGHTS_NORMAL
            rating_cum = build_cum_weights_uniform(rating_weights)
            rating_idx = bisect.bisect_left(rating_cum, rng.random())
            review_rating = min(rating_idx + 1, 5)

        items.append(
            {
                "product_id": product["product_id"],
                "quantity": rng.randint(1, 3),
                "unit_price": product["price"],
                "shipping_cost": shipping_cost,
                "parcel_size": product["parcel_size"],
                "seller_tier": seller_tier,
                "buyer_protection_fee_rate": BUYER_PROTECTION_RATE,
                "seller_commission_rate": commission_rate,
                "payment_processing_rate": PAYMENT_PROCESSING_RATE,
                "is_returned": is_returned,
                "return_date": return_date,
                "return_reason": return_reason,
                "has_review": has_review,
                "review_date": review_date,
                "review_rating": review_rating,
            }
        )

    return {
        "event_id": stable_id(f"event-{event_date.isoformat()}", idx),
        "order_id": stable_id(f"order-{event_date.isoformat()}", idx),
        "order_date": event_date.isoformat(),
        "timestamp": timestamp,
        "buyer_id": buyer["buyer_id"],
        "seller_id": seller["seller_id"],
        "payment_method": payment_method,
        "carrier": carrier,
        "shipped_date": shipped_date.isoformat(),
        "delivered_date": delivered_date.isoformat(),
        "items": items,
    }


# ---------------------------------------------------------------------------
# Public interface
#
# generate_orders() is the function called by app.py. It computes the total
# number of orders for the day across all markets, builds the entity pools
# once, then generates each order deterministically.
# ---------------------------------------------------------------------------
def generate_orders(event_date: date, page: int = 1, page_size: int = 1000) -> dict:
    """Generate all orders for a given date, paginated.

    Args:
        event_date: the date to generate orders for
        page:       page number (1-indexed)
        page_size:  orders per page
    """
    if event_date < LAUNCH_DATE:
        return {
            "data": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
            "has_more": False,
            "event_date": event_date.isoformat(),
        }

    # Compute total orders per market for this date
    market_order_counts = {market: get_daily_order_count(event_date, market) for market in MARKETS}
    total_orders = sum(market_order_counts.values())

    # Build region order counts for weighted region selection
    region_counts = {}
    for market, count in market_order_counts.items():
        region = MARKETS[market]["region"]
        region_counts[region] = region_counts.get(region, 0) + count

    # Build entity pools once for the day
    pools = _build_pools(event_date)

    # Remove regions with no pools
    valid_regions = [r for r in region_counts if r in pools]
    region_weights = {r: region_counts[r] for r in valid_regions}
    region_cum = build_cum_weights_uniform(region_weights)
    region_list = list(region_weights.keys())

    # Seed per date for determinism
    date_seed = int(event_date.strftime("%Y%m%d"))
    rng = random.Random(BASE_SEED + date_seed)

    # Generate all orders for the day
    all_orders = []
    for idx in range(total_orders):
        region_idx = bisect.bisect_left(region_cum, rng.random())
        region_idx = min(region_idx, len(region_list) - 1)
        region = region_list[region_idx]

        order = _generate_order(idx, event_date, rng, pools, region)
        all_orders.append(order)

    result = paginate(all_orders, page, page_size)
    result["event_date"] = event_date.isoformat()
    return result
