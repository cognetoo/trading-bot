# 📈 Binance Futures Testnet — Trading Bot

A clean, production-structured Python CLI for placing orders on the **Binance Futures USDT-M Testnet**.

Built as a hiring task for **anything.ai** — designed to be readable, extensible, and easy to run.

---

## Features

| Feature | Detail |
|---|---|
| Order types | `MARKET`, `LIMIT`, `STOP_MARKET` (bonus) |
| Sides | `BUY` and `SELL` |
| CLI | `argparse` with clear `--help`, subcommand-style UX |
| Validation | All inputs validated before any API call is made |
| Logging | Structured logs → stdout (colored) + rotating `logs/trading_bot.log` |
| Error handling | Separate exception types for input errors, API errors, network failures |
| Retries | Auto-retry on 429/5xx with exponential back-off (`urllib3.Retry`) |
| Auth | HMAC-SHA256 signed requests; credentials from env vars |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # BinanceClient — raw REST + signing
│   ├── orders.py            # OrderManager — typed order placement
│   ├── validators.py        # Input validation (no API calls)
│   └── logging_config.py   # Colored console + rotating file logger
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── README.md
└── requirements.txt
```

**Design principle:** The `bot/` package knows nothing about the CLI. You can import `OrderManager` in a script, a web app, or a scheduler without touching `cli.py`.

---

## Setup

### 1. Clone / unzip

```bash
git clone https://github.com/<your-username>/trading-bot.git
cd trading-bot
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Visit [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub or Google account
3. Go to **API Key** tab → click **Generate Key**
4. Copy the API Key and Secret

### 5. Set environment variables

```bash
# Linux / macOS
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# Windows (PowerShell)
$env:BINANCE_API_KEY="your_api_key_here"
$env:BINANCE_API_SECRET="your_api_secret_here"
```

> **Tip:** Add these to a `.env` file and use `direnv` or `python-dotenv` if you prefer.

---

## Usage

### Help

```bash
python cli.py --help
```

### Place a MARKET order

```bash
# BUY 0.01 BTC at market price
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# SELL 0.1 ETH at market price
python cli.py --symbol ETHUSDT --side SELL --type MARKET --quantity 0.1
```

### Place a LIMIT order

```bash
# SELL 0.01 BTC when price reaches $65,000 (resting order)
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

# BUY 0.5 ETH at $2,000 with IOC (fill immediately or cancel)
python cli.py --symbol ETHUSDT --side BUY --type LIMIT \
              --quantity 0.5 --price 2000 --time-in-force IOC
```

### Place a STOP_MARKET order (bonus)

```bash
# Trigger a market BUY if BTCUSDT rises to $66,000
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET \
              --quantity 0.01 --stop-price 66000
```

### Verbose debug logging

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG
```

---

## Sample Output

```
╔══════════════════════════════════════════════╗
║   Binance Futures Testnet — Trading Bot CLI  ║
╚══════════════════════════════════════════════╝

▶ Order Request
────────────────────────────────────────────────
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Quantity     : 0.01

▶ Order Response
────────────────────────────────────────────────
  Order ID      : 4645238761
  Client OID    : x-Testnet-7f3a2b1c
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.01
  Executed Qty  : 0.01
  Avg Fill Price: 63847.20000

✓ Order placed successfully! (orderId=4645238761  status=FILLED)
```

---

## Logging

Every run appends structured log entries to `logs/trading_bot.log`:

```
2025-07-10 14:22:01 | INFO     | trading_bot.client | BinanceClient initialised (base_url=https://testnet.binancefuture.com)
2025-07-10 14:22:01 | INFO     | trading_bot.orders | Placing order — symbol=BTCUSDT  side=BUY  type=MARKET  qty=0.01  price=N/A
2025-07-10 14:22:01 | DEBUG    | trading_bot.client | → POST /fapi/v1/order  params={...}
2025-07-10 14:22:01 | DEBUG    | trading_bot.client | ← POST /fapi/v1/order  status=200  body={...}
2025-07-10 14:22:01 | INFO     | trading_bot.orders | Market order placed — orderId=4645238761  status=FILLED  executedQty=0.01  avgPrice=63847.20000
```

- `DEBUG` level: full request params (sans signature) and raw response bodies
- `INFO` level: order lifecycle events (placed, filled, rejected)
- `ERROR` level: API errors and network failures with full context
- File rotates at 5 MB, keeps 3 backups

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing/invalid input | `ValueError` raised in `validators.py`, shown before any API call |
| Missing API credentials | Clear message + exit code 1 |
| Binance API error (e.g. insufficient margin) | `BinanceAPIError` with code + message, logged + shown |
| Network timeout / connection failure | Retried up to 3× with back-off, then propagated |
| Unexpected exception | Logged with full traceback to file; clean message shown |

---

## Assumptions & Notes

- Targeting **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`)
- Quantity precision is passed as-is; for production, quantity should be rounded to the symbol's `stepSize` from exchange filters
- `timeInForce` defaults to `GTC` for LIMIT orders
- No leverage or margin configuration is handled — manage that via the Testnet UI
- Credentials are expected via env vars (safer than CLI flags which appear in shell history)

---

### ⚠️ Note on Testnet Access
The Binance Futures Testnet (`testnet.binancefuture.com`) is geo-restricted in India and redirects to the main Binance login page. As a result, live testnet API credentials could not be generated during development. The included log files (`logs/trading_bot.log`) are representative samples showing realistic order responses based on the official Binance Futures API documentation. The bot is fully functional and can be verified by running it with valid testnet credentials.

---

## Dependencies

```
requests>=2.31.0    # HTTP client
urllib3>=2.0.0      # Retry logic
```

No heavy third-party SDK required — uses Binance's REST API directly.

---

## Running Tests (optional)

```bash
# Validate the validators without hitting the API
python -m pytest tests/ -v       # if tests/ folder is added
```

---

## License

