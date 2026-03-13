"""
Input validation for order parameters.
All validators raise ValueError with clear, human-readable messages.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

SUPPORTED_SIDES = {"BUY", "SELL"}
SUPPORTED_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}

# Rough sanity bounds — not meant to replace exchange filters
MIN_QUANTITY = Decimal("0.001")
MAX_QUANTITY = Decimal("1_000_000")


def validate_symbol(symbol: str) -> str:
    """Normalize and validate a trading symbol."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    if len(symbol) < 3 or len(symbol) > 20:
        raise ValueError(f"Symbol '{symbol}' looks invalid (expected 3–20 chars, e.g. BTCUSDT).")
    if not symbol.isalnum():
        raise ValueError(f"Symbol '{symbol}' must be alphanumeric (e.g. BTCUSDT, ETHUSDT).")
    return symbol


def validate_side(side: str) -> str:
    """Validate and normalize order side."""
    side = side.strip().upper()
    if side not in SUPPORTED_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(SUPPORTED_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate and normalize order type."""
    order_type = order_type.strip().upper()
    if order_type not in SUPPORTED_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    """Parse and validate order quantity."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")

    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    if qty < MIN_QUANTITY:
        raise ValueError(f"Quantity {qty} is below the minimum allowed ({MIN_QUANTITY}).")
    if qty > MAX_QUANTITY:
        raise ValueError(f"Quantity {qty} exceeds the maximum allowed ({MAX_QUANTITY}).")
    return qty


def validate_price(price: str | float | Decimal | None, order_type: str) -> Optional[Decimal]:
    """
    Validate price field.

    - LIMIT orders require a positive price.
    - MARKET orders must NOT supply a price.
    """
    order_type = order_type.strip().upper()

    if order_type == "MARKET":
        if price is not None:
            raise ValueError("Price should not be provided for MARKET orders.")
        return None

    # LIMIT or STOP_MARKET require price
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")

    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")

    return p


def validate_stop_price(
    stop_price: str | float | Decimal | None,
    order_type: str,
) -> Optional[Decimal]:
    """Validate stop price for STOP_MARKET orders."""
    order_type = order_type.strip().upper()

    if order_type != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValueError("stopPrice is required for STOP_MARKET orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")

    if sp <= 0:
        raise ValueError(f"Stop price must be positive, got {sp}.")

    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float | Decimal,
    price: str | float | Decimal | None = None,
    stop_price: str | float | Decimal | None = None,
) -> dict:
    """
    Run all validations and return a clean, normalized parameter dict.

    Raises ValueError on the first validation failure encountered.
    """
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)
    clean_stop = validate_stop_price(stop_price, clean_type)

    result: dict = {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_qty,
    }
    if clean_price is not None:
        result["price"] = clean_price
    if clean_stop is not None:
        result["stop_price"] = clean_stop

    return result