# GoPay 完整整合版运行手册

这份项目现在整理成一个本机可重复生成、可验证、可启动的 GoPay protocol vNext 包。它不是只写死一份输出，而是用你的真机抓包加多个参考仓库重新生成协议画像、端点清单和离线全流程验证结果。

## 当前整合范围

| 来源 | 路径 | 用途 |
|---|---|---|
| 本机主项目 | `/Users/username/Downloads/gopay-deploy` | 最终运行目录、worker、协议模块、离线验证 |
| 真机抓包 | `/Users/username/Downloads/Telegram Lite/真机3` | 注册、OTP、PIN、余额、GoPay App 真实接口形状 |
| Gopay_plus_automatic | `/tmp/Gopay_plus_automatic` | ChatGPT/Stripe/Midtrans/GoPay 支付链参考 |
| chatgpt-plus-automation-toolkit | `/tmp/chatgpt-plus-automation-toolkit` | ChatGPT checkout 和支付入口参考 |
| Gpt-Agreement-Payment | `/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment` | 更完整的 OpenAI/Stripe/Midtrans/GoPay 协议资料 |
| gopay_account_auto | `/tmp/liangshilin-gopay_account_auto` | GoPay 注册、OTP、PIN、HMAC/header 参考 |

## 已生成的完整版本文件

| 文件 | 说明 |
|---|---|
| `config/protocol_vnext.json` | 机器可读的 vNext 协议画像 |
| `config/protocol_vnext.md` | 人能直接看的协议状态摘要 |
| `config/protocol_offline_dataset.json` | 真机抓包 + 代码参考合并后的完整离线数据集 |
| `config/protocol_offline_report.md` | 抓包和代码参考对比报告 |
| `config/gopay_protocol_inventory.json` | 分类后的端点清单 |
| `config/gopay_protocol_inventory.md` | 人能直接看的端点清单 |
| `config/offline_full_flow_result.json` | 最近一次离线完整流程验证结果 |
| `PROTOCOL_VNEXT_GUIDE.md` | 协议层详细说明 |
| `GOPAY_COMPLETE_RUNBOOK.md` | 当前这份完整运行手册 |

协议结构、路径、method、字段类型、状态码、来源证据都会保留在生成物里。账号 token、cookie、OTP、PIN、手机号、支付 session 这类运行时凭据由本机配置和实时流程读取，不写进文档输出。

## 一键验证完整版本

进入项目目录：

```bash
cd /Users/username/Downloads/gopay-deploy
```

跑完整验证：

```bash
./verify_ready.sh
```

这个脚本会依次执行：

```text
1. 重新从真机抓包和参考仓库生成 protocol vNext
2. 打印 protocol status
3. 跑离线 register -> OTP -> balance -> payment 全流程
4. 跑 app/tests 测试
```

通过时最后会看到：

```text
READY: protocol package, offline flow, and tests passed.
```

## 当前健康状态

当前版本：

```text
gopay-protocol-vnext-2026-05-29
```

当前验证指标：

```text
capture items: 271
capture endpoints: 46
code endpoint inventory: 224
registration_missing: []
payment_missing: []
pytest: 12 passed
offline flow: ok
```

这里的 `registration_missing: []` 和 `payment_missing: []` 表示协议画像要求的注册链路和支付链路都有证据覆盖。注册侧主要来自你的真机抓包；支付/Midtrans 侧主要来自几个参考项目里的代码证据，因为这次 `真机3` 抓包里没有完整 Midtrans linking/charge 过程。

## 本地离线跑通

不需要任何外部 key，直接跑：

```bash
./run_offline.sh
```

单独看协议状态：

```bash
.venv/bin/opai protocol status --profile config/protocol_vnext.json
```

单独跑测试：

```bash
.venv/bin/python -m pytest app/tests -q
```

## 配置实时运行

实时 worker 需要短信平台 key 和 Payment Inbox 配置。项目已经带了模板：

```bash
cp config/runtime.env.example config/runtime.env
```

如果 `config/runtime.env` 已经存在，就直接编辑它，不要覆盖：

```bash
nano config/runtime.env
```

至少要确认这几个值：

```bash
OPAI_HEROSMS_API_KEY=你的HeroSMSKey
OPAI_PAYMENT_INBOX_BASE_URL=http://127.0.0.1:19080
OPAI_PAYMENT_INBOX_PORT=19080
OPAI_PAYMENT_INBOX_PATH=config/payment_inbox.json
OPAI_GOPAY_DEFAULT_PIN=147258
```

也可以把 key 放到单独文件：

```bash
OPAI_HEROSMS_API_KEY_FILE=/Users/username/.config/herosms.key
```

## 手动填写模式

如果你没有 Hero-SMS API Key，或者想先用自己的手机号手动测试，可以用手动注册模式。这个模式不租号，不自动读短信；程序会把 OTP 发到你填的手机号，然后在终端里等你输入验证码。

