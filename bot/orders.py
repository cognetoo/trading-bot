"""
Order placement logic.
Sits between the CLI layer and the raw BinanceClient.
Handles parameter mapping, response normalisation, and pretty-printing.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from bot.client import BinanceClient, BinanceAPIError
from bot.validators import validate_all

logger = logging.getLogger("trading_bot.orders")


class OrderResult:
    """Structured representation of a placed order response."""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.order_id: int = raw.get("orderId", 0)
        self.symbol: str = raw.get("symbol", "")
        self.side: str = raw.get("side", "")
        self.order_type: str = raw.get("type", "")
        self.status: str = raw.get("status", "")
        self.orig_qty: str = raw.get("origQty", "0")
        self.executed_qty: str = raw.get("executedQty", "0")
        self.avg_price: str = raw.get("avgPrice", "0")
        self.price: str = raw.get("price", "0")
        self.time_in_force: str = raw.get("timeInForce", "")
        self.client_order_id: str = raw.get("clientOrderId", "")
        self.update_time: int = raw.get("updateTime", 0)

    def is_filled(self) -> bool:
        return self.status == "FILLED"

    def summary_lines(self) -> list[str]:
        """Return a list of formatted summary lines for CLI output."""
        lines = [
            f"  Order ID      : {self.order_id}",
            f"  Client OID    : {self.client_order_id}",
            f"  Symbol        : {self.symbol}",
            f"  Side          : {self.side}",
            f"  Type          : {self.order_type}",
            f"  Status        : {self.status}",
            f"  Orig Qty      : {self.orig_qty}",
            f"  Executed Qty  : {self.executed_qty}",
        ]
        if self.order_type != "MARKET" and self.price and self.price != "0":
            lines.append(f"  Limit Price   : {self.price}")
        if self.avg_price and self.avg_price != "0":
            lines.append(f"  Avg Fill Price: {self.avg_price}")
        if self.time_in_force:
            lines.append(f"  Time In Force : {self.time_in_force}")
        return lines


class OrderManager:
    """
    High-level order manager.

    Validates input, maps to Binance API parameters, delegates to the client,
    and returns structured OrderResult objects.
    """

    def __init__(self, client: BinanceClient):
        self.client = client

    def _log_request_summary(self, params: dict) -> None:
        logger.info(
            "Placing order — symbol=%s  side=%s  type=%s  qty=%s  price=%s",
            params.get("symbol"),
            params.get("side"),
            params.get("type"),
            params.get("quantity"),
            params.get("price", "N/A"),
        )

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
    ) -> OrderResult:
        """Place a MARKET order."""
        validated = validate_all(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity,
        )

        api_params = {
            "symbol": validated["symbol"],
            "side": validated["side"],
            "type": "MARKET",
            "quantity": str(validated["quantity"]),
        }
        self._log_request_summary(api_params)

        raw = self.client.place_order(**api_params)
        result = OrderResult(raw)

        logger.info(
            "Market order placed — orderId=%s  status=%s  executedQty=%s  avgPrice=%s",
            result.order_id,
            result.status,
            result.executed_qty,
            result.avg_price,
        )
        return result

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        price: str | float | Decimal,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """Place a LIMIT order."""
        validated = validate_all(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=price,
        )

        api_params = {
            "symbol": validated["symbol"],
            "side": validated["side"],
            "type": "LIMIT",
            "quantity": str(validated["quantity"]),
            "price": str(validated["price"]),
            "timeInForce": time_in_force.upper(),
        }
        self._log_request_summary(api_params)

        raw = self.client.place_order(**api_params)
        result = OrderResult(raw)

        logger.info(
            "Limit order placed — orderId=%s  status=%s  price=%s  executedQty=%s",
            result.order_id,
            result.status,
            result.price,
            result.executed_qty,
        )
        return result

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        stop_price: str | float | Decimal,
    ) -> OrderResult:
        """
        Place a STOP_MARKET order (bonus feature).

        The order triggers a market exit/entry when price crosses stop_price.
        """
        validated = validate_all(
            symbol=symbol,
            side=side,
            order_type="STOP_MARKET",
            quantity=quantity,
            stop_price=stop_price,
        )

        api_params = {
            "symbol": validated["symbol"],
            "side": validated["side"],
            "type": "STOP_MARKET",
            "quantity": str(validated["quantity"]),
            "stopPrice": str(validated["stop_price"]),
        }
        self._log_request_summary(api_params)

        raw = self.client.place_order(**api_params)
        result = OrderResult(raw)

        logger.info(
            "Stop-Market order placed — orderId=%s  status=%s  stopPrice=%s",
            result.order_id,
            result.status,
            validated["stop_price"],
        )
        return result

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float | Decimal,
        price: Optional[str | float | Decimal] = None,
        stop_price: Optional[str | float | Decimal] = None,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """
        Unified order placement dispatcher.
        Routes to the appropriate typed method based on order_type.
        """
        order_type = order_type.strip().upper()

        if order_type == "MARKET":
            return self.place_market_order(symbol, side, quantity)
        elif order_type == "LIMIT":
            return self.place_limit_order(symbol, side, quantity, price, time_in_force)
        elif order_type == "STOP_MARKET":
            return self.place_stop_market_order(symbol, side, quantity, stop_price)
        else:
            raise ValueError(f"Unsupported order type: '{order_type}'")