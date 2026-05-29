# GoPay Protocol vNext

- Version: `gopay-protocol-vnext-2026-05-29`
- Generated at: `2026-05-28T16:35:11Z`
- Mode: `offline_complete_protocol_profile`

## Sources

- Capture: `/Users/username/Downloads/Telegram Lite/真机3`
- Current: `/Users/username/Downloads/gopay-deploy`
- Reference: `/tmp/Gopay_plus_automatic`
- Reference: `/tmp/chatgpt-plus-automation-toolkit`
- Reference: `/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment`
- Reference: `/tmp/liangshilin-gopay_account_auto`

## Summary

- Capture items: 271
- Capture endpoints: 46
- Code endpoint inventory: 224

## References

- `/tmp/Gopay_plus_automatic`: files=22, endpoints=39, paths=34, capture_path_matches=0
- `/tmp/chatgpt-plus-automation-toolkit`: files=97, endpoints=18, paths=23, capture_path_matches=0
- `/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment`: files=1345, endpoints=149, paths=237, capture_path_matches=0
- `/tmp/liangshilin-gopay_account_auto`: files=10, endpoints=4, paths=9, capture_path_matches=7

## Registration Flow

- `login_probe` `POST /goto-auth/login/methods` [capture, no-code]
- `signup_otp_methods` `POST /cvs/v1/methods` [capture, no-code]
- `signup_otp_initiate` `POST /cvs/v1/initiate` [capture, no-code]
- `signup_otp_verify` `POST /cvs/v1/verify` [capture, code]
- `account_create` `POST /v7/customers/signup` [capture, no-code]
- `token_exchange` `POST /goto-auth/token` [capture, no-code]
- `pin_setup` `POST /api/v2/users/pins/setup/tokens` [capture, no-code]
- `profile_check` `GET /v1/users/profile` [capture, code]
- `balance_poll` `GET /v1/payment-options/balances` [capture, no-code]

## Payment Flow

- `midtrans_linking` `POST /snap/v3/accounts/{snap_token}/linking` [no-capture, code]
- `gopay_validate_reference` `POST /v1/linking/validate-reference` [no-capture, code]
- `gopay_user_consent` `POST /v1/linking/user-consent` [no-capture, code]
- `gopay_validate_otp` `POST /v1/linking/validate-otp` [no-capture, code]
- `gopay_validate_pin` `POST /v1/linking/validate-pin` [no-capture, code]
- `midtrans_charge` `POST /snap/v2/transactions/{snap_token}/charge` [no-capture, code]
- `gopay_payment_validate` `GET /v1/payment/validate` [no-capture, code]
- `gopay_payment_confirm` `POST /v1/payment/confirm` [no-capture, code]
- `gopay_payment_process` `POST /v1/payment/process` [no-capture, code]
- `midtrans_status` `GET /snap/v1/transactions/{snap_token}/status` [no-capture, code]

## Missing

- `registration`: none
- `payment`: none