命令：

```bash
cd /Users/username/Downloads/gopay-deploy
./start_manual_register.sh --phone 085142447768 --pin 147258
```

手机号必须是印尼 GoPay 可接收 OTP 的号码，支持这些格式：

```text
085142447768
85142447768
6285142447768
+6285142447768
```

不要填 `86...` 开头的中国号码；GoPay 注册接口会拒绝。

如果只是想先用 `86` 号码测试终端输入流程，不请求真实 GoPay 接口，用 mock 模式：

```bash
./start_manual_register.sh --mock --phone 861992222991 --pin 147258
```

## PIN 后真机初始化链路

这版已经把 `真机3` 里 PIN 设置成功后的 App 初始化动作接进当前运行版本。注册完成后不会只跑 `post-registration-hook`，还会继续执行：

```text
1. /api/v2/consents/accept
2. /bff/v1/screens/gopay-home-v3
3. /v1/payment-options/profiles
4. /v1/payment-options/balances
5. /v1/user/wallet-card/balance?screen=home_3_1
6. /v1/user/wallet-card/widget?screen=home_3_1
7. api.gojekapi.com/v1/devices/push_token
8. api.gojekapi.com/courier/v1/token
9. /paylater/auth/partner/v1/auth/gofin-token
10. /v1/users/security-meter 的 gopay_home / account_safety_home / security_meter 来源刷新
```

网页里的“补激活/查余额”也走同一套链路。`support/customer/initiate/session/actions/activity` 在抓包里是加密 SDK body；当前没有硬造假 body，等拿到明文算法或新的可复现抓包后再接入。

mock 模式会让你输入两次任意验证码，然后把本地测试结果写到：

```text
config/manual_register_mock_result.json
```

如果你明确要用 `86` 号码真实请求 GoPay 接口做返回测试，用：

```bash
./start_manual_register.sh --phone 861992222991 --country-code 86 --force-live --pin 147258
```

这会真实请求 GoPay/Gojek 的注册链路。按当前抓包证据，GoPay 注册主要是印尼 `+62` 体系，所以 `+86` 大概率会被接口返回 `400`，脚本会把错误 body 打到日志里。

也可以不写手机号，让程序提示你输入：

```bash
./start_manual_register.sh --pin 147258
```

手动模式会要求你输入两次验证码：

```text
1. 注册 OTP
2. 设置 PIN 的 OTP
```

当前 OTP 等待时间：

```text
注册 OTP：180 秒
PIN OTP：第一次 60 秒；超时后最多重发 2 次，每次 180 秒
已有账号登录 OTP：180 秒
支付 OTP：120 秒
网页 OTP 收件箱缓存：300 秒
```

网页注册页默认勾选了“注册后退出登录并重新登录”。开启时，PIN 设置和钱包初始化完成后会真实调用 logout，然后走已有账号 `PIN + 登录 OTP`，最后把重新登录得到的 token 覆盖保存到 `config/gopay_worker_accounts.json`。

终端手动注册也可以打开同样流程：

```bash
./start_manual_register.sh --phone 085142447768 --pin 147258 --relogin-after-register
```

PIN 设置完成后，流程会继续做：

```text
1. GoPay post-registration-hook 激活钱包
2. 执行真机 PIN 后钱包初始化链路
3. 如果 hook 第一次失败，跑真机初始化后刷新 token，再补打第二次 hook
4. 最多等待 180 秒轮询系统异步到账余额
5. 刷新余额并写回 config/gopay_worker_accounts.json
```

外部节日红包默认不强制领取；如果要领，在网页「GoPay账号」页的「节日红包配置」里保存红包短链，再在注册页勾选「注册后领取节日红包」，或在账号列表点「领节日红包」。配置保存到：

```text
config/envelope_links.json
```

你真机手动注册后 PIN 一设置或安全初始化后自动到账的余额，属于 GoPay 后端系统异步发放；节日红包是额外配置短链后调用 GoPay 红包领取接口。

```text
OPAI_GOPAY_POST_PIN_BALANCE_WAIT_SEC=180
OPAI_GOPAY_POST_PIN_BALANCE_POLL_SEC=10
```

`GoPay 钱包激活 hook 返回 500` 不代表注册失败。它是 GoPay 服务端 hook 没接受这次激活触发；当前流程会继续执行真机初始化链路，刷新 token 后补打第二次 hook，再轮询余额并保存账号。

注册成功后账号会保存到：

```text
config/gopay_worker_accounts.json
```

后面可以查余额：

```bash
.venv/bin/opai worker balance +6285142447768
```

单笔 Midtrans GoPay 支付也支持手动 OTP：

```bash
.venv/bin/opai pay "https://app.midtrans.com/snap/v4/redirection/<snap_id>" --phone 85142447768 --pin 147258
```

支付过程中如果 GoPay linking 发送 OTP，终端会提示你手动输入。

