from datetime import date

# ---------------------------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------------------------


BASE_SEED = 42
LAUNCH_DATE = date(2025, 1, 1)
NUM_SELLERS = 200
NUM_BUYERS = 2_000
NUM_PRODUCTS = 5_000
BASE_ORDERS_PER_DAY = 500
RETENTION_PERIOD_DAYS = 732

# ------------------------------------------------------------------------------------------------
# Markets & Regions
# ------------------------------------------------------------------------------------------------

REGIONS = {
    "america": ["US", "AR", "VE"],
    "europe": ["DE", "ES"],
}

MARKETS = {
    "US": {"region": "america", "locale": "en_US"},
    "AR": {"region": "america", "locale": "es_AR"},
    "VE": {"region": "america", "locale": "es_VE"},
    "DE": {"region": "europe", "locale": "de_DE"},
    "ES": {"region": "europe", "locale": "es_ES"},
}


MARKET_SIZE_MULT = {
    "US": 1.00,
    "DE": 0.60,
    "ES": 0.40,
    "AR": 0.25,
    "VE": 0.15,
}

# ------------------------------------------------------------------------------------------------
# Seller Tiers
# ------------------------------------------------------------------------------------------------

SELLER_TIERS = {
    "standard": {"commission_rate": 0.15, "distribution_weight": 60},
    "pro": {"commission_rate": 0.12, "distribution_weight": 30},
    "premium": {"commission_rate": 0.09, "distribution_weight": 10},
}

# ------------------------------------------------------------------------------------------------
# Platform Fees & Rates
# ------------------------------------------------------------------------------------------------

BUYER_PROTECTION_RATE = 0.05
PAYMENT_PROCESSING_RATE = 0.029
PAYMENT_PROCESSING_FIXED = 0.30
REVIEW_RATE = 0.30

# ------------------------------------------------------------------------------------------------
# Product Hierarchy
# ------------------------------------------------------------------------------------------------

PRODUCT_HIERARCHY = {
    "technology": {
        "electronics": ["phones", "computers", "gadgets"],
        "gaming_multimedia": ["consoles", "video_games", "cameras", "audio"],
    },
    "lifestyle": {
        "fashion": ["men", "women", "kids"],
        "beauty": ["fragrances", "makeup", "skincare"],
        "sports": ["baseball", "football_soccer", "basketball", "tennis"],
        "collectibles": ["pokemon", "magic", "sports_cards", "sports_gear"],
    },
}


# --------------------------------------------------------------------------------------------------
# Price Parameters (mu, sigma for log-normal distribution per subcategory)
#
# These are NOT prices. They are inputs to the log-normal formula:
#   price = e^(mu + sigma * random_normal())
#
# mu controls the center price: mu = ln(target_price)
#   e.g. mu=5.85 → e^5.85 ≈ $348, so phones cluster around ~$350
#
# sigma controls the spread of the distribution:
#   low sigma (0.35) = tight cluster, prices are predictable (e.g. consoles)
#   high sigma (1.20) = wide spread, most items cheap but rare ones expensive
#   (e.g. pokemon cards: most worth $3-$15, rare ones worth $500+)
#
# This mirrors real marketplace pricing better than a flat random range,
# which would generate just as many $1200 phones as $80 phones.
# --------------------------------------------------------------------------------------------------
SUBCATEGORY_PRICE_PARAMS = {
    # Technology
    "phones": (5.85, 0.65),  # center ~$350, range $80-$1200
    "computers": (6.40, 0.60),  # center ~$600, range $200-$2000
    "gadgets": (3.80, 0.70),  # center ~$45,  range $10-$150
    "consoles": (5.85, 0.35),  # center ~$350, range $150-$600
    "video_games": (3.70, 0.45),  # center ~$40,  range $10-$70
    "cameras": (5.99, 0.70),  # center ~$400, range $100-$1500
    "audio": (4.38, 0.70),  # center ~$80,  range $15-$400
    # Lifestyle
    "men": (3.55, 0.55),  # center ~$35,  range $8-$120
    "women": (3.69, 0.55),  # center ~$40,  range $8-$150
    "kids": (3.09, 0.50),  # center ~$22,  range $5-$60
    "fragrances": (4.00, 0.60),  # center ~$55,  range $15-$200
    "makeup": (3.00, 0.55),  # center ~$20,  range $5-$60
    "skincare": (3.33, 0.50),  # center ~$28,  range $8-$80
    "baseball": (3.40, 0.55),  # center ~$30,  range $8-$100
    "football_soccer": (3.55, 0.55),  # center ~$35,  range $10-$120
    "basketball": (3.69, 0.55),  # center ~$40,  range $10-$150
    "tennis": (3.55, 0.55),  # center ~$35,  range $10-$130
    "pokemon": (2.70, 1.20),  # center ~$15,  range $3-$500
    "magic": (2.48, 1.10),  # center ~$12,  range $3-$300
    "sports_cards": (2.89, 1.20),  # center ~$18,  range $3-$800
    "sports_gear": (4.61, 1.30),  # center ~$100, range $20-$2000
}


