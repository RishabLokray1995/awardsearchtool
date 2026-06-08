"""
Alaska Airlines award-search scraper.

Anti-bot techniques applied (mirrors southwest/scraper.py — see docs/prereq.md):
  1.  navigator.webdriver  → undefined
  2.  window.chrome        → realistic object
  3.  navigator.languages / plugins → realistic values
  4.  navigator.hardwareConcurrency / deviceMemory → randomised realistic values
  5.  Notification / Permissions API  → returns 'default', not 'denied'
  6.  WebGL vendor + renderer         → realistic Mac/Intel strings
  7.  Canvas pixel noise              → per-session salt defeats fingerprinting
  8.  screen / outerWidth/Height      → consistent desktop dimensions
  9.  --disable-blink-features=AutomationControlled Chrome flag
 10.  Session warm-up                 → visit Alaska homepage first
 11.  Human-like delay                → random 1.5–3.5 s after homepage load
"""

from __future__ import annotations

import random
import time

from playwright.sync_api import sync_playwright

_ALASKA_HOME   = "https://www.alaskaair.com/"
_BASE_PAGE_URL = "https://www.alaskaair.com/search/results"

# Runs inside the browser after page load.
# Finds the SvelteKit-embedded script with flight data, bracket-counts to
# extract the data block, then eval()s it natively (handles void 0 / unquoted
# keys without any Python-side parsing).
_EXTRACT_JS = """
() => {
    function extractBlock(text, start) {
        let depth = 0, inStr = false, strChar = null;
        for (let i = start; i < text.length; i++) {
            const c = text[i];
            if (inStr) {
                if (c === '\\\\') { i++; continue; }
                if (c === strChar) inStr = false;
            } else {
                if (c === '"' || c === "'" || c === '`') { inStr = true; strChar = c; }
                else if (c === '{' || c === '[' || c === '(') depth++;
                else if (c === '}' || c === ']' || c === ')') {
                    if (--depth === 0) return text.slice(start, i + 1);
                }
            }
        }
        return null;
    }

    for (const s of document.querySelectorAll('script')) {
        const text = s.textContent;
        if (!text.includes('departureStation') || !text.includes('atmosPoints')) continue;
        const re = /\\.resolve\\((\\d+),\\s*\\(\\)\\s*=>\\s*/g;
        let m;
        while ((m = re.exec(text)) !== null) {
            const block = extractBlock(text, m.index + m[0].length);
            if (!block) continue;
            try {
                const data = eval(block);
                if (Array.isArray(data) && data[0] && Array.isArray(data[0].rows)) {
                    return data[0].rows;
                }
            } catch(e) {}
        }
    }
    return [];
}
"""

