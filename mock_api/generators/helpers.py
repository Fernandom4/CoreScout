import bisect
import hashlib
import math
import random
from datetime import date
from config import (
    ANNUAL_GROWTH_RATE,
    ANNUAL_GROWTH_VARIANCE,
    BASE_SEED,
    BRANDS,
    DOW_MULT,
    LAUNCH_DATE,
    LAUNCH_DAILY_ORDERS,
    MAGIC_PRODUCT_TYPES,
    MAGIC_SETS,
    MARKET_SIZE_MULT,
    MONTH_MULT,
    POKEMON_PRODUCT_TYPES,
    POKEMON_SETS,
    SPORTS_CARDS_BRANDS,
    SPORTS_CARDS_SPORTS,
    SPORTS_CARDS_TYPES,
    SPORTS_GEAR_CONDITIONS,
    SPORTS_GEAR_ITEMS,
    SUBCATEGORY_PRICE_PARAMS,
    SUBCATEGORY_SEASON,
)


# ---------------------------------------------------------------------------
# API Pagination
#
# All API endpoints return paginated responses. This function takes a full
# list of items and returns the slice corresponding to the requested page.
# It also returns metadata so the caller knows if there are more pages.
# ---------------------------------------------------------------------------
def paginate(
    items: list,
    page: int,
    page_size: int,
) -> dict:
    """Slice a list into a paginated response.

    Args:
        items:     full list of items to paginate
        page:      1-indexed page number
        page_size: number of items per page

    Returns:
        dict with keys: data, page, page_size, total, total_pages, has_more
    """
    total = len(items)
    total_pages = math.ceil(total / page_size)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "data": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


# ---------------------------------------------------------------------------
# Deterministic ID generation
#
# We need IDs that are stable across runs — the same seller #42 should always
# get the same seller_id. We achieve this by hashing a prefix + index instead
# of using random UUIDs. This is what makes the entire dataset deterministic.
# ---------------------------------------------------------------------------