# -------------------------------------------------------------------------------------------------
# Shipping
#
# CARRIERS: each market uses its own regional carriers. A German order will
# ship via DHL, Hermes, or DPD — never FedEx. This mirrors real marketplace
# logistics where carriers are regional.
#
# SHIPPING_PARAMS: cost_range is the range of shipping costs in USD.
# days_range is the range of delivery days from shipped_date to delivered_date.
# Note that Venezuela and Argentina have higher costs and longer delivery
# times — this reflects real logistics challenges in those markets.
# ------------------------------------------------------------------------------------------------
CARRIERS = {
    "US": ["FedEx", "UPS", "USPS"],
    "DE": ["DHL", "Hermes", "DPD"],
    "ES": ["Correos", "SEUR", "MRW"],
    "AR": ["Andreani", "OCA", "Correo Argentino"],
    "VE": ["MRW", "Zoom", "Tealca"],
}

SHIPPING_PARAMS = {
    "US": {"cost_range": (4.99, 12.99), "days_range": (2, 7)},
    "DE": {"cost_range": (3.99, 9.99), "days_range": (1, 5)},
    "ES": {"cost_range": (3.99, 9.99), "days_range": (2, 6)},
    "AR": {"cost_range": (5.99, 15.99), "days_range": (3, 10)},
    "VE": {"cost_range": (6.99, 19.99), "days_range": (5, 15)},
}


# ---------------------------------------------------------------------------
# Parcel Size
#
# Each subcategory is assigned a parcel size: "small", "large", or "mixed".
# This determines shipping cost allocation per item:
#   small → lower end of SHIPPING_PARAMS cost range
#   large → upper end of SHIPPING_PARAMS cost range
#   mixed → 50/50 random assignment per product at product creation time
#
# This attribute enables shipping cost analysis by parcel type in dbt.
# ---------------------------------------------------------------------------
PARCEL_SIZE = {
    "phones": "small",
    "computers": "small",
    "gadgets": "mixed",
    "consoles": "large",
    "video_games": "small",
    "cameras": "mixed",
    "audio": "mixed",
    "men": "mixed",
    "women": "mixed",
    "kids": "small",
    "fragrances": "small",
    "makeup": "small",
    "skincare": "small",
    "baseball": "mixed",
    "football_soccer": "mixed",
    "basketball": "mixed",
    "tennis": "large",
    "pokemon": "small",
    "magic": "small",
    "sports_cards": "small",
    "sports_gear": "mixed",
}

# ---------------------------------------------------------------------------
# Return Rates
#
# Probability that a delivered item gets returned, per subcategory.
# Fashion has the highest return rates (mirrors real e-commerce: sizing issues).
# Collectibles have the lowest (buyers research carefully before purchasing).
# These rates are applied independently per item at order creation time.
# ---------------------------------------------------------------------------
RETURN_RATES = {
    "phones": 0.06,
    "computers": 0.06,
    "gadgets": 0.05,
    "consoles": 0.04,
    "video_games": 0.04,
    "cameras": 0.05,
    "audio": 0.04,
    "men": 0.12,
    "women": 0.18,
    "kids": 0.15,
    "fragrances": 0.03,
    "makeup": 0.04,
    "skincare": 0.03,
    "baseball": 0.06,
    "football_soccer": 0.06,
    "basketball": 0.06,
    "tennis": 0.05,
    "pokemon": 0.07,
    "magic": 0.08,
    "sports_cards": 0.04,
    "sports_gear": 0.12,
}

