"""
Binance Futures Testnet REST client.
Handles authentication (HMAC-SHA256), request signing, and HTTP communication.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str, status_code: int = 0):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceClient:
    """
    Lightweight Binance Futures USDT-M Testnet client.

    Wraps raw REST calls with:
    - HMAC-SHA256 request signing
    - Automatic retry with exponential back-off
    - Structured logging of every request/response cycle
    - Consistent error mapping to BinanceAPIError
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = self._build_session()
        logger.info("BinanceClient initialised (base_url=%s)", self.base_url)

    # ── Session setup ────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    # ── Signing ──────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Append a HMAC-SHA256 signature to the parameter dict."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    @staticmethod
    def _timestamp() -> int:
        return int(time.time() * 1000)

    # ── Core HTTP helpers ────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request against the Binance REST API.

        Args:
            method:   HTTP verb (GET, POST, DELETE).
            endpoint: API path, e.g. '/fapi/v1/order'.
            params:   Query / body parameters.
            signed:   Whether to add timestamp + signature.

        Returns:
            Parsed JSON response dict.

        Raises:
            BinanceAPIError: On API-level errors.
            requests.RequestException: On network failures.
        """
        params = params or {}
        if signed:
            params["timestamp"] = self._timestamp()
            params = self._sign(params)

        url = f"{self.base_url}{endpoint}"

        logger.debug(
            "→ %s %s  params=%s",
            method.upper(),
            endpoint,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            elif method.upper() == "POST":
                response = self.session.post(url, data=params, timeout=DEFAULT_TIMEOUT)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params, timeout=DEFAULT_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.debug(
                "← %s %s  status=%d  body=%.500s",
                method.upper(),
                endpoint,
                response.status_code,
                response.text,
            )

            data = response.json()

        except requests.exceptions.Timeout:
            logger.error("Request timed out: %s %s", method.upper(), endpoint)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise
        except ValueError as exc:
            logger.error("Failed to decode JSON response: %s", exc)
            raise

        # Binance error responses carry a 'code' field (negative integers)
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(
                code=data.get("code", -1),
                message=data.get("msg", "Unknown error"),
                status_code=response.status_code,
            )

        return data

    # ── Public API methods ───────────────────────────────────────────────────

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch futures account information."""
        return self._request("GET", "/fapi/v2/account")

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch exchange info (trading rules, lot sizes, etc.)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params, signed=False)

    def place_order(self, **kwargs) -> Dict[str, Any]:
        """
        Place a futures order.

        Accepted kwargs mirror Binance /fapi/v1/order POST params:
          symbol, side, type, quantity, price, timeInForce, stopPrice, etc.
        """
        return self._request("POST", "/fapi/v1/order", params=dict(kwargs))

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Fetch all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by orderId."""
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
        )