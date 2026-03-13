"""
cli.py — Trading Bot CLI Entry Point
=====================================
Place Binance Futures Testnet orders from the command line.

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Limit SELL
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 2000

# Stop-Market BUY (bonus)
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 65000

# Override log level
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG

Environment variables
---------------------
BINANCE_API_KEY     — testnet API key
BINANCE_API_SECRET  — testnet API secret
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from typing import Optional

# ── Bootstrap path so `bot` package is importable when run from project root ─
sys.path.insert(0, os.path.dirname(__file__))

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import OrderManager

# ── ANSI helpers ─────────────────────────────────────────────────────────────
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"


def _banner() -> None:
    print(
        f"{CYAN}{BOLD}"
        "╔══════════════════════════════════════════════╗\n"
        "║   Binance Futures Testnet — Trading Bot CLI  ║\n"
        "╚══════════════════════════════════════════════╝"
        f"{RESET}"
    )


def _section(title: str) -> None:
    print(f"\n{BOLD}{YELLOW}▶ {title}{RESET}")
    print(f"{DIM}{'─' * 48}{RESET}")


def _success(msg: str) -> None:
    print(f"\n{GREEN}{BOLD}✓ {msg}{RESET}")


def _failure(msg: str) -> None:
    print(f"\n{RED}{BOLD}✗ {msg}{RESET}")


def _print_request_summary(args: argparse.Namespace) -> None:
    _section("Order Request")
    print(f"  Symbol       : {args.symbol.upper()}")
    print(f"  Side         : {args.side.upper()}")
    print(f"  Type         : {args.type.upper()}")
    print(f"  Quantity     : {args.quantity}")
    if args.price:
        print(f"  Limit Price  : {args.price}")
    if args.stop_price:
        print(f"  Stop Price   : {args.stop_price}")
    if args.time_in_force:
        print(f"  Time-in-Force: {args.time_in_force}")


def _print_order_result(result) -> None:
    _section("Order Response")
    for line in result.summary_lines():
        print(line)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Binance Futures Testnet — CLI Order Placer
            ==========================================
            Place MARKET, LIMIT, and STOP_MARKET orders on the
            Binance Futures USDT-M Testnet.

            API credentials are read from environment variables:
              BINANCE_API_KEY
              BINANCE_API_SECRET
            """
        ),
        epilog=textwrap.dedent(
            """\
            Examples:
              # Market BUY 0.01 BTC
              python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

              # Limit SELL 0.05 ETH at $2,000
              python cli.py --symbol ETHUSDT --side SELL --type LIMIT \\
                            --quantity 0.05 --price 2000

              # Stop-Market BUY (triggers at $65,000)
              python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET \\
                            --quantity 0.01 --stop-price 65000
            """
        ),
    )

    # ── Required order params ────────────────────────────────────────────────
    order_grp = parser.add_argument_group("Order Parameters")
    order_grp.add_argument(
        "--symbol", required=True,
        help="Trading pair symbol, e.g. BTCUSDT",
    )
    order_grp.add_argument(
        "--side", required=True, choices=["BUY", "SELL", "buy", "sell"],
        metavar="BUY|SELL",
        help="Order direction: BUY or SELL",
    )
    order_grp.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET",
                 "market", "limit", "stop_market"],
        metavar="MARKET|LIMIT|STOP_MARKET",
        dest="type",
        help="Order type",
    )
    order_grp.add_argument(
        "--quantity", required=True, type=float,
        help="Order quantity (base asset units)",
    )

    # ── Optional order params ─────────────────────────────────────────────────
    opt_grp = parser.add_argument_group("Optional Parameters")
    opt_grp.add_argument(
        "--price", type=float, default=None,
        help="Limit price (required for LIMIT orders)",
    )
    opt_grp.add_argument(
        "--stop-price", type=float, default=None, dest="stop_price",
        help="Stop trigger price (required for STOP_MARKET orders)",
    )
    opt_grp.add_argument(
        "--time-in-force", default="GTC", dest="time_in_force",
        choices=["GTC", "IOC", "FOK", "GTX"],
        help="Time-in-force for LIMIT orders (default: GTC)",
    )

    # ── Config ────────────────────────────────────────────────────────────────
    cfg_grp = parser.add_argument_group("Configuration")
    cfg_grp.add_argument(
        "--api-key", default=None,
        help="Binance API key (overrides BINANCE_API_KEY env var)",
    )
    cfg_grp.add_argument(
        "--api-secret", default=None,
        help="Binance API secret (overrides BINANCE_API_SECRET env var)",
    )
    cfg_grp.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )

    return parser


def resolve_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve API key/secret from args → env vars."""
    api_key = args.api_key or os.environ.get("BINANCE_API_KEY", "")
    api_secret = args.api_secret or os.environ.get("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        _failure(
            "API credentials not found.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
            "  or pass --api-key / --api-secret flags."
        )
        sys.exit(1)

    return api_key, api_secret


def main(argv: Optional[list] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(args.log_level)

    _banner()

    # ── Resolve credentials ───────────────────────────────────────────────────
    api_key, api_secret = resolve_credentials(args)

    # ── Print what we're about to do ─────────────────────────────────────────
    _print_request_summary(args)

    # ── Initialise client & manager ───────────────────────────────────────────
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        manager = OrderManager(client)
    except Exception as exc:
        logger.error("Failed to initialise trading client: %s", exc)
        _failure(f"Initialisation error: {exc}")
        sys.exit(1)

    # ── Place order ───────────────────────────────────────────────────────────
    try:
        result = manager.place_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )

        _print_order_result(result)
        _success(f"Order placed successfully! (orderId={result.order_id}  status={result.status})")

    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        _failure(f"Invalid input: {exc}")
        sys.exit(2)

    except BinanceAPIError as exc:
        logger.error(
            "Binance API error — code=%s  msg=%s  http_status=%s",
            exc.code,
            exc.message,
            exc.status_code,
        )
        _failure(f"Binance API Error [{exc.code}]: {exc.message}")
        sys.exit(3)

    except Exception as exc:
        logger.exception("Unexpected error during order placement")
        _failure(f"Unexpected error: {exc}")
        sys.exit(4)


if __name__ == "__main__":
    main()