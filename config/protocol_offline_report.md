# Offline Protocol Dataset

## Sources

- Capture XML: `/Users/username/Downloads/Telegram Lite/真机3`
- Current repo: `/Users/username/Downloads/gopay-deploy`
- Reference repo: `/tmp/Gopay_plus_automatic`
- Reference repo: `/tmp/chatgpt-plus-automation-toolkit`
- Reference repo: `/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment`
- Reference repo: `/tmp/liangshilin-gopay_account_auto`

## Capture Summary

- Total items: 271
- Unique endpoints: 46

## Hosts

- `stpphi.inapps.appsflyersdk.com`: 190
- `customer.gopayapi.com`: 35
- `api.gojekapi.com`: 14
- `accounts.goto-products.com`: 9
- `i.gojekapi.com`: 7
- `stpphi.launches.appsflyersdk.com`: 5
- `gopay-raccoon.gojekapi.com`: 3
- `api.ipify.org`: 2
- `crashlyticsreports-pa.googleapis.com`: 2
- `firebaselogging-pa.googleapis.com`: 2
- `firebaseremoteconfig.googleapis.com`: 1
- `gateway.paylater.gofin.co.id`: 1

## Comparison

- Capture endpoint keys: 46
- Current code endpoint keys: 14
- Reference code endpoint keys: 171
- Capture matched current: 2
- Capture matched reference: 0
- Capture matched both: 0
- Capture paths matched current: 35
- Capture paths matched reference: 7
- Capture paths matched both: 7

## Top Capture Endpoints

- 190x `POST stpphi.inapps.appsflyersdk.com/api/v6.17/androidevent` statuses={'200': 190}
- 8x `GET customer.gopayapi.com/v1/users/security-meter` statuses={'200': 8}
- 5x `POST stpphi.launches.appsflyersdk.com/api/v6.17/androidevent` statuses={'200': 5}
- 4x `GET customer.gopayapi.com/v1/users/profile` statuses={'200': 4}
- 3x `POST accounts.goto-products.com/cvs/v1/initiate` statuses={'200': 3}
- 3x `GET api.gojekapi.com/gojek/v2/customer` statuses={'401': 1, '200': 2}
- 3x `POST api.gojekapi.com/v7/customers/signup` statuses={'400': 2, '201': 1}
- 3x `GET gopay-raccoon.gojekapi.com/api/v1/events` statuses={'101': 3}
- 2x `POST accounts.goto-products.com/cvs/v1/methods` statuses={'200': 2}
- 2x `POST accounts.goto-products.com/cvs/v1/verify` statuses={'200': 2}
- 2x `GET api.gojekapi.com/courier/v1/token` statuses={'200': 2}
- 2x `GET api.gojekapi.com/litmus/public/run/experiments` statuses={'200': 2}
- 2x `GET api.gojekapi.com/litmus/run/experiments` statuses={'200': 2}
- 2x `GET api.ipify.org/` statuses={'200': 2}
- 2x `POST crashlyticsreports-pa.googleapis.com/v1/firelog/legacy/batchlog` statuses={}
- 2x `GET customer.gopayapi.com/v1/festivals/assets` statuses={'200': 2}
- 2x `GET customer.gopayapi.com/v1/payment-options/balances` statuses={'200': 2}
- 2x `GET customer.gopayapi.com/v1/payment-options/profiles` statuses={'200': 2}
- 2x `POST customer.gopayapi.com/v1/support/customer/initiate` statuses={'200': 2}
- 2x `GET customer.gopayapi.com/v1/users/red-badges` statuses={'200': 2}
- 2x `GET customer.gopayapi.com/v2/users/kyc/status` statuses={'200': 2}
- 2x `POST firebaselogging-pa.googleapis.com/v1/firelog/legacy/batchlog` statuses={'200': 1}
- 1x `POST accounts.goto-products.com/goto-auth/login/methods` statuses={'401': 1}
- 1x `POST accounts.goto-products.com/goto-auth/token` statuses={'201': 1}
- 1x `PUT api.gojekapi.com/v1/devices/push_token` statuses={'204': 1}