也可以在网页里用 OpenAI AT 生成 Midtrans 链接：

```text
支付任务 -> OpenAI AT -> 用 AT 生成 Midtrans 链接
```

生成成功后系统会自动创建一条 GoPay 订阅任务，并把 Midtrans 链接填到支付栏。AT 只通过本机网页 POST 到本机后端用于本次生成，不会写入任务库或日志；如果 OpenAI 返回 401/403，再补填同浏览器的 chatgpt.com Session Cookie。

## 启动 Payment Inbox

开一个终端：

```bash
cd /Users/username/Downloads/gopay-deploy
./start_inbox.sh
```

默认监听：

```text
http://127.0.0.1:19080
```

现在这个地址是网页管理台，不只是旧的收件箱页面。里面有：

```text
订阅任务
注册任务
GoPay账号
PIN管理
支付任务
OTP收件箱
```

手动注册也可以在网页里操作：

```text
1. 打开 http://127.0.0.1:19080
2. 点左侧「注册任务」
3. 填手机号、国家码、PIN
4. 点「开始注册」
5. 页面提示 OTP 时，直接在网页输入验证码
```

如果要用 `86` 号码真实请求接口测试，需要在网页里把国家码改成 `86`，模式选「强制真实请求非 +62」。接口仍可能返回 `invalid_phone_email`，这是 GoPay 服务端对号码的校验结果。

老号修改 PIN：

```text
1. 先在「注册任务」里用「已有账号登录」把老号登录并保存到本地账号列表
2. 点左侧「PIN管理」
3. 选择 GoPay 账号
4. 修改方式选「知道旧 PIN，直接修改」
5. 输入旧 PIN 和新 PIN
6. 点「开始修改」
7. 成功后会自动把新 PIN 写回 config/gopay_worker_accounts.json
```

不知道旧 PIN 时，页面里选「不知道旧 PIN，短信重置」。这条不是普通改 PIN challenge，需要真机里点「忘记 PIN」后抓到短信重置流程再接入；当前页面会用中文提示，不再暴露 `UPDATE_PIN` / `CHANGE_PIN` 这类协议名。

```text
知道旧 PIN：验证旧 PIN -> 提交新 PIN
不知道旧 PIN：发送短信 OTP -> 验证 OTP -> 重置新 PIN
```

老账户补激活 / 查余额 / 领节日红包：

```text
1. 打开 http://127.0.0.1:19080
2. 点左侧「GoPay账号」
3. 在「节日红包配置」里保存或替换红包短链
4. 在对应账号行点「补激活/查余额」或「领节日红包」
5. 余额会刷新到列表里
```

## 启动 Worker

再开一个终端：

```bash
cd /Users/username/Downloads/gopay-deploy
./start_worker.sh --workers 3 --pin 147258
```

如果你看到：

```text
Missing Hero-SMS API key. Set OPAI_HEROSMS_API_KEY or OPAI_HEROSMS_API_KEY_FILE in config/runtime.env.
```

说明 `config/runtime.env` 里还没有填 `OPAI_HEROSMS_API_KEY`，或者 `OPAI_HEROSMS_API_KEY_FILE` 指向的文件不存在/为空。

## 用新抓包更新协议

以后你又抓了新的 Burp XML，直接指定新路径刷新：

```bash
GOPAY_CAPTURE_XML="/path/to/new/burp.xml" ./refresh_protocol_vnext.sh
```

如果参考仓库路径也换了：

```bash
GOPAY_CAPTURE_XML="/path/to/new/burp.xml" \
GOPAY_PLUS_AUTO_ROOT="/path/to/Gopay_plus_automatic" \
CHATGPT_PLUS_TOOLKIT_ROOT="/path/to/chatgpt-plus-automation-toolkit" \
GPT_AGREEMENT_PAYMENT_ROOT="/path/to/Gpt-Agreement-Payment" \
GOPAY_ACCOUNT_AUTO_ROOT="/path/to/gopay_account_auto" \
./refresh_protocol_vnext.sh
```

刷新后再跑：

```bash
./verify_ready.sh
```

## 两条运行线

| 模式 | 命令 | 是否需要外部配置 | 用途 |
|---|---|---|---|
| 离线验证 | `./verify_ready.sh` | 不需要 | 验证协议包、抓包整合、测试是否完整 |
| 实时 worker | `./start_worker.sh --workers 3 --pin 147258` | 需要 Hero-SMS key、Payment Inbox | 走真实注册和支付 worker |

## 现在还差什么最有价值

当前真机抓包已经覆盖注册/account 侧。下一份最有价值的新抓包是完整支付侧：

```text
Midtrans redirection
GoPay linking
validate-reference
user-consent
validate-otp
validate-pin
charge
payment validate/confirm/process
transaction status
```

拿到这段以后，`payment` 部分就能从“代码证据覆盖”升级成“真机抓包 + 代码证据双覆盖”。