def stable_id(prefix: str, index: int) -> str:
    """Generate a deterministic UUID-like ID from a prefix and an Index.

    Example: stable_id('seller',42) always return the same string
    """
    raw = f"{prefix}-{index}"
    return hashlib.md5(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Weighted random selection
#
# Many distributions in the real world follow a Zipf (power law) pattern:
# a small number of items account for the majority of activity. Examples:
#   - Top 20% of sellers generate ~70-80% of orders
#   - A few products are purchased far more than others
#   - A few buyers shop far more frequently than most
#
# We model this with cumulative weight arrays + binary search for O(log n)
# random selection. Building the weights once at startup and reusing them
# is much faster than recomputing on every selection.
# ---------------------------------------------------------------------------
def build_cum_weights_zipf(n: int, alpha: float = 1.0) -> list[float]:
    """Build cumulative weights following a Zipf distribution.

    The first item gets weight 1.0, second gets 1/2^alpha,
    third gets 1/3^alpha, etc. Higher alpha = more skewed toward
    the top items.

    Args:
        n:     number of items
        alpha: skew parameter. 1.0 is standard Zipf.
    """
    weights = [1.0 / (i**alpha) for i in range(1, n + 1)]
    total = sum(weights)
    cumulative = []
    running = 0.0
    for w in weights:
        running += w / total
        cumulative.append(running)
    return cumulative


def build_cum_weights_uniform(raw: dict) -> list[float]:
    """Build cumulative weights from a dict of {value: weight}.

    Used for distributions like ITEMS_PER_ORDER_DIST or PAYMENT_METHODS
    where we define explicit probabilities per value.

    Args:
        raw: dict mapping values to their relative weights
    """
    total = sum(raw.values())
    cumulative = []
    running = 0.0
    for w in raw.values():
        running += w / total
        cumulative.append(running)
    return cumulative


def weighted_idx(rng: random.Random, cum_weights: list[float]) -> int:
    """Pick a random index using cumulative weights via binary search.

    Returns the index of the selected item. O(log n) via bisect.

    Args:
        rng:         a seeded random.Random instance
        cum_weights: cumulative weight array from build_cum_weights_*
    """
    return bisect.bisect_left(cum_weights, rng.random())


# ---------------------------------------------------------------------------
# Growth curve
#
# CoreScout launched at LAUNCH_DAILY_ORDERS on day 1 and grows year over
# year at a base rate of ANNUAL_GROWTH_RATE. Each year gets its own random
# growth modifier seeded deterministically, so some years the business grows
# fast, some years it shrinks. This produces a realistic long-term trajectory
# without an artificial ceiling or a smooth ramp.
#
# Example trajectory:
#   2025: +30% (strong launch year)
#   2026: +40% (accelerating growth)
#   2027: -5%  (tough market year)
#   2028: +20% (recovery)
# ---------------------------------------------------------------------------
def get_growth_multiplier(d: date) -> float:
    """Return the order volume multiplier for a given date.

    Compounds annual growth from LAUNCH_DATE with per-year randomness.
    Each year's growth rate is seeded deterministically so results are
    always reproducible.

    Args:
        d: the date to compute the multiplier for

    Returns:
        multiplier to apply to LAUNCH_DAILY_ORDERS for the given date
    """
    years_since_launch = (d.year - LAUNCH_DATE.year) + (d.month - LAUNCH_DATE.month) / 12

    if years_since_launch <= 0:
        return 1.0

    # Compound growth year by year, each with its own random modifier
    multiplier = 1.0
    full_years = int(years_since_launch)

    for year_offset in range(full_years + 1):
        # Seed per year so each year's modifier is deterministic but independent
        year_rng = random.Random(BASE_SEED + year_offset)
        variance = year_rng.uniform(-ANNUAL_GROWTH_VARIANCE, ANNUAL_GROWTH_VARIANCE)
        year_growth = 1.0 + ANNUAL_GROWTH_RATE + variance

        if year_offset < full_years:
            # Full year — apply completely
            multiplier *= year_growth
        else:
            # Partial year — apply proportionally
            partial = years_since_launch - full_years
            multiplier *= 1.0 + (year_growth - 1.0) * partial

    return multiplier


# ---------------------------------------------------------------------------
# Daily order count
#
# Combines all multipliers to produce the expected order count for a given
# date and market. This is the single function the order generator calls
# to know how many orders to produce.
# ---------------------------------------------------------------------------
def get_daily_order_count(d: date, market: str) -> int:
    """Return the expected number of orders for a given date and market.

    Combines: launch volume, growth curve, monthly seasonality,
    day-of-week pattern, and market size.

    Args:
        d:      the date
        market: market code e.g. "US", "DE"
    """

    base = LAUNCH_DAILY_ORDERS
    growth = get_growth_multiplier(d)
    monthly = MONTH_MULT[d.month]
    daily = DOW_MULT[d.weekday()]
    market_mult = MARKET_SIZE_MULT[market]

    return max(1, round(base * growth * monthly * daily * market_mult))


# ---------------------------------------------------------------------------
# Subcategory seasonal multiplier
# ---------------------------------------------------------------------------
def get_subcategory_multiplier(subcategory: str, month: int) -> float:
    """Return the seasonal multiplier for a subcategory in a given month.

    Returns 1.0 if no specific multiplier is defined for that month.

    Args:
        subcategory: e.g. "phones", "pokemon"
        month:       integer month 1-12
    """

    return SUBCATEGORY_SEASON.get(subcategory, {}).get(month, 1.0)


# ---------------------------------------------------------------------------
# Price generation
# ---------------------------------------------------------------------------
def generate_price(subcategory: str, rng: random.Random) -> float:
    """Generate a realistic price for a product using log-normal distribution.

    Args:
        subcategory: e.g. "phones", "pokemon"
        rng:         seeded random instance for determinism
    """

    mu, sigma = SUBCATEGORY_PRICE_PARAMS[subcategory]
    price = rng.lognormvariate(mu, sigma)
    return round(price, 2)


# ---------------------------------------------------------------------------
# Product name generation
#
# Generates realistic product titles per subcategory using brand lists and
# Faker. Subcategories with empty BRANDS lists use custom generation logic
# that mirrors how those products are actually named in real marketplaces.
# ---------------------------------------------------------------------------
def generate_product_name(subcategory: str, rng: random.Random, faker_instance) -> str:
    """Generate a realistic product title for a given subcategory.

    Args:
        subcategory:     e.g. "phones", "pokemon"
        rng:             seeded random instance for determinism
        faker_instance:  a Faker instance for generating descriptors
    """
    if subcategory == "video_games":
        word1 = faker_instance.word().capitalize()
        word2 = faker_instance.word().capitalize()
        subtitle = faker_instance.catch_phrase().title()
        return f"{word1} {word2}: {subtitle}"

    elif subcategory == "pokemon":
        set_name = rng.choice(POKEMON_SETS)
        product_type = rng.choice(POKEMON_PRODUCT_TYPES)
        return f"{set_name} {product_type}"

    elif subcategory == "magic":
        set_name = rng.choice(MAGIC_SETS)
        product_type = rng.choice(MAGIC_PRODUCT_TYPES)
        return f"{set_name} {product_type}"

    elif subcategory == "sports_cards":
        year = rng.randint(2020, 2025)
        brand = rng.choice(SPORTS_CARDS_BRANDS)
        sport = rng.choice(SPORTS_CARDS_SPORTS)
        product_type = rng.choice(SPORTS_CARDS_TYPES)
        return f"{year} {brand} {sport} {product_type}"

    elif subcategory == "sports_gear":
        item = rng.choice(SPORTS_GEAR_ITEMS)
        condition = rng.choice(SPORTS_GEAR_CONDITIONS)
        return f"{item} - {condition}"

    else:
        # Standard brand + faker descriptor
        brands = BRANDS[subcategory]
        brand = rng.choice(brands)
        descriptor = faker_instance.word().capitalize()
        return f"{brand} {descriptor}"
