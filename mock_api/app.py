from datetime import date, timedelta

from fastapi import FastAPI, Query

from generators.reference import (
    get_buyers,
    get_categories,
    get_products,
    get_sellers,
)

app = FastAPI(title="CoreScout Mock API")


# ---------------------------------------------------------------------------
# Health check
#
# Used by Docker Compose healthcheck to know when the API is ready.
# The pipeline container won't start until this returns 200.
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Reference endpoints
#
# All reference endpoints accept as_of_date so the pipeline can request
# the catalog as it existed on a specific date. This enables historical
# backfills to use the correct set of entities for each day.
#
# Default as_of_date is yesterday — the most recent complete day.
# ---------------------------------------------------------------------------
@app.get("/sellers")
def sellers(
    as_of_date: date = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
):
    if as_of_date is None:
        as_of_date = date.today() - timedelta(days=1)
    return get_sellers(as_of_date, page, page_size)


@app.get("/buyers")
def buyers(
    as_of_date: date = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
):
    if as_of_date is None:
        as_of_date = date.today() - timedelta(days=1)
    return get_buyers(as_of_date, page, page_size)


@app.get("/categories")
def categories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
):
    return get_categories(page, page_size)


@app.get("/products")
def products(
    as_of_date: date = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
):
    if as_of_date is None:
        as_of_date = date.today() - timedelta(days=1)
    return get_products(as_of_date, page, page_size)


# ---------------------------------------------------------------------------
# Orders endpoint
#
# Returns orders for a specific date. The date parameter is required —
# the pipeline always requests one day at a time.
# Generator is a stub for now — implemented in Phase 3.
# ---------------------------------------------------------------------------
@app.get("/orders")
def orders(
    event_date: date = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=1000, ge=1, le=5000),
):
    # Stub — returns empty until Phase 3
    return {
        "data": [],
        "page": page,
        "page_size": page_size,
        "total": 0,
        "total_pages": 0,
        "has_more": False,
        "event_date": event_date.isoformat(),
    }