_STEALTH_JS_TEMPLATE = """
(function () {{
  Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

  if (!window.chrome) {{
    window.chrome = {{
      app: {{ isInstalled: false, InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }}, RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }} }},
      runtime: {{
        OnInstalledReason: {{ CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' }},
        OnRestartRequiredReason: {{ APP_UPDATE: 'app_update', GC_PRESSURE: 'gc_pressure', PERIODIC: 'periodic' }},
        PlatformArch: {{ ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' }},
        PlatformNaclArch: {{ ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' }},
        PlatformOs: {{ ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' }},
        RequestUpdateCheckStatus: {{ NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }},
        connect: function() {{}},
        sendMessage: function() {{}}
      }}
    }};
  }}

  Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});
  const pluginData = [
    {{ name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer',              description: 'Portable Document Format' }},
    {{ name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
    {{ name: 'Native Client',      filename: 'internal-nacl-plugin',             description: '' }},
  ];
  Object.defineProperty(navigator, 'plugins', {{
    get: () => {{
      const arr = pluginData.map(p => {{ const o = Object.create(Plugin.prototype); Object.assign(o, p); return o; }});
      arr.refresh = () => {{}};
      arr.item = i => arr[i];
      arr.namedItem = n => arr.find(p => p.name === n);
      Object.defineProperty(arr, 'length', {{ get: () => arr.length }});
      return arr;
    }}
  }});

  Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw_concurrency} }});
  Object.defineProperty(navigator, 'deviceMemory',        {{ get: () => {device_memory}  }});

  if (window.Notification) {{
    Object.defineProperty(Notification, 'permission', {{ get: () => 'default' }});
  }}
  const origPermissions = navigator.permissions && navigator.permissions.query.bind(navigator.permissions);
  if (origPermissions) {{
    navigator.permissions.query = (params) => {{
      if (params.name === 'notifications') return Promise.resolve({{ state: 'default', onchange: null }});
      return origPermissions(params);
    }};
  }}

  const getParam = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(param) {{
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParam.call(this, param);
  }};
  if (typeof WebGL2RenderingContext !== 'undefined') {{
    const getParam2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(param) {{
      if (param === 37445) return 'Intel Inc.';
      if (param === 37446) return 'Intel Iris OpenGL Engine';
      return getParam2.call(this, param);
    }};
  }}

  const salt = {canvas_salt};
  const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(type, ...args) {{
    const ctx = this.getContext('2d');
    if (ctx) {{
      const imgData = ctx.getImageData(0, 0, this.width || 1, this.height || 1);
      imgData.data[0] = (imgData.data[0] + salt) & 0xff;
      ctx.putImageData(imgData, 0, 0);
    }}
    return origToDataURL.call(this, type, ...args);
  }};

  Object.defineProperty(screen, 'width',       {{ get: () => {screen_w} }});
  Object.defineProperty(screen, 'height',      {{ get: () => {screen_h} }});
  Object.defineProperty(screen, 'availWidth',  {{ get: () => {screen_w} }});
  Object.defineProperty(screen, 'availHeight', {{ get: () => {screen_h} - 40 }});
  Object.defineProperty(window, 'outerWidth',  {{ get: () => {screen_w} }});
  Object.defineProperty(window, 'outerHeight', {{ get: () => {screen_h} }});
}})();
"""

_SCREEN_SIZES = [
    (1920, 1080, 1440, 900),
    (2560, 1440, 1440, 900),
    (1680, 1050, 1440, 900),
    (1440, 900,  1280, 800),
    (1920, 1200, 1440, 900),
]


def _make_context(p):
    """Return a (browser, context) pair with a randomised stealth profile."""
    screen_w, screen_h, vp_w, vp_h = random.choice(_SCREEN_SIZES)
    hw_concurrency = random.choice([4, 6, 8, 10, 12, 16])
    device_memory  = random.choice([4, 8, 16])
    canvas_salt    = random.randint(1, 15)

    stealth_js = _STEALTH_JS_TEMPLATE.format(
        hw_concurrency=hw_concurrency,
        device_memory=device_memory,
        canvas_salt=canvas_salt,
        screen_w=screen_w,
        screen_h=screen_h,
    )

    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            f"--window-size={screen_w},{screen_h}",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
        viewport={"width": vp_w, "height": vp_h},
        locale="en-US",
        timezone_id="America/Los_Angeles",
        java_script_enabled=True,
    )
    context.add_init_script(stealth_js)
    return browser, context


def _warm_up(page) -> None:
    """Visit Alaska homepage so the CDN/bot-detection layer can issue session
    cookies before we hit the search endpoint."""
    try:
        page.goto(_ALASKA_HOME, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(random.uniform(1.5, 3.5))
    except Exception:
        pass


def build_search_url(origin: str, destination: str, date: str) -> str:
    """date format: YYYY-MM-DD"""
    params = (
        f"O={origin}&D={destination}&OD={date}"
        "&A=1&ShoppingMethod=onlineaward&RT=false&locale=en-us"
    )
    return f"{_BASE_PAGE_URL}?{params}"


def fetch_flight_rows(origin: str, destination: str, date: str) -> list[dict]:
    """
    Navigate to the Alaska award search page with a headless browser, wait for
    full render, then extract embedded SvelteKit flight data via page.evaluate().

    Returns [] if no award data is found on the page.
    """
    page_url = build_search_url(origin, destination, date)

    with sync_playwright() as p:
        browser, context = _make_context(p)
        page = context.new_page()
        try:
            _warm_up(page)
            page.goto(page_url, wait_until="networkidle", timeout=60_000)
            rows = page.evaluate(_EXTRACT_JS)
        except Exception:
            rows = []
        finally:
            browser.close()

    return rows or []
