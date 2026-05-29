# GoPay Protocol vNext Guide

This project now has a project-owned protocol profile built from real-device
capture data and multiple reference repositories. The goal is to keep one
repeatable source of truth for GoPay registration and GoPay/Midtrans payment
protocol evidence.

## Current Version

- Version: `gopay-protocol-vnext-2026-05-29`
- Capture source: `/Users/username/Downloads/Telegram Lite/真机3`
- Capture items: `271`
- Capture endpoints: `46`
- Code endpoint inventory: `224`
- Registration missing steps: `0`
- Payment missing steps: `0`

## Source Inputs

| Role | Path | Purpose |
|---|---|---|
| Current project | `/Users/username/Downloads/gopay-deploy` | Local protocol worker, offline harness, profile generator |
| Real-device capture | `/Users/username/Downloads/Telegram Lite/真机3` | Ground truth for GoPay/Gojek registration, PIN, balance, app API shape |
| Reference | `/tmp/Gopay_plus_automatic` | ChatGPT/Stripe/Midtrans/GoPay payment chain evidence |
| Reference | `/tmp/chatgpt-plus-automation-toolkit` | ChatGPT checkout/GoPay workflow evidence |
| Reference | `/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment` | Larger payment protocol reference, OpenAI/Stripe/Midtrans/GoPay paths |
| Reference | `/tmp/liangshilin-gopay_account_auto` | GoPay account registration, OTP, PIN setup, HMAC/header evidence |

## Source Contribution Matrix

| Source | Registration | GoPay account app | Midtrans/GoPay payment | OpenAI checkout |
|---|---|---|---|---|
| Real-device capture `真机3` | primary evidence | primary evidence | not captured in this file | no |
| Current project | implementation | implementation | implementation | payment inbox entry only |
| `Gopay_plus_automatic` | partial | partial | primary reference | reference |
| `chatgpt-plus-automation-toolkit` | no | no | checkout entry reference | reference |
| `Gpt-Agreement-Payment` | partial | partial | primary reference | primary reference |
| `gopay_account_auto` | closest code match | PIN/envelope reference | no | no |

## Generated Files

| File | Description |
|---|---|
| `config/protocol_vnext.json` | Main vNext profile: sources, flow evidence, missing-step status |
| `config/protocol_vnext.md` | Human-readable vNext summary |
| `config/protocol_offline_dataset.json` | Full redacted dataset from capture + code references |
| `config/protocol_offline_report.md` | Capture/reference comparison summary |
| `config/gopay_protocol_inventory.json` | Categorized endpoint inventory from capture and code |
| `config/gopay_protocol_inventory.md` | Human-readable endpoint inventory |
| `config/offline_full_flow_result.json` | Last offline verification result |
| `GOPAY_COMPLETE_RUNBOOK.md` | Chinese complete runbook for setup and operation |
| `verify_ready.sh` | One-command rebuild + offline validation + tests |

## Refresh The Whole vNext Package

```bash
cd /Users/username/Downloads/gopay-deploy
./refresh_protocol_vnext.sh
```

The refresh script performs three steps:

1. Rebuilds `protocol_offline_dataset.json` from the real-device Burp XML and all reference repos.
2. Rebuilds `protocol_vnext.json` and `protocol_vnext.md`.
3. Runs the offline full-flow validation.

Override source paths with environment variables when needed:

```bash
GOPAY_CAPTURE_XML="/path/to/new/burp.xml" \
GOPAY_PLUS_AUTO_ROOT="/path/to/Gopay_plus_automatic" \
CHATGPT_PLUS_TOOLKIT_ROOT="/path/to/chatgpt-plus-automation-toolkit" \
GPT_AGREEMENT_PAYMENT_ROOT="/path/to/Gpt-Agreement-Payment" \
GOPAY_ACCOUNT_AUTO_ROOT="/path/to/gopay_account_auto" \
./refresh_protocol_vnext.sh
```

## Inspect Status

```bash
.venv/bin/opai protocol status --profile config/protocol_vnext.json
```

Expected healthy status:

```text
registration_missing: []
payment_missing: []
```

## Registration Flow Evidence

These steps are covered by the real-device capture. Some also have code-source
evidence from the local project or references.

| Step | Method + Path | Evidence |
|---|---|---|
| `login_probe` | `POST /goto-auth/login/methods` | capture |
| `signup_otp_methods` | `POST /cvs/v1/methods` | capture |
| `signup_otp_initiate` | `POST /cvs/v1/initiate` | capture |
| `signup_otp_verify` | `POST /cvs/v1/verify` | capture + code |
| `account_create` | `POST /v7/customers/signup` | capture |
| `token_exchange` | `POST /goto-auth/token` | capture |
| `pin_setup` | `POST /api/v2/users/pins/setup/tokens` | capture |
| `profile_check` | `GET /v1/users/profile` | capture + code |
| `balance_poll` | `GET /v1/payment-options/balances` | capture |

The `liangshilin0122-wq/gopay_account_auto` reference currently matches the
registration capture paths most closely:

- `/cvs/v1/methods`
- `/cvs/v1/initiate`
- `/cvs/v1/verify`
- `/goto-auth/login/methods`
- `/goto-auth/token`
- `/v7/customers/signup`
- `/api/v2/users/pins/setup/tokens`

## Payment Flow Evidence

The current real-device capture is mainly registration/account-side traffic.
The GoPay/Midtrans payment chain is code-backed by the reference repositories.

| Step | Method + Path | Evidence |
|---|---|---|
| `midtrans_linking` | `POST /snap/v3/accounts/{snap_token}/linking` | code |
| `gopay_validate_reference` | `POST /v1/linking/validate-reference` | code |
| `gopay_user_consent` | `POST /v1/linking/user-consent` | code |
| `gopay_validate_otp` | `POST /v1/linking/validate-otp` | code |
| `gopay_validate_pin` | `POST /v1/linking/validate-pin` | code |
| `midtrans_charge` | `POST /snap/v2/transactions/{snap_token}/charge` | code |
| `gopay_payment_validate` | `GET /v1/payment/validate` | code |
| `gopay_payment_confirm` | `POST /v1/payment/confirm` | code |
| `gopay_payment_process` | `POST /v1/payment/process` | code |
| `midtrans_status` | `GET /snap/v1/transactions/{snap_token}/status` | code |

## Verification

Run the complete local verification:

```bash
./verify_ready.sh
```

Run tests:

```bash
.venv/bin/python -m pytest app/tests -q
```

Run offline flow:

```bash
./run_offline.sh
```

Latest verified result:

- `pytest`: `6 passed`
- offline flow: `ok: true`

## Notes

- The real-device capture remains the source of truth for registration-side
  request shapes.
- Payment-side steps are currently code-backed, not capture-backed, because the
  provided `真机3` capture does not contain the Midtrans linking/charge sequence.
- Generated protocol files are excluded from protocol literal scanning to avoid
  self-referential growth on each refresh.
