import bisect
import random
from datetime import date, timedelta

from faker import Faker

from config import (
    BASE_SEED,
    BUYER_GROWTH_RATE,
    BUYER_GROWTH_VARIANCE,
    INITIAL_BUYERS,
    INITIAL_PRODUCTS,
    INITIAL_SELLERS,
    LAUNCH_DATE,
    MARKETS,
    MARKET_SIZE_MULT,
    PARCEL_SIZE,
    PRODUCT_GROWTH_RATE,
    PRODUCT_GROWTH_VARIANCE,
    PRODUCT_HIERARCHY,
    SELLER_GROWTH_RATE,
    SELLER_GROWTH_VARIANCE,
    SELLER_TIERS,
)
from generators.helpers import (
    build_cum_weights_zipf,
    generate_price,
    generate_product_name,
    get_entity_count,
    paginate,
    stable_id,
)


# ---------------------------------------------------------------------------
# Sellers
#
# Sellers grow over time — new ones join as the business expands.
# The total count as of any date is computed by get_entity_count().
# Sellers are distributed across markets proportionally to MARKET_SIZE_MULT.
# Each seller has a tier drawn from SELLER_TIERS distribution weights.
# Faker locale matches the seller's country so business names feel authentic.
#
# All generation is deterministic — same as_of_date always returns
# the same sellers.
# ---------------------------------------------------------------------------
def _build_sellers(as_of_date: date) -> list[dict]:
    num_sellers = get_entity_count(
        as_of_date,
        INITIAL_SELLERS,
        SELLER_GROWTH_RATE,
        SELLER_GROWTH_VARIANCE,
        seed_offset=100,
    )

    rng = random.Random(BASE_SEED)

    # Distribute sellers across markets by size
    total_weight = sum(MARKET_SIZE_MULT.values())
    market_counts = {}
    allocated = 0
    markets = list(MARKET_SIZE_MULT.keys())

    for i, market in enumerate(markets):
        if i == len(markets) - 1:
            market_counts[market] = num_sellers - allocated
        else:
            count = round(num_sellers * MARKET_SIZE_MULT[market] / total_weight)
            market_counts[market] = count
            allocated += count

    # Build tier cumulative weights
    tier_names = list(SELLER_TIERS.keys())
    tier_weights = [SELLER_TIERS[t]["distribution_weight"] for t in tier_names]
    total_weight_tiers = sum(tier_weights)
    tier_cum = []
    running = 0.0
    for w in tier_weights:
        running += w / total_weight_tiers
        tier_cum.append(running)

    sellers = []
    idx = 0
    for market, count in market_counts.items():
        locale = MARKETS[market]["locale"]
        fake = Faker(locale)
        fake.seed_instance(BASE_SEED + idx)

        for _ in range(count):
            # Pick tier
            r = rng.random()
            tier = tier_names[next(i for i, c in enumerate(tier_cum) if r <= c)]

            # joined_date:
            joined_date = LAUNCH_DATE if idx > INITIAL_SELLERS else as_of_date

            sellers.append(
                {
                    "seller_id": stable_id("seller", idx),
                    "business_name": fake.company(),
                    "country": market,
                    "region": MARKETS[market]["region"],
                    "seller_tier": tier,
                    "joined_date": joined_date.isoformat(),
                }
            )
            idx += 1

    return sellers


def get_sellers(as_of_date: date, page: int = 1, page_size: int = 100) -> dict:
    sellers = _build_sellers(as_of_date)
    return paginate(sellers, page, page_size)


def get_seller_list(as_of_date: date) -> list[dict]:
    """Return full unpaginated seller list. Used internally by orders generator."""
    return _build_sellers(as_of_date)


# ---------------------------------------------------------------------------
# Buyers
#
# Buyers grow fastest of all entity types — consumer signups are high volume.
# Distributed across markets proportionally to MARKET_SIZE_MULT.
# Each buyer gets a signup_date spread across the period from launch to
# as_of_date, simulating organic user acquisition over time.
# ---------------------------------------------------------------------------
def _build_buyers(as_of_date: date) -> list[dict]:
    num_buyers = get_entity_count(
        as_of_date,
        INITIAL_BUYERS,
        BUYER_GROWTH_RATE,
        BUYER_GROWTH_VARIANCE,
        seed_offset=200,
    )

    rng = random.Random(BASE_SEED + 1)

    # Distribute buyers across markets by size
    total_weight = sum(MARKET_SIZE_MULT.values())
    market_counts = {}
    allocated = 0
    markets = list(MARKET_SIZE_MULT.keys())

    for i, market in enumerate(markets):
        if i == len(markets) - 1:
            market_counts[market] = num_buyers - allocated
        else:
            count = round(num_buyers * MARKET_SIZE_MULT[market] / total_weight)
            market_counts[market] = count
            allocated += count

    buyers = []
    idx = 0
    for market, count in market_counts.items():
        locale = MARKETS[market]["locale"]
        fake = Faker(locale)
        fake.seed_instance(BASE_SEED + 1 + idx)

        for _ in range(count):
            signup_date = LAUNCH_DATE if idx < INITIAL_BUYERS else as_of_date

            buyers.append(
                {
                    "buyer_id": stable_id("buyer", idx),
                    "username": fake.user_name(),
                    "email": fake.email(),
                    "country": market,
                    "region": MARKETS[market]["region"],
                    "signup_date": signup_date.isoformat(),
                }
            )
            idx += 1

    return buyers


