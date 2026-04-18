from datetime import date, timedelta
from typing import Iterator
import os
import dlt
import requests


# NOTE: Reference data (sellers, buyers, products) uses write_disposition="replace"
# because the API is deterministic and historical snapshots are captured in orders
# (fee rates, seller_tier are snapshotted at purchase time).
#
# SCD Type 2 for sellers and buyers is handled in dbt using dbt snapshots.
# See dbt_project/snapshots/ — added in Phase 5.


API_BASE = os.environ.get("CORESCOUT_API_URL", "http://mock_api:8000")


def _paginate(endpoint: str, params: dict) -> Iterator[list]:
    """Paginate through all pages of an API endpoint.

    Yields one page of records at a time. Handles pagination automatically
    using the has_more field in the response.

    Args:
        endpoint: API endpoint path e.g. "/sellers"
        params:   query parameters to include in every request
    """
    page = 1
    while True:
        response = requests.get(
            f"{API_BASE}{endpoint}",
            params={**params, "page": page, "page_size": 1000},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        yield data["data"]

        if not data["has_more"]:
            break
        page += 1


@dlt.resource(
    name="sellers",
    write_disposition="merge",
    primary_key="seller_id",
)
def sellers_resource(as_of_date: date = None) -> Iterator[list]:
    """Load all sellers as of a given date.

    Args:
        as_of_date: date to load sellers as of. Defaults to yesterday.
    """
    if as_of_date is None:
        as_of_date = date.today() - timedelta(days=1)

    params = {"as_of_date": as_of_date.isoformat()}
    yield from _paginate("/sellers", params)


@dlt.resource(
    name="buyers",
    write_disposition="merge",
    primary_key="buyer_id",
)
def buyers_resource(as_of_date: date = None) -> Iterator[list]:
    """Load all buyers as of a given date.

    Args:
        as_of_date: date to load buyers as of. Defaults to yesterday.
    """
    if as_of_date is None:
        as_of_date = date.today() - timedelta(days=1)

    params = {"as_of_date": as_of_date.isoformat()}
    yield from _paginate("/buyers", params)


@dlt.resource(
    name="categories",
    write_disposition="merge",
    primary_key="category_id",
)
def categories_resource() -> Iterator[list]:
    """Load all categories. Categories are static so no as_of_date needed."""
    yield from _paginate("/categories", {})


@dlt.resource(
    name="products",
    write_disposition="merge",
    primary_key="product_id",
)
def products_resource(as_of_date: date = None) -> Iterator[list]:
    """Load all products as of a given date.

    Args:
        as_of_date: date to load products as of. Defaults to yesterday.
    """
    if as_of_date is None:
        as_of_date = date.today() - timedelta(days=1)

    params = {"as_of_date": as_of_date.isoformat()}
    yield from _paginate("/products", params)


@dlt.resource(
    name="orders",
    write_disposition="merge",
    primary_key="event_id",
    columns={"items": {"data_type": "complex"}},
)
def orders_resource(
    start_date: date,
    end_date: date = None,
) -> Iterator[list]:
    """Load orders day by day from start_date to end_date.

    Orders use merge disposition so re-running the pipeline for the same
    date range never creates duplicates. Each order has a stable event_id
    so dlt can identify and skip already-loaded records.

    Args:
        start_date: first date to load orders for
        end_date:   last date to load orders for. Defaults to yesterday.
    """
    if end_date is None:
        end_date = date.today() - timedelta(days=1)

    current = start_date
    while current <= end_date:
        params = {"event_date": current.isoformat()}
        for page in _paginate("/orders", params):
            yield page
        current += timedelta(days=1)


@dlt.source(name="corescout")
def corescout_source(
    start_date: date,
    end_date: date = None,
    as_of_date: date = None,
) -> list:
    """CoreScout data source combining all resources.

    Args:
        start_date: first date to load orders for
        end_date:   last date to load orders for. Defaults to yesterday.
        as_of_date: date to load reference data as of. Defaults to yesterday.
    """
    return [
        sellers_resource(as_of_date),
        buyers_resource(as_of_date),
        categories_resource(),
        products_resource(as_of_date),
        orders_resource(start_date, end_date),
    ]