# ---------------------------------------------------------------------------
# Temporal Multipliers
#
# These multipliers are applied on top of BASE_ORDERS_PER_DAY to simulate
# realistic order volume patterns throughout the year.
#
# MONTH_MULT: monthly seasonality. November is the busiest month (Black
# Friday). February is the slowest (post-holiday slump, short month).
#
# DOW_MULT: day-of-week patterns. Friday peaks as people shop heading into
# the weekend. Monday is slowest.
#
# HOUR_WEIGHTS: 24 values, one per hour. Used to pick a realistic timestamp
# for each order. Peak at 19:00 (7pm), dead between 1-5am.
#
# GROWTH_START: the business launched at 30% capacity and grows linearly
# to 100% over 18 months. Applied as a multiplier based on days since launch.
# ---------------------------------------------------------------------------
MONTH_MULT = {
    1: 0.85,  # January:   post-holiday slump
    2: 0.80,  # February:  slowest month
    3: 0.95,  # March:     recovering
    4: 1.00,  # April:     baseline
    5: 1.00,  # May:       baseline
    6: 1.05,  # June:      slight summer bump
    7: 1.05,  # July:      slight summer bump
    8: 1.00,  # August:    baseline
    9: 1.05,  # September: back to school
    10: 1.10,  # October:   pre-holiday
    11: 1.40,  # November:  Black Friday, busiest
    12: 1.30,  # December:  holidays
}

DOW_MULT = {
    0: 0.85,  # Monday:    slowest
    1: 0.90,  # Tuesday
    2: 0.95,  # Wednesday
    3: 1.00,  # Thursday:  baseline
    4: 1.15,  # Friday:    peak
    5: 1.10,  # Saturday
    6: 1.05,  # Sunday
}

HOUR_WEIGHTS = [
    0.2,
    0.1,
    0.1,
    0.1,
    0.1,
    0.2,  # 0-5:   mostly dead
    0.4,
    0.6,
    0.8,
    1.0,
    1.1,
    1.2,  # 6-11:  morning ramp
    1.3,
    1.2,
    1.1,
    1.0,
    1.1,
    1.2,  # 12-17: lunch + afternoon
    1.5,
    1.8,
    1.6,
    1.3,
    0.9,
    0.5,  # 18-23: evening peak at 19:00
]

LAUNCH_DAILY_ORDERS = 250  # actual orders on day 1
ANNUAL_GROWTH_RATE = 0.25  # baseline 25% YoY growth
ANNUAL_GROWTH_VARIANCE = 0.20  # ±20% randomness per year, can produce degrowth

# ---------------------------------------------------------------------------
# Subcategory Seasonality
#
# Additional multipliers per subcategory for specific months.
# Only non-1.0 months are listed to keep this readable.
# These stack on top of MONTH_MULT — a console in November gets both
# the 1.40x November multiplier AND the 1.8x console multiplier.
# ---------------------------------------------------------------------------
SUBCATEGORY_SEASON = {
    "consoles": {11: 1.8, 12: 1.6},
    "video_games": {11: 1.8, 12: 1.6, 6: 1.2},
    "phones": {11: 1.5, 12: 1.3, 9: 1.2},
    "cameras": {11: 1.3, 12: 1.2},
    "women": {3: 1.2, 4: 1.3, 9: 1.3, 10: 1.2},
    "men": {6: 1.2, 12: 1.3},
    "kids": {8: 1.3, 12: 1.5},
    "fragrances": {2: 1.4, 5: 1.3, 12: 1.4},
    "skincare": {1: 1.3},
    "football_soccer": {8: 1.4, 1: 1.3},
    "baseball": {3: 1.4, 10: 1.3},
    "basketball": {10: 1.3, 3: 1.2},
    "tennis": {5: 1.3, 6: 1.3, 7: 1.2},
    "pokemon": {11: 1.5, 12: 1.8, 2: 1.2},
    "magic": {11: 1.4, 12: 1.7},
    "sports_cards": {2: 1.2, 7: 1.3},
    "sports_gear": {11: 1.6, 12: 1.5, 6: 1.2},
}