## Capture Endpoints Not Present As Full URL Literals

- `accounts.goto-products.com/cvs/v1/initiate`
- `accounts.goto-products.com/cvs/v1/methods`
- `accounts.goto-products.com/goto-auth/login/methods`
- `accounts.goto-products.com/goto-auth/token`
- `api.gojekapi.com/courier/v1/token`
- `api.gojekapi.com/gojek/v2/customer`
- `api.gojekapi.com/litmus/public/run/experiments`
- `api.gojekapi.com/litmus/run/experiments`
- `api.gojekapi.com/v1/devices/push_token`
- `api.gojekapi.com/v2/chat/profile`
- `api.gojekapi.com/v7/customers/signup`
- `api.ipify.org/`
- `crashlyticsreports-pa.googleapis.com/v1/firelog/legacy/batchlog`
- `customer.gopayapi.com/api/v1/users/pins/allowed`
- `customer.gopayapi.com/api/v2/consents/accept`
- `customer.gopayapi.com/api/v2/users/pins/setup/tokens`
- `customer.gopayapi.com/bff/v1/screens/gopay-home-v3`
- `customer.gopayapi.com/paylater/auth/partner/v1/auth/gofin-token`
- `customer.gopayapi.com/v1/festivals/assets`
- `customer.gopayapi.com/v1/payment-options/balances`
- `customer.gopayapi.com/v1/payment-options/profiles`
- `customer.gopayapi.com/v1/support/customer/actions`
- `customer.gopayapi.com/v1/support/customer/activity`
- `customer.gopayapi.com/v1/support/customer/initiate`
- `customer.gopayapi.com/v1/support/customer/session`
- `customer.gopayapi.com/v1/user/wallet-card/balance`
- `customer.gopayapi.com/v1/user/wallet-card/widget`
- `customer.gopayapi.com/v1/users/red-badges`
- `customer.gopayapi.com/v1/users/security-meter`
- `customer.gopayapi.com/v2/users/cross-sells`
- `customer.gopayapi.com/v2/users/kyc/status`
- `firebaselogging-pa.googleapis.com/v1/firelog/legacy/batchlog`
- `firebaseremoteconfig.googleapis.com/v1/projects/43578156263/namespaces/fireperf:fetch`
- `gateway.paylater.gofin.co.id/paylater-user/v2/profile`
- `gopay-raccoon.gojekapi.com/api/v1/events`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/0d7e9a7a-0874-409f-8c3f-450b4c6bce86_D_IdleV2_opt_lottie.json`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/62479384-7190-4222-bcae-331fe72114e0_DiraListeningwithGlow.json`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/7d1c26b0-2727-4edb-bc0c-a12288abc932_DiraErrorWithGlow4Opt.json`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/a4e2158c-059c-4c3e-998d-837edb5d60e8_DiraLady_Animation4.json`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/f404a24d-e888-4fbc-828d-3472d0fa4d99_DiraProcessingWithGlow4Opt.json`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/fcea6769-6c41-47ff-ab5b-a5896f4018ca_Dira_ListeningState2.json`
- `i.gojekapi.com/darkroom/nearby-cms-id/v2/files/fe9ff978-7407-4ad9-ac3a-89f42578864a_Dira_ProceessingState2.json`
- `stpphi.inapps.appsflyersdk.com/api/v6.17/androidevent`
- `stpphi.launches.appsflyersdk.com/api/v6.17/androidevent`

## Reference Repos

- `/tmp/Gopay_plus_automatic`: endpoint_keys=39, paths=34, capture_full_matches=0, capture_path_matches=0
- `/tmp/chatgpt-plus-automation-toolkit`: endpoint_keys=18, paths=23, capture_full_matches=0, capture_path_matches=0
- `/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment`: endpoint_keys=149, paths=237, capture_full_matches=0, capture_path_matches=0
- `/tmp/liangshilin-gopay_account_auto`: endpoint_keys=4, paths=9, capture_full_matches=0, capture_path_matches=7
