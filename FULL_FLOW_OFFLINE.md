# Offline Full Flow

This repo now has a runnable offline full-flow harness. It does not call live
GoPay, SMS, PIN, or Midtrans services. It uses a redacted protocol dataset from
the real-device Burp XML capture to validate the required request shapes, then
runs a deterministic end-to-end simulation:

1. Login/registration probe
2. Signup OTP methods/initiate/verify
3. Account creation
4. Token exchange
5. PIN setup
6. Profile check
7. Balance polling
8. Job claim
9. Payment settlement

## Build The Dataset

```bash
PYTHONPATH=app/src python3 -m opai capture bundle \
  "/Users/username/Downloads/Telegram Lite/真机3" \
  --current-root /Users/username/Downloads/gopay-deploy \
  --reference-root /tmp/gopay_account_auto \
  --out-json config/protocol_offline_dataset.json \
  --out-md config/protocol_offline_report.md
```

Outputs:

- `config/protocol_offline_dataset.json`
- `config/protocol_offline_report.md`

## Run The Full Flow

```bash
PYTHONPATH=app/src python3 -m opai flow offline \
  --dataset config/protocol_offline_dataset.json \
  --out config/offline_full_flow_result.json
```

Output:

- `config/offline_full_flow_result.json`

Success means the capture dataset contains the protocol shapes needed by the
offline full-flow harness, and the local end-to-end runner can execute every
phase through a simulated `settlement` payment status.

## Boundary

This is a local protocol harness, not a live payment client. It is useful for
testing orchestration, data shape changes, CLI wiring, reports, and future
sandbox integrations without touching real accounts or real money movement.