# ---------------------------------------------------------------------------
# Order Behavior
#
# ITEMS_PER_ORDER_DIST: probability distribution for how many items are
# in a single order. Most orders are 1-2 items, mimicking real marketplace
# behavior where buyers typically purchase one thing at a time.
#
# PAYMENT_METHODS: weighted distribution of payment methods.
# Credit card dominates but PayPal and bank transfer are common alternatives.
#
# RETURN_REASONS: weighted distribution of why items get returned.
# "wrong_size" is the most common reason, especially relevant for fashion.
#
# RATING_WEIGHTS_NORMAL: rating distribution for non-returned items.
# Skewed toward 4-5 stars — satisfied buyers are the majority.
#
# RATING_WEIGHTS_RETURNED: rating distribution for returned items.
# Skewed toward 1-2 stars — buyers who return items are usually unhappy.
# ---------------------------------------------------------------------------
ITEMS_PER_ORDER_DIST = {
    1: 0.55,  # 55% of orders have 1 item
    2: 0.25,  # 25% have 2 items
    3: 0.12,  # 12% have 3 items
    4: 0.05,  # 5%  have 4 items
    5: 0.03,  # 3%  have 5 items
}

PAYMENT_METHODS = {
    "credit_card": 0.60,
    "paypal": 0.25,
    "bank_transfer": 0.15,
}

RETURN_REASONS = {
    "wrong_size": 0.30,
    "not_as_described": 0.25,
    "changed_mind": 0.25,
    "defective": 0.15,
    "other": 0.05,
}

RATING_WEIGHTS_NORMAL = {
    1: 0.03,
    2: 0.05,
    3: 0.12,
    4: 0.35,
    5: 0.45,
}

RATING_WEIGHTS_RETURNED = {
    1: 0.50,
    2: 0.30,
    3: 0.12,
    4: 0.05,
    5: 0.03,
}


# ---------------------------------------------------------------------------
# Product Name Generation
#
# BRANDS: curated brand lists per subcategory. The generator picks a random
# brand and combines it with Faker-generated descriptors to produce realistic
# product titles. For example: "Samsung Galaxy X12 128GB" or "Nike Dri-FIT
# Running Shorts".
#
# Subcategories with empty brand lists use a different generation strategy:
#   video_games  → "{word} {word}: {subtitle}" e.g. "Cosmic Drift: Remastered"
#   pokemon      → "{set_name} {product_type}" e.g. "Obsidian Flames Booster Box"
#   magic        → "{set_name} {product_type}" e.g. "March of the Machine Draft Set"
#   sports_cards → "{year} {brand} {sport} {product_type}"
#   sports_gear  → "{athlete_adj} Signed {item}" e.g. "Game-Used Signed Jersey"
# ---------------------------------------------------------------------------
BRANDS = {
    "phones": ["Samsung", "Apple", "Xiaomi", "OnePlus", "Google", "Motorola", "Sony"],
    "computers": ["Dell", "HP", "Lenovo", "Asus", "Acer", "MSI", "Apple"],
    "gadgets": ["Anker", "Belkin", "Logitech", "Razer", "Tile", "Fitbit"],
    "consoles": ["Sony PlayStation", "Microsoft Xbox", "Nintendo"],
    "video_games": [],
    "cameras": ["Canon", "Nikon", "Sony", "Fujifilm", "GoPro", "DJI"],
    "audio": ["Sony", "Bose", "JBL", "Sennheiser", "Audio-Technica", "Beats"],
    "men": ["Nike", "Adidas", "Levi's", "H&M", "Zara", "Uniqlo", "Puma"],
    "women": ["Zara", "H&M", "Mango", "COS", "Nike", "Adidas", "Reformation"],
    "kids": ["H&M Kids", "Zara Kids", "Carter's", "Gap Kids", "Nike Kids"],
    "fragrances": ["Dior", "Chanel", "Tom Ford", "Versace", "Calvin Klein", "YSL"],
    "makeup": ["MAC", "Maybelline", "NYX", "Fenty Beauty", "Charlotte Tilbury"],
    "skincare": ["CeraVe", "The Ordinary", "La Roche-Posay", "Neutrogena", "Drunk Elephant"],
    "baseball": ["Rawlings", "Wilson", "Mizuno", "Louisville Slugger", "Marucci"],
    "football_soccer": ["Nike", "Adidas", "Puma", "New Balance", "Umbro"],
    "basketball": ["Nike", "Adidas", "Under Armour", "Jordan", "Spalding"],
    "tennis": ["Wilson", "Head", "Babolat", "Yonex", "Tecnifibre"],
    "pokemon": [],
    "magic": [],
    "sports_cards": [],
    "sports_gear": [],
}

