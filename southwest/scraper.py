"""
Southwest Airlines award-search scraper.

Uses a headless Playwright browser to navigate to Southwest's booking page and
intercepts the internal JSON API call that returns award pricing data.  Because
Southwest's front-end uses dynamically generated anti-bot headers (Akamai
ee30zvqlwf-*), we let the real browser generate those headers and simply
capture the XHR response rather than replaying the request ourselves.

Anti-bot techniques applied (see docs/prereq.md for full notes):
  1.  navigator.webdriver  → undefined
  2.  window.chrome        → realistic object (headless has none by default)
  3.  navigator.languages / plugins / mimeTypes → realistic values
  4.  navigator.hardwareConcurrency / deviceMemory → randomised realistic values
  5.  Notification / Permissions API  → returns 'default', not 'denied'
  6.  WebGL vendor + renderer         → realistic Mac/Intel strings
  7.  Canvas pixel noise              → tiny random per-session salt defeats
                                        deterministic canvas fingerprinting
  8.  screen.width/height             → larger than viewport (as on a real desktop)
  9.  window.outerWidth/Height        → matches screen (not 0 as in headless)
 10.  --disable-blink-features=AutomationControlled Chrome flag
 11.  Session warm-up                 → visit SW homepage first to build Akamai
                                        session cookies before hitting the API page
 12.  Human-like delay                → random 1-3 s after homepage load
"""

from __future__ import annotations

import random
import time

from playwright.sync_api import sync_playwright

_SW_HOME            = "https://www.southwest.com/"
_SHOPPING_URL_FRAGMENT = "/api/air-booking/v1/air-booking/page/air/booking/shopping"
_CALENDAR_URL_FRAGMENT = "/api/air-booking/v1/air-booking/page/air/low-fare-calendar/select-dates"
_SEARCH_PAGE_BASE   = "https://www.southwest.com/air/booking/select-depart.html"
_CALENDAR_PAGE_BASE = "https://www.southwest.com/air/low-fare-calendar/select-dates"

# ---------------------------------------------------------------------------
# Stealth JS — injected before ANY page script runs (add_init_script)
# ---------------------------------------------------------------------------
# hw_concurrency and device_memory are filled in at runtime so they stay
# consistent across every page load within the same browser session.
_STEALTH_JS_TEMPLATE = """
(function () {{
  // 1. Hide webdriver flag
  Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

  // 2. Realistic window.chrome (absent in headless by default)
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

  // 3. Languages and plugins
  Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});
  const pluginData = [
    {{ name: 'Chrome PDF Plugin',      filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
    {{ name: 'Chrome PDF Viewer',      filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
    {{ name: 'Native Client',          filename: 'internal-nacl-plugin', description: '' }},
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

  // 4. Hardware concurrency and device memory (set at launch time)
  Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw_concurrency} }});
  Object.defineProperty(navigator, 'deviceMemory',        {{ get: () => {device_memory}  }});

  // 5. Permissions API — return 'default' for notification instead of 'denied'
  const _origQuery = window.Notification && Notification.permission;
  if (window.Notification) {{
    Object.defineProperty(Notification, 'permission', {{ get: () => 'default' }});
  }}
  const origPermissions = navigator.permissions && navigator.permissions.query.bind(navigator.permissions);
  if (origPermissions) {{
    navigator.permissions.query = (params) => {{
      if (params.name === 'notifications') {{
        return Promise.resolve({{ state: 'default', onchange: null }});
      }}
      return origPermissions(params);
    }};
  }}

  // 6. WebGL — realistic Mac Intel strings
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

  // 7. Canvas fingerprint — add per-session pixel noise so hash is never constant
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

  // 8 & 9. Screen and outer window dimensions
  Object.defineProperty(screen, 'width',       {{ get: () => {screen_w} }});
  Object.defineProperty(screen, 'height',      {{ get: () => {screen_h} }});
  Object.defineProperty(screen, 'availWidth',  {{ get: () => {screen_w} }});
  Object.defineProperty(screen, 'availHeight', {{ get: () => {screen_h} - 40 }});
  Object.defineProperty(window, 'outerWidth',  {{ get: () => {screen_w} }});
  Object.defineProperty(window, 'outerHeight', {{ get: () => {screen_h} }});
}})();
"""

