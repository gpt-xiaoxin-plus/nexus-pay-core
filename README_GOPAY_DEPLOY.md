# GoPay Protocol Deploy

Pure-API GoPay registration + Midtrans payment pipeline. No browser, no ADB, no emulator.

## Protocol vNext

The integrated protocol package is documented in
[`PROTOCOL_VNEXT_GUIDE.md`](PROTOCOL_VNEXT_GUIDE.md). The complete Chinese
runbook is [`GOPAY_COMPLETE_RUNBOOK.md`](GOPAY_COMPLETE_RUNBOOK.md). It combines
the local project, four reference repositories, and the real-device capture at
`/Users/username/Downloads/Telegram Lite/真机3`.

```bash
# Rebuild everything, run offline validation, and run tests
./verify_ready.sh

# Rebuild the full vNext protocol package and run offline validation
./refresh_protocol_vnext.sh

# Inspect current vNext status
.venv/bin/opai protocol status --profile config/protocol_vnext.json
```

## Quick Start

### macOS/Linux local setup

```bash
# Create .venv with Python 3.11+ and install the package
./setup.sh

# Verify the offline full-flow harness
./run_offline.sh

# Optional: start the local Payment Inbox UI
./start_inbox.sh
# open http://127.0.0.1:19080

# Web console mode: subscription tasks, GoPay accounts, manual registration,
# and browser OTP input are all available at the same URL.

# Live worker: first set OPAI_HEROSMS_API_KEY or OPAI_HEROSMS_API_KEY_FILE
# in config/runtime.env, then run:
./start_worker.sh --workers 3 --pin 147258

# Manual phone/OTP registration mode, no Hero-SMS API key needed:
./start_manual_register.sh --phone 085142447768 --pin 147258
```

```bash
# Set Hero-SMS API key
set OPAI_HEROSMS_API_KEY=your_key_here

# Run 3 parallel workers (register + wait for balance + pay)
./start_worker.bat --workers 3 --pin 147258

# Or via Python directly
cd app
python -m opai worker run --workers 3 --pin 147258

# Dry run (register one account only, no payment)
python -m opai worker dry-run --pin 147258

# Test a single Midtrans payment
python -m opai pay "https://app.midtrans.com/snap/v4/redirection/<snap_id>" --phone 85142447768 --pin 147258

# Web UI can generate a Midtrans URL from a local OpenAI AT input
./start_inbox.sh
# Open http://127.0.0.1:19080 -> 支付任务 -> 用 AT 生成 Midtrans 链接

# Check balance of a saved account
python -m opai worker balance +6285142447768

# Resume from existing accounts (skip registration)
python -m opai worker run --resume +6285142447768 +6281234567890
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPAI_HEROSMS_API_KEY` | (required) | Hero-SMS API key for phone rental |
| `OPAI_HEROSMS_API_KEY_FILE` | | Path to file containing API key |
| `OPAI_PAYMENT_INBOX_BASE_URL` | (required) | Payment Inbox server URL |
| `OPAI_PAYMENT_INBOX_BASIC_USER` | (required) | Inbox auth user |
| `OPAI_PAYMENT_INBOX_BASIC_PASS` | (required) | Inbox auth password |
| `OPAI_GOPAY_POLL_INTERVAL` | `10` | Inbox poll frequency (seconds) |
| `OPAI_GOPAY_MIN_REMAINING_SEC` | `300` | Min job remaining time to claim |
| `OPAI_GOPAY_DEFAULT_PIN` | `147258` | Default 6-digit PIN |
| `OPAI_GOPAY_MIN_BALANCE_RP` | `1` | Min balance before payment |
| `OPAI_GOPAY_POST_PIN_BALANCE_WAIT_SEC` | `180` | Wait window for async GoPay balance after PIN setup |
| `OPAI_GOPAY_POST_PIN_BALANCE_POLL_SEC` | `10` | Poll interval while waiting for post-PIN balance |
| `OPAI_GOPAY_ACCOUNT_TTL_SEC` | `1200` | Account cleanup TTL |
| `OPAI_GOPAY_REGISTER_PROXY` | (none) | Override proxy for registration |
| `OPAI_GOPAY_PROXY_TEMPLATE` | (none) | Proxy URL template with `{sid}` placeholder |
| `OPAI_GOPAY_ACCOUNTS_FILE` | `config/gopay_worker_accounts.json` | Local account store |

## Architecture

```
worker thread N
  |
  +--> _register_one()
  |      rent phone (hero-sms) -> signup (gojek API) -> refresh -> GoPay init -> PIN setup
  |      -> post-registration hook -> real-device wallet warmup -> wait async balance -> refresh balance
  |      uses: gojek_client.py + gopay_signer_v2.py (HMAC-SHA256 V2 signing)
  |
  +--> wait balance >= 1 Rp (poll gopay API, keep phone alive via reactivate)
  |
  +--> _claim_job() from Payment Inbox
  |
  +--> _pay_job()
  |      uses: gopay_payment_protocol.py (Midtrans snap linking + charge + PIN challenge)
  |
  +--> loop back to register
```

## Protocol Modules

| Module | Purpose |
|---|---|
| `gopay_signer_v2.py` | HMAC-SHA256 V2 request signing (Frida-verified) |
| `gojek_client.py` | Complete Gojek/GoPay API client (signup, login, PIN, wallet, balance, app warmup) |
| `gopay_payment_protocol.py` | Midtrans GoPay payment (linking + charge + challenge, 14 steps) |
| `gopay_protocol_worker.py` | Multi-threaded worker orchestrating register + pay |
| `sms_helpers.py` | Hero-SMS API utilities (rent, wait OTP, cancel) |
| `envelope_manager.py` | Historical GoPay envelope link manager; external envelope claims are disabled in current flow |
| `payment_inbox.py` | Payment Inbox HTTP client + SQLite server |
| `burp_capture.py` | Offline Burp XML importer: decode, redact, and summarize real-device protocol captures |

## Offline Capture Import

Use this to compare real-device Burp XML captures against the local protocol
shape without storing live credentials, OTPs, PINs, cookies, or raw tokens.

```bash
cd app
PYTHONPATH=src python -m opai capture import "/path/to/burp.xml" --summary-only --out ../config/real_device_capture_summary.json
```

The summary keeps endpoint counts, status codes, header names, and JSON field
types only. For deeper local debugging, omit `--summary-only`; sensitive values
are still redacted in per-record output.

## Dependencies

- Python 3.11+
- `tls_client` (TLS fingerprint spoofing for Gojek API)