# Pokemon set names for product name generation
POKEMON_SETS = [
    "Obsidian Flames",
    "Paldea Evolved",
    "Scarlet & Violet",
    "Paradox Rift",
    "Temporal Forces",
    "Twilight Masquerade",
    "Shrouded Fable",
]

POKEMON_PRODUCT_TYPES = [
    "Booster Box",
    "Elite Trainer Box",
    "Booster Pack",
    "V Promo Card",
    "ex Collection",
    "Tin",
    "Binder Collection",
]

# Magic: The Gathering set names
MAGIC_SETS = [
    "March of the Machine",
    "The Lord of the Rings",
    "Wilds of Eldraine",
    "Lost Caverns of Ixalan",
    "Murders at Karlov Manor",
    "Outlaws of Thunder Junction",
]

MAGIC_PRODUCT_TYPES = [
    "Draft Booster Box",
    "Set Booster Box",
    "Collector Booster Pack",
    "Commander Deck",
    "Bundle",
    "Jumpstart Pack",
]

# Sports cards brands and product types
SPORTS_CARDS_BRANDS = ["Topps", "Panini", "Upper Deck", "Bowman", "Donruss"]
SPORTS_CARDS_SPORTS = ["Baseball", "Basketball", "Football", "Soccer", "Hockey"]
SPORTS_CARDS_TYPES = ["Hobby Box", "Blaster Box", "Mega Box", "Hanger Pack", "Rookie Card"]

# Signed memorabilia descriptors
SPORTS_GEAR_ITEMS = [
    "Signed Jersey",
    "Signed Bat",
    "Signed Helmet",
    "Signed Basketball",
    "Signed Soccer Ball",
    "Signed Racquet",
    "Game-Used Signed Glove",
    "Signed Trading Card Lot",
    "Framed Signed Photo",
    "Signed Mini Helmet",
]

SPORTS_GEAR_CONDITIONS = ["COA Included", "Authenticated", "Framed", "Display Case Included"]


# ---------------------------------------------------------------------------
# Target KPI Ranges
#
# Used by validate_patterns.py in Phase 3 to verify that the generated data
# matches expected business patterns. These are not exact targets — they are
# sanity check ranges. If a metric falls outside these bounds, something is
# wrong with the generator logic or config.
#
# All volume metrics are per day. Revenue metrics are in USD.
# ---------------------------------------------------------------------------
TARGET_KPIS = {
    # Order volume
    "daily_orders_min": 300,
    "daily_orders_max": 900,
    # Revenue
    "avg_order_value_min": 35.0,
    "avg_order_value_max": 120.0,
    # Operations
    "avg_shipping_days_min": 1.5,
    "avg_shipping_days_max": 10.0,
    "overall_return_rate_min": 0.02,
    "overall_return_rate_max": 0.15,
    "avg_review_rating_min": 3.5,
    "avg_review_rating_max": 4.8,
    # Distribution checks
    "top_20pct_seller_volume_min": 0.60,  # top 20% sellers drive at least 60% of orders
    "top_20pct_seller_volume_max": 0.85,  # but not more than 85%
    "single_item_order_pct_min": 0.45,  # at least 45% of orders have 1 item
    "single_item_order_pct_max": 0.65,  # but not more than 65%
    # Seasonality checks
    "nov_vs_feb_ratio_min": 1.3,  # November must be at least 1.3x February
    "fri_vs_mon_ratio_min": 1.1,  # Friday must be at least 1.1x Monday
}