# Common desktop resolutions — viewport is always slightly smaller
_SCREEN_SIZES = [
    (1920, 1080, 1440, 900),   # screen_w, screen_h, vp_w, vp_h
    (2560, 1440, 1440, 900),
    (1680, 1050, 1440, 900),
    (1440, 900,  1280, 800),
    (1920, 1200, 1440, 900),
]


def _make_context(p):
    """
    Return a (browser, context) pair with a fully randomised stealth profile.
    Every call picks new hardware/screen values so sequential searches have
    different fingerprints.
    """
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
    """
    Visit the Southwest homepage first so Akamai can issue its session cookies
    (ak_bmsc, bm_sz, bm_sv) before we hit the booking/calendar endpoint.
    Also adds a human-like pause to let JS challenges complete.
    """
    try:
        page.goto(_SW_HOME, wait_until="domcontentloaded", timeout=30_000)
        time.sleep(random.uniform(1.5, 3.5))
    except Exception:
        pass  # warm-up failure is non-fatal; proceed to the real page


def build_search_url(origin: str, destination: str, date: str) -> str:
    """date format: YYYY-MM-DD"""
    params = (
        f"adultsCount=1&adultPassengersCount=1"
        f"&originationAirportCode={origin}"
        f"&destinationAirportCode={destination}"
        f"&departureDate={date}"
        f"&departureTimeOfDay=ALL_DAY"
        f"&fareType=POINTS"
        f"&int=HOMEQBOMAIR"
        f"&passengerType=ADULT"
        f"&promoCode="
        f"&returnDate="
        f"&returnTimeOfDay=ALL_DAY"
        f"&tripType=oneway"
    )
    return f"{_SEARCH_PAGE_BASE}?{params}"


def build_calendar_url(origin: str, destination: str, month_start: str) -> str:
    """month_start format: YYYY-MM-01 (first day of the target month)"""
    params = (
        f"adultsCount=1&adultPassengersCount=1"
        f"&originationAirportCode={origin}"
        f"&destinationAirportCode={destination}"
        f"&departureDate={month_start}"
        f"&currencyCode=POINTS"
        f"&hasNearByAirport=false"
        f"&lapInfantPassengersCount=0"
        f"&passengerType=ADULT"
        f"&promoCode="
        f"&returnAirportCode="
        f"&returnDate="
        f"&selectedFlight1={month_start}"
        f"&selectedFlight2="
        f"&tripType=oneway"
    )
    return f"{_CALENDAR_PAGE_BASE}?{params}"


def fetch_award_data(origin: str, destination: str, date: str) -> dict | None:
    """
    Navigate to the Southwest award search page with a headless browser,
    intercept the internal shopping API call, and return the parsed JSON body.

    Returns None if no matching API response is captured before timeout.
    """
    page_url = build_search_url(origin, destination, date)

    with sync_playwright() as p:
        browser, context = _make_context(p)
        page = context.new_page()
        try:
            _warm_up(page)
            with page.expect_response(
                lambda r: _SHOPPING_URL_FRAGMENT in r.url and r.status == 200,
                timeout=90_000,
            ) as response_info:
                page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            return response_info.value.json()
        except Exception:
            return None
        finally:
            browser.close()


def fetch_calendar_data(origin: str, destination: str, month_start: str) -> dict | None:
    """
    Navigate to the Southwest Low Fare Calendar page and intercept the internal
    calendar API call.  Returns the full month's per-day fare data as a dict,
    or None if the API response is not captured before timeout.

    month_start: first day of the target month, e.g. "2026-08-01"
    """
    page_url = build_calendar_url(origin, destination, month_start)

    with sync_playwright() as p:
        browser, context = _make_context(p)
        page = context.new_page()
        try:
            _warm_up(page)
            with page.expect_response(
                lambda r: _CALENDAR_URL_FRAGMENT in r.url and r.status == 200,
                timeout=90_000,
            ) as response_info:
                page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            return response_info.value.json()
        except Exception:
            return None
        finally:
            browser.close()
