"""Inefficient nested-loop pricing used as the demo hotspot."""

from __future__ import annotations


def calculate_order_total(items: list[dict], tax_rate: float = 0.21) -> float:
    """Sum line items and apply a 5% discount when the same SKU appears more than once.

    The nested scan is intentional: the Code Agent should rewrite this to O(n).
    """
    total = 0.0
    for item in items:
        duplicate_count = 0
        for other in items:
            if other.get("sku") == item.get("sku"):
                duplicate_count += 1
        unit = float(item.get("price", 0))
        qty = int(item.get("qty", 1))
        discount = 0.05 if duplicate_count > 1 else 0.0
        total += unit * qty * (1.0 - discount)
    return round(total * (1.0 + tax_rate), 2)
