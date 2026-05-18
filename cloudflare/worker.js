const MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";
const DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

function ok(body) {
  return new Response(JSON.stringify(body), {
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

function extractNextData(html) {
  const m = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
  if (!m) return null;
  try { return JSON.parse(m[1]); } catch { return null; }
}

function findProductArray(obj, depth) {
  if (depth > 8 || !obj || typeof obj !== "object") return null;
  if (Array.isArray(obj)) {
    if (obj.length > 0) {
      const first = obj[0];
      if (typeof first === "object" && first !== null &&
          (first.name || first.desc || first.product_name || first.display_name || first.productName) &&
          (first.price != null || first.mrp != null || first.sp != null ||
           first.discountedSellingPrice != null || first.sellingPrice != null ||
           (first.pricing && (first.pricing.np != null || first.pricing.mrp != null)))) {
        return obj;
      }
    }
    for (const item of obj) {
      const f = findProductArray(item, depth + 1);
      if (f) return f;
    }
  } else {
    const priorityKeys = [
      "objects", "prod_list", "products", "items", "results",
      "product_list", "productList", "searchResult", "productListings",
      "catalogItems", "skus", "variants",
    ];
    for (const key of priorityKeys) {
      if (obj[key]) {
        const f = findProductArray(obj[key], depth);
        if (f) return f;
      }
    }
    for (const [k, v] of Object.entries(obj)) {
      if (typeof v === "object" && v !== null && !priorityKeys.includes(k)) {
        const f = findProductArray(v, depth + 1);
        if (f) return f;
      }
    }
  }
  return null;
}

function parsePrice(p) {
  const raw = parseFloat(
    p.price ?? p.sp ?? p.mrp ?? p.discountedSellingPrice ?? p.sellingPrice ??
    p.pricing?.discount?.dsc_prc ?? p.pricing?.np ?? p.pricing?.mrp ?? 0
  );
  return raw > 5000 ? raw / 100 : raw;
}

function parseName(p) {
  return String(p.name || p.desc || p.product_name || p.display_name || p.productName || "").trim();
}

function parseUnit(p) {
  return String(
    p.unit || p.quantity || p.unit_quantity || p.unitQuantity ||
    p.w || p.qty || p.weight || p.pack_size || ""
  ).trim();
}

function parseImage(p) {
  return String(
    p.image || p.image_url || p.imageUrl || p.thumbnail ||
    (p.images?.[0]?.s) || (p.images?.[0]) || ""
  );
}

function toItems(raw, max) {
  const out = [];
  const seen = new Set();
  for (const p of (raw || [])) {
    if (out.length >= max) break;
    if (typeof p !== "object" || !p) continue;
    const name = parseName(p);
    const price = parsePrice(p);
    if (!name || !price || seen.has(name)) continue;
    seen.add(name);
    out.push({ name, price, unit: parseUnit(p), imageUrl: parseImage(p) });
  }
  return out;
}

// Build the Blinkit `gr` location cookie value (base64-encoded JSON)
function blinkitGrCookie(lat, lon) {
  const payload = JSON.stringify({
    lat: String(lat),
    lon: String(lon),
    society_id: "0",
    city_id: "608",
  });
  return btoa(payload);
}

// ── Scrapers ──────────────────────────────────────────────────────────────────

async function blinkit(q, lat, lon) {
  const gr = blinkitGrCookie(lat, lon);
  const commonHeaders = {
    "User-Agent": MOBILE_UA,
    Cookie: `gr=${gr}`,
    Origin: "https://blinkit.com",
    Referer: "https://blinkit.com/",
  };

  // 1. Try JSON search API with location cookie
  try {
    const r = await fetch(
      `https://blinkit.com/v6/search/?q=${encodeURIComponent(q)}&start=0&size=20`,
      {
        headers: {
          ...commonHeaders,
          app_client: "consumer_web",
          lat: String(lat),
          lon: String(lon),
          Accept: "application/json",
        },
      }
    );
    const text = await r.text();
    if (!text.trimStart().startsWith("<")) {
      const body = JSON.parse(text);
      const raw =
        body?.products?.objects ||
        body?.snippets ||
        body?.data?.products ||
        [];
      const items = toItems(raw, 5);
      if (items.length) return items;
    }
  } catch { /* fall through */ }

  // 2. HTML search page with location cookie + lat/lon in URL
  try {
    const r2 = await fetch(
      `https://blinkit.com/s/?q=${encodeURIComponent(q)}&lat=${lat}&lon=${lon}`,
      {
        headers: {
          ...commonHeaders,
          "User-Agent": DESKTOP_UA,
          Accept: "text/html",
          "Accept-Language": "en-IN,en;q=0.9",
        },
      }
    );
    const html = await r2.text();
    const nd = extractNextData(html);
    if (nd) {
      const raw = findProductArray(nd, 0);
      if (raw) {
        const items = toItems(raw, 5);
        if (items.length) return items;
      }
    }
    // 3. Also scan plain HTML for price patterns as a last resort
    const priceMatches = [...html.matchAll(/₹\s*(\d+(?:\.\d+)?)/g)];
    if (priceMatches.length > 0) {
      // Found prices in HTML but couldn't parse structure — return empty so UI shows no data
    }
  } catch { /* fall through */ }

  return [];
}

async function zepto(q, lat, lon) {
  // 1. Mobile JSON API
  try {
    const r = await fetch(
      `https://api.zeptonow.com/api/v1/search?query=${encodeURIComponent(q)}&pageNumber=0&pageSize=15&version=5`,
      {
        headers: {
          "User-Agent": MOBILE_UA,
          Accept: "application/json",
          appVersion: "10.6.2",
          deviceType: "3",
          storeType: "1",
          latitude: String(lat),
          longitude: String(lon),
        },
      }
    );
    const text = await r.text();
    if (!text.trimStart().startsWith("<")) {
      const body = JSON.parse(text);
      const raw = [];
      for (const sec of (body?.sections || body?.data?.sections || [])) {
        for (const item of (sec.items || [])) {
          const p = item.product || item;
          if (p?.name) raw.push(p);
        }
      }
      if (!raw.length) {
        for (const k of ["products", "items", "results"]) {
          if (Array.isArray(body[k])) { raw.push(...body[k]); break; }
        }
      }
      const items = toItems(raw, 5);
      if (items.length) return items;
    }
  } catch { /* fall through */ }

  // 2. Next.js HTML page
  try {
    const r2 = await fetch(
      `https://www.zeptonow.com/search?query=${encodeURIComponent(q)}`,
      {
        headers: {
          "User-Agent": DESKTOP_UA,
          Accept: "text/html",
          "Accept-Language": "en-IN,en;q=0.9",
        },
      }
    );
    const html = await r2.text();
    const nd = extractNextData(html);
    if (nd) {
      const raw = findProductArray(nd, 0);
      if (raw) return toItems(raw, 5);
    }
  } catch { /* fall through */ }

  return [];
}

async function bigbasket(q) {
  // 1. JSON listing API
  try {
    const r = await fetch(
      `https://www.bigbasket.com/listing-svc/v2/products/?type=ps&q=${encodeURIComponent(q)}&tab_type=%5B%22prd%22%5D&sorted_on=relevance`,
      {
        headers: {
          "User-Agent": DESKTOP_UA,
          Accept: "application/json",
          "x-channel": "web",
          Origin: "https://www.bigbasket.com",
          Referer: `https://www.bigbasket.com/ps/?q=${encodeURIComponent(q)}`,
        },
      }
    );
    const text = await r.text();
    if (!text.trimStart().startsWith("<")) {
      const body = JSON.parse(text);
      let raw = [];
      for (const tab of (body.tab_info || [body])) {
        if ((tab.prod_list || []).length) { raw = tab.prod_list; break; }
      }
      if (!raw.length) {
        for (const k of ["products", "data", "items", "results"]) {
          if (Array.isArray(body[k])) { raw = body[k]; break; }
        }
      }
      const items = toItems(raw, 5);
      if (items.length) return items;
    }
  } catch { /* fall through */ }

  // 2. Next.js HTML page
  try {
    const r2 = await fetch(
      `https://www.bigbasket.com/ps/?q=${encodeURIComponent(q)}`,
      {
        headers: {
          "User-Agent": DESKTOP_UA,
          Accept: "text/html",
          "Accept-Language": "en-IN,en;q=0.9",
        },
      }
    );
    const html = await r2.text();
    const nd = extractNextData(html);
    if (nd) {
      const raw = findProductArray(nd, 0);
      if (raw) return toItems(raw, 5);
    }
  } catch { /* fall through */ }

  return [];
}

async function instamart(q, lat, lon) {
  // 1. Swiggy Instamart search API
  try {
    const params = new URLSearchParams({
      pageNumber: "0",
      searchResultsOffset: "0",
      limit: "15",
      query: q,
      ageConsent: "false",
      layoutId: "3994",
      pageType: "INSTAMART_SEARCH_PAGE",
      isPreSearchTag: "false",
      highConfidencePageNo: "0",
      lowConfidencePageNo: "0",
    });
    const r = await fetch(`https://www.swiggy.com/api/instamart/search?${params}`, {
      headers: {
        "User-Agent": MOBILE_UA,
        Accept: "application/json",
        Origin: "https://www.swiggy.com",
        Referer: `https://www.swiggy.com/instamart/search?query=${encodeURIComponent(q)}`,
      },
    });
    const text = await r.text();
    if (!text.trimStart().startsWith("<")) {
      const body = JSON.parse(text);
      const raw = [];
      for (const w of (body?.data?.widgets || body?.widgets || [])) {
        raw.push(...(w?.data?.products || w?.products || []));
      }
      // Also try direct product arrays
      for (const k of ["products", "items", "results"]) {
        if (!raw.length && Array.isArray(body[k])) { raw.push(...body[k]); break; }
      }
      const items = toItems(raw, 5);
      if (items.length) return items;
    }
  } catch { /* fall through */ }

  // 2. Next.js HTML page
  try {
    const r2 = await fetch(
      `https://www.swiggy.com/instamart/search?query=${encodeURIComponent(q)}`,
      {
        headers: {
          "User-Agent": DESKTOP_UA,
          Accept: "text/html",
          "Accept-Language": "en-IN,en;q=0.9",
        },
      }
    );
    const html = await r2.text();
    const nd = extractNextData(html);
    if (nd) {
      const raw = findProductArray(nd, 0);
      if (raw) return toItems(raw, 5);
    }
  } catch { /* fall through */ }

  return [];
}

async function amazonfresh(q) {
  try {
    const r = await fetch(
      `https://www.amazon.in/s?k=${encodeURIComponent(q)}&i=grocery&rh=n%3A5940050031`,
      {
        headers: {
          "User-Agent": DESKTOP_UA,
          Accept: "text/html,application/xhtml+xml",
          "Accept-Language": "en-IN,en;q=0.9",
        },
      }
    );
    const html = await r.text();
    const out = [];
    const blocks = html.split('data-component-type="s-search-result"');
    for (let i = 1; i < blocks.length && out.length < 5; i++) {
      const b = blocks[i];
      const nm = b.match(/<h2[^>]*>[\s\S]*?<span[^>]*>([^<]{3,120})<\/span>/);
      const wm = b.match(/a-price-whole[^>]*>([\d,]+)/);
      const fm = b.match(/a-price-fraction[^>]*>(\d+)/);
      if (nm && wm) {
        const name = nm[1].replace(/&amp;/g, "&").replace(/&nbsp;/g, " ").trim();
        const price = parseFloat(wm[1].replace(/,/g, "") + "." + (fm?.[1] || "0"));
        if (name && price > 0) out.push({ name, price, unit: "", imageUrl: "" });
      }
    }
    return out;
  } catch { return []; }
}

async function flipkart(q, lat, lon) {
  // 1. Flipkart Minutes JSON API
  try {
    const r = await fetch(
      `https://minutes.flipkart.com/api/4/page?q=${encodeURIComponent(q)}&type=search`,
      {
        headers: {
          "User-Agent": MOBILE_UA,
          Accept: "application/json",
          "X-User-Agent": "FKUA/app/42/42.0/ios; Mobile",
          Origin: "https://minutes.flipkart.com",
        },
      }
    );
    const text = await r.text();
    if (!text.trimStart().startsWith("<")) {
      const body = JSON.parse(text);
      const raw =
        body?.data?.products ||
        body?.products ||
        body?.items ||
        findProductArray(body, 0) ||
        [];
      const items = toItems(raw, 5);
      if (items.length) return items;
    }
  } catch { /* fall through */ }

  // 2. Next.js HTML page
  try {
    const r2 = await fetch(
      `https://minutes.flipkart.com/search?q=${encodeURIComponent(q)}`,
      {
        headers: {
          "User-Agent": DESKTOP_UA,
          Accept: "text/html",
          "Accept-Language": "en-IN,en;q=0.9",
        },
      }
    );
    const html = await r2.text();
    const nd = extractNextData(html);
    if (nd) {
      const raw = findProductArray(nd, 0);
      if (raw) return toItems(raw, 5);
    }
  } catch { /* fall through */ }

  return [];
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }
    const url = new URL(request.url);
    const platform = url.pathname.replace(/^\//, "").toLowerCase();
    const q = url.searchParams.get("q") || "";
    const lat = parseFloat(url.searchParams.get("lat") || "19.076");
    const lon = parseFloat(url.searchParams.get("lon") || "72.877");

    if (!q) return ok({ error: "missing q" });

    try {
      let items;
      if      (platform === "blinkit")     items = await blinkit(q, lat, lon);
      else if (platform === "zepto")       items = await zepto(q, lat, lon);
      else if (platform === "bigbasket")   items = await bigbasket(q);
      else if (platform === "instamart")   items = await instamart(q, lat, lon);
      else if (platform === "amazonfresh") items = await amazonfresh(q);
      else if (platform === "flipkart")    items = await flipkart(q, lat, lon);
      else return ok({ error: "unknown platform" });

      return ok({ platform, query: q, items: items || [], error: null });
    } catch (e) {
      return ok({ platform, query: q, items: [], error: e.message });
    }
  },
};