def get_buyers(as_of_date: date, page: int = 1, page_size: int = 100) -> dict:
    buyers = _build_buyers(as_of_date)
    return paginate(buyers, page, page_size)


def get_buyer_list(as_of_date: date) -> list[dict]:
    """Return full unpaginated buyer list. Used internally by orders generator."""
    return _build_buyers(as_of_date)


# ---------------------------------------------------------------------------
# Categories
#
# Categories are static — the product hierarchy never changes over time.
# We flatten PRODUCT_HIERARCHY into individual rows with level indicators
# so dbt can easily join and slice by vertical, category, or subcategory.
# ---------------------------------------------------------------------------
def _build_categories() -> list[dict]:
    categories = []
    idx = 0

    for vertical, cat_dict in PRODUCT_HIERARCHY.items():
        categories.append(
            {
                "category_id": stable_id("cat", idx),
                "name": vertical,
                "parent_name": None,
                "level": 1,
                "vertical": vertical,
                "category": None,
                "subcategory": None,
            }
        )
        idx += 1

        for category, subcategories in cat_dict.items():
            categories.append(
                {
                    "category_id": stable_id("cat", idx),
                    "name": category,
                    "parent_name": vertical,
                    "level": 2,
                    "vertical": vertical,
                    "category": category,
                    "subcategory": None,
                }
            )
            idx += 1

            for subcategory in subcategories:
                categories.append(
                    {
                        "category_id": stable_id("cat", idx),
                        "name": subcategory,
                        "parent_name": category,
                        "level": 3,
                        "vertical": vertical,
                        "category": category,
                        "subcategory": subcategory,
                    }
                )
                idx += 1

    return categories


_CATEGORIES = _build_categories()


def get_categories(page: int = 1, page_size: int = 100) -> dict:
    return paginate(_CATEGORIES, page, page_size)


# ---------------------------------------------------------------------------
# Products
#
# Products grow over time as existing sellers list more items and new sellers
# join. Each product belongs to one seller and inherits that seller's market
# and region. Products are distributed across sellers using Zipf weighting
# so popular sellers have larger catalogs.
#
# parcel_size is determined by subcategory — "mixed" subcategories get
# a deterministic random assignment per product.
# ---------------------------------------------------------------------------
def _build_products(as_of_date: date) -> list[dict]:
    num_products = get_entity_count(
        as_of_date,
        INITIAL_PRODUCTS,
        PRODUCT_GROWTH_RATE,
        PRODUCT_GROWTH_VARIANCE,
        seed_offset=300,
    )

    sellers = _build_sellers(as_of_date)
    seller_zipf = build_cum_weights_zipf(len(sellers))

    rng = random.Random(BASE_SEED + 2)

    fake = Faker()
    fake.seed_instance(BASE_SEED + 2)

    subcategories = [
        (vertical, category, subcategory)
        for vertical, cat_dict in PRODUCT_HIERARCHY.items()
        for category, subs in cat_dict.items()
        for subcategory in subs
    ]

    products = []
    for idx in range(num_products):
        seller_idx = bisect.bisect_left(seller_zipf, rng.random())
        seller_idx = min(seller_idx, len(sellers) - 1)
        seller = sellers[seller_idx]

        vertical, category, subcategory = rng.choice(subcategories)

        raw_size = PARCEL_SIZE[subcategory]
        if raw_size == "mixed":
            parcel_size = rng.choice(["small", "large"])
        else:
            parcel_size = raw_size

        price = generate_price(subcategory, rng)
        title = generate_product_name(subcategory, rng, fake)

        seller_joined = date.fromisoformat(seller["joined_date"])
        listed_date = LAUNCH_DATE if idx < INITIAL_PRODUCTS else as_of_date

        products.append(
            {
                "product_id": stable_id("product", idx),
                "title": title,
                "seller_id": seller["seller_id"],
                "vertical": vertical,
                "category": category,
                "subcategory": subcategory,
                "price": price,
                "parcel_size": parcel_size,
                "market": seller["country"],
                "region": seller["region"],
                "listed_date": listed_date.isoformat(),
            }
        )

    return products


def get_products(as_of_date: date, page: int = 1, page_size: int = 100) -> dict:
    products = _build_products(as_of_date)
    return paginate(products, page, page_size)


def get_product_list(as_of_date: date) -> list[dict]:
    """Return full unpaginated product list. Used internally by orders generator."""
    return _build_products(as_of_date)
