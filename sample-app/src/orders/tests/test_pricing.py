from orders.pricing import calculate_order_total


def test_single_sku_no_discount():
    total = calculate_order_total([{"sku": "A", "price": 10, "qty": 2}], tax_rate=0.21)
    assert total == round(20 * 1.21, 2)


def test_duplicate_sku_applies_discount():
    items = [
        {"sku": "A", "price": 10, "qty": 1},
        {"sku": "A", "price": 10, "qty": 1},
    ]
    total = calculate_order_total(items, tax_rate=0.0)
    assert total == 19.0
