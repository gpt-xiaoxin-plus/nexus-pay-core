# GoPay 云手机抓包工具包

这个目录用于抓 GoPay 云手机操作包，重点抓：

- 注册后真实 App 初始化链路
- 已知旧 PIN 修改新 PIN
- 不知道旧 PIN 的短信重置链路
- 设置 PIN 后余额/系统赠送触发链路

## 目录

- `scripts/check_env.sh`：检查本机工具、IP、ADB 设备。
- `scripts/adb_connect_cloud.sh`：连接云手机 ADB。
- `scripts/start_mitmweb.sh`：启动网页版 mitmproxy，方便边点边看。
- `scripts/start_mitmdump_gopay.sh`：启动命令行抓包，自动把 GoPay 相关请求写入 `captures/`。
- `scripts/set_android_proxy.sh`：给云手机设置 HTTP 代理。
- `scripts/clear_android_proxy.sh`：清掉云手机代理。
- `scripts/export_latest.sh`：打包最新抓包结果。
- `addons/gopay_capture_filter.py`：mitmproxy 插件，只提取 GoPay/GoTo/Midtrans 相关请求。
- `captures/`：抓包输出目录。

## 快速开始

1. 检查环境：

```bash
cd /Users/username/Downloads/gopay-deploy/gopay_cloud_capture_toolkit
./scripts/check_env.sh
```

2. 连接云手机 ADB，例如云手机 ADB 是 `127.0.0.1:7252`：

```bash
./scripts/adb_connect_cloud.sh 127.0.0.1:7252
```

3. 启动 mitmweb：

```bash
./scripts/start_mitmweb.sh
```

打开浏览器：

```text
http://127.0.0.1:18081
```

4. 给云手机设置代理。`HOST_IP` 必须是云手机能访问到的电脑 IP：

```bash
HOST_IP=你的电脑IP ./scripts/set_android_proxy.sh 127.0.0.1:7252
```

如果云手机和 Mac 不在同一网络，云手机访问不到 Mac 局域网 IP，需要用云手机平台提供的本地代理/端口映射，或者把 mitmproxy 部署在云手机同网段服务器上。

5. 安装证书：

云手机浏览器打开：

```text
http://mitm.it
```

下载 Android 证书并安装。安装路径通常是：

```text
设置 -> 安全 -> 加密与凭据 -> 安装证书 -> CA 证书
```

6. 开始抓 GoPay：

```bash
./scripts/start_mitmdump_gopay.sh
```

7. 操作 GoPay App。操作完成后按 `Ctrl+C` 停止抓包。

8. 打包结果：

```bash
./scripts/export_latest.sh
```

## 要抓哪些操作

### A. 已知旧 PIN 修改新 PIN

从点击修改 PIN 前开始抓：

1. 打开 GoPay。
2. 进入安全/PIN 页面。
3. 点击修改 PIN。
4. 输入旧 PIN。
5. 输入新 PIN。
6. 再确认新 PIN。
7. 等成功或失败提示。

重点看这些接口有没有出现：

- `/api/v1/users/pin/challenges`
- `/api/v1/users/pin/tokens`
- `/api/v1/users/pin/tokens/nb`
- `/v3/users/pin/update`
- 任何包含 `pin`、`challenge`、`token` 的 GoPay 请求。

### B. 忘记 PIN / 短信重置

从点击“忘记 PIN”前开始抓：

1. 进入 PIN 页面。
2. 点击忘记 PIN。
3. 触发短信 OTP。
4. 输入 OTP。
5. 设置新 PIN。
6. 等成功或失败提示。

重点看：

- `/api/v3/users/pins/reset/tokens`
- OTP initiate / verify 请求
- challenge 请求

### C. 设置 PIN 后余额触发

新号注册设置 PIN 完成后不要立刻关 App，继续抓：

1. 设置 PIN 成功。
2. 回首页。
3. 点钱包/余额卡片。
4. 点安全中心或完成 App 弹出的安全提示。
5. 等 1-3 分钟。
6. 刷新余额。

重点看：

- `/v1/customer/payment-options/post-registration-hook`
- `/v1/payment-options/profiles`
- `/v1/payment-options/balances`
- 钱包首页 BFF / widget / security meter 相关接口。

## 判断有没有抓成功

成功时，`captures/gopay_flows_*.jsonl` 里应该看到 `customer.gopayapi.com` 请求，并且有明文 path/body/status。

如果只能看到 `CONNECT customer.gopayapi.com:443`，看不到 path/body，说明 App 没有接受代理证书，或者云手机代理没有生效。

如果浏览器能打开 `http://mitm.it`，但 GoPay 没有明文，通常是 App 侧不信任用户 CA 或使用证书固定。这种情况下不要靠猜接口，先换可抓包环境或补真机抓包。

## 清理代理

抓完必须清掉云手机代理：

```bash
./scripts/clear_android_proxy.sh 127.0.0.1:7252
```

