from playwright.sync_api import sync_playwright

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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto(page_url, wait_until="networkidle", timeout=60_000)
        rows = page.evaluate(_EXTRACT_JS)
        browser.close()

    return rows or []
