const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PROFILE_ROOT = process.env.OPAI_CHECKOUT_BROWSER_PROFILE_DIR || "/tmp/gopay_openai_checkout_profiles";
const HEADLESS = !/^0|false|no$/i.test(String(process.env.OPAI_CHECKOUT_BROWSER_HEADLESS || "1").trim());
const WARMUP_WAIT_MS = Math.max(500, Number.parseInt(process.env.OPAI_CHECKOUT_BROWSER_WARMUP_WAIT_MS || "2500", 10) || 2500);
const FETCH_RETRIES = Math.max(1, Number.parseInt(process.env.OPAI_CHECKOUT_BROWSER_FETCH_RETRIES || "3", 10) || 3);
const FETCH_TIMEOUT_MS = Math.max(5000, Number.parseInt(process.env.OPAI_CHECKOUT_BROWSER_FETCH_TIMEOUT_MS || "30000", 10) || 30000);

function sanitizeProfileName(proxy) {
  const tag = Buffer.from(String(proxy || "direct")).toString("base64url").slice(0, 24);
  return path.join(PROFILE_ROOT, tag);
}

function parseCookieHeader(cookieHeader) {
  const out = [];
  for (const part of String(cookieHeader || "").split(";")) {
    const idx = part.indexOf("=");
    if (idx <= 0) continue;
    const name = part.slice(0, idx).trim();
    const value = part.slice(idx + 1).trim();
    if (name && value) out.push({ name, value });
  }
  return out;
}

function buildPayload(input) {
  return {
    entry_point: "all_plans_pricing_modal",
    plan_name: input.plan_name || "chatgptplusplan",
    billing_details: {
      country: String(input.country || "ID").trim().toUpperCase(),
      currency: String(input.currency || "IDR").trim().toUpperCase(),
    },
    cancel_url: "https://chatgpt.com/#pricing",
    promo_campaign: {
      promo_campaign_id: input.promo_campaign_id || "plus-1-month-free",
      is_coupon_from_query_param: false,
    },
    checkout_ui_mode: input.checkout_ui_mode || "hosted",
  };
}

async function addStealth(context) {
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    Object.defineProperty(navigator, "language", { get: () => "en-US" });
    Object.defineProperty(navigator, "languages", { get: () => ["en-US", "en"] });
    Object.defineProperty(navigator, "platform", { get: () => "MacIntel" });
    Object.defineProperty(navigator, "hardwareConcurrency", { get: () => 8 });
    Object.defineProperty(navigator, "plugins", {
      get: () => [{ name: "Chrome PDF Plugin" }, { name: "Chrome PDF Viewer" }, { name: "Native Client" }],
    });
    if (!window.chrome) {
      Object.defineProperty(window, "chrome", {
        get: () => ({ runtime: {}, app: {}, csi: () => ({}), loadTimes: () => ({}) }),
      });
    }
  });
}

async function seedCookies(context, input) {
  const cookies = [];
  const seen = new Set();
  for (const item of parseCookieHeader(input.cookie_header || input.cookieHeader || "")) {
    seen.add(item.name);
    cookies.push({
      name: item.name,
      value: item.value,
      domain: ".chatgpt.com",
      path: "/",
      httpOnly: /next-auth|session/i.test(item.name),
      secure: true,
      sameSite: "Lax",
    });
  }
  const sessionToken = String(input.session_token || input.sessionToken || "").trim();
  if (sessionToken && !seen.has("__Secure-next-auth.session-token")) {
    cookies.push({
      name: "__Secure-next-auth.session-token",
      value: sessionToken,
      domain: ".chatgpt.com",
      path: "/",
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
    });
  }
  if (cookies.length) await context.addCookies(cookies).catch(() => {});
}

async function safeGoto(page, url) {
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  } catch (_) {}
}

async function pageBodyText(page) {
  return page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
}

function looksLikeChallengeText(text) {
  return /enable javascript and cookies to continue|attention required|verify you are human|cloudflare/i.test(
    String(text || "").replace(/\s+/g, " ")
  );
}

async function warmupContext(page) {
  for (const url of ["https://chatgpt.com/", "https://chatgpt.com/#pricing", "https://chatgpt.com/api/auth/session"]) {
    await safeGoto(page, url);
    await page.waitForTimeout(WARMUP_WAIT_MS);
  }
  const text = await pageBodyText(page);
  if (looksLikeChallengeText(text)) {
    await page.waitForTimeout(WARMUP_WAIT_MS * 2);
  }
}

async function launchContext(input) {
  const options = {
    headless: HEADLESS,
    locale: "en-US",
    timezoneId: "America/New_York",
    viewport: { width: 1366, height: 920 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
  };
  const proxy = String(input.proxy || input.proxy_url || "").trim();
  if (proxy) options.proxy = { server: proxy };
  if (fs.existsSync(CHROME_PATH)) options.executablePath = CHROME_PATH;
  fs.mkdirSync(PROFILE_ROOT, { recursive: true });
  const context = await chromium.launchPersistentContext(sanitizeProfileName(proxy), options);
  return { context, close: () => context.close() };
}

async function requestCheckout(page, token, payload) {
  await safeGoto(page, "https://chatgpt.com/#pricing");
  return page.evaluate(async ({ token, payload, timeoutMs }) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch("https://chatgpt.com/backend-api/payments/checkout", {
        method: "POST",
        credentials: "include",
        signal: controller.signal,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch (_) { data = { raw: text.slice(0, 1200) }; }
      return { ok: response.ok, status: response.status, data };
    } catch (error) {
      return { ok: false, status: 0, data: { error: String((error && error.message) || error) } };
    } finally {
      clearTimeout(timer);
    }
  }, { token, payload, timeoutMs: FETCH_TIMEOUT_MS });
}

async function main() {
  const input = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
  const token = String(input.access_token || input.accessToken || "").trim();
  if (!token) throw new Error("missing access_token");
  const { context, close } = await launchContext(input);
  try {
    await addStealth(context);
    await seedCookies(context, input);
    const page = context.pages()[0] || await context.newPage();
    await warmupContext(page);
    let last = { ok: false, status: 0, data: { error: "not_started" } };
    for (let attempt = 1; attempt <= FETCH_RETRIES; attempt += 1) {
      last = await requestCheckout(page, token, buildPayload(input));
      if (last.ok) break;
      await warmupContext(page);
      await page.waitForTimeout(WARMUP_WAIT_MS * attempt);
    }
    if (!last.ok) {
      throw new Error(`browser checkout HTTP ${last.status}: ${JSON.stringify(last.data).slice(0, 500)}`);
    }
    const body = last.data || {};
    const longUrl = body.url || body.stripe_hosted_url || body.checkout_url || "";
    const checkoutSessionId = body.checkout_session_id || body.session_id || body.id || "";
    if (!longUrl && !checkoutSessionId) throw new Error(`browser checkout missing URL/session: ${JSON.stringify(body).slice(0, 500)}`);
    process.stdout.write(JSON.stringify({
      ok: true,
      strategy: "browser_warmup",
      longUrl,
      checkoutSessionId,
      publishableKey: body.publishable_key || "",
      processorEntity: body.processor_entity || "",
      checkoutResponse: body,
    }));
  } finally {
    await close().catch(() => {});
  }
}

main().catch((error) => {
  process.stderr.write(String((error && error.stack) ? error.stack : error));
  process.exit(1);
});
