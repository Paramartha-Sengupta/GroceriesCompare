
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

async function blinkit(q, lat, lon) {
  const r = await fetch(
    `https://blinkit.com/v6/search/?q=${encodeURIComponent(q)}&start=0&size=20`,
    { headers: { app_client: "consumer_web", lat: String(lat), lon: String(lon),
        "User-Agent": MOBILE_UA, Accept: "application/json",
        Origin: "https://blinkit.com", Referer: "https://blinkit.com/" } }
  );
  const body = await r.json();
  const raw = body?.products?.objects || body?.snippets || [];
  const out = [];
  for (const p of raw) {
    if (out.length >= 5) break;
    const name = p.name || p.product_name || p.display_name || "";
    if (!name) continue;
    let price = parseFloat(p.price || p.mrp || p.sp || p?.pricing?.price || 0);
    if (price > 5000) price /= 100;
    if (!price) continue;
    out.push({ name: name.trim(), price, unit: String(p.unit || p.quantity || ""), imageUrl: p.image || p.image_url || "" });
  }
  return out;
}

async function zepto(q, lat, lon) {
  const r = await fetch(
    `https://api.zeptonow.com/api/v1/search?query=${encodeURIComponent(q)}&pageNumber=0&pageSize=15&version=5`,
    { headers: { "User-Agent": MOBILE_UA, Accept: "application/json",
        appVersion: "10.6.2", deviceType: "3", storeType: "1",
        latitude: String(lat), longitude: String(lon) } }
  );
  const body = await r.json();
  const raw = [];
  for (const sec of (body?.sections || body?.data?.sections || [])) {
    for (const item of (sec.items || [])) {
      const p = item.product || item;
      if (p?.name) raw.push(p);
    }
  }
  for (const key of ["products", "items", "results"]) {
    if (!raw.length && Array.isArray(body[key])) { raw.push(...body[key]); break; }
  }
  const out = [];
  for (const p of raw) {
    if (out.length >= 5) break;
    const name = p.name || p.product_name || "";
    if (!name) continue;
    let price = parseFloat(p.discountedSellingPrice || p.sellingPrice || p.price || 0);
    if (price > 5000) price /= 100;
    if (!price) continue;
    out.push({ name: name.trim(), price, unit: String(p.unitQuantity || p.quantity || ""), imageUrl: p.imageUrl || p.image || "" });
  }
  return out;
}

async function bigbasket(q) {
  const r = await fetch(
    `https://www.bigbasket.com/listing-svc/v2/products/?type=ps&q=${encodeURIComponent(q)}&tab_type=%5B%22prd%22%5D&sorted_on=relevance`,
    { headers: { "User-Agent": DESKTOP_UA, Accept: "application/json",
        "x-channel": "web", Origin: "https://www.bigbasket.com" } }
  );
  const body = await r.json();
  let raw = [];
  for (const tab of (body.tab_info || [body])) {
    if ((tab.prod_list || []).length) { raw = tab.prod_list; break; }
  }
  for (const key of ["products", "data", "items", "results"]) {
    if (!raw.length && Array.isArray(body[key])) { raw = body[key]; break; }
  }
  const out = [];
  for (const p of raw) {
    if (out.length >= 5) break;
    const name = p.desc || p.name || p.product_name || "";
    if (!name) continue;
    const disc = p?.pricing?.discount || {};
    const price = parseFloat(disc.dsc_prc || p?.pricing?.np || p.sp || p.price || p.mrp || 0);
    if (!price) continue;
    out.push({ name: name.trim(), price, unit: String(p.w || p.unit || p.qty || ""), imageUrl: (p.images || [{}])[0]?.s || p.image || "" });
  }
  return out;
}

async function instamart(q, lat, lon) {
  const params = new URLSearchParams({
    pageNumber: "0", searchResultsOffset: "0", limit: "15", query: q,
    ageConsent: "false", layoutId: "3994", pageType: "INSTAMART_SEARCH_PAGE",
    isPreSearchTag: "false", highConfidencePageNo: "0", lowConfidencePageNo: "0",
  });
  const r = await fetch(`https://www.swiggy.com/api/instamart/search?${params}`, {
    headers: { "User-Agent": MOBILE_UA, Accept: "application/json",
      Origin: "https://www.swiggy.com",
      Referer: `https://www.swiggy.com/instamart/search?query=${encodeURIComponent(q)}` }
  });
  const body = await r.json();
  const raw = [];
  for (const w of (body?.data?.widgets || body?.widgets || [])) {
    raw.push(...(w?.data?.products || w?.products || []));
  }
  const out = [];
  for (const p of raw) {
    if (out.length >= 5) break;
    const name = p.name || p.display_name || "";
    if (!name) continue;
    let price = parseFloat(p.price || p.instamart_price || p.mrp || 0);
    if (price > 5000) price /= 100;
    if (!price) continue;
    out.push({ name: name.trim(), price, unit: String(p.quantity || p.unit || ""), imageUrl: p.image_id || p.image || "" });
  }
  return out;
}

async function amazonfresh(q) {
  const r = await fetch(
    `https://www.amazon.in/s?k=${encodeURIComponent(q)}&i=grocery&rh=n%3A5940050031`,
    { headers: { "User-Agent": DESKTOP_UA, Accept: "text/html,application/xhtml+xml", "Accept-Language": "en-IN,en;q=0.9" } }
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
}

async function flipkart(q, lat, lon) {
  const r = await fetch(
    `https://minutes.flipkart.com/api/4/page?q=${encodeURIComponent(q)}&type=search`,
    { headers: { "User-Agent": MOBILE_UA, Accept: "application/json",
        "X-User-Agent": "FKUA/app/42/42.0/ios; Mobile",
        Origin: "https://minutes.flipkart.com" } }
  );
  const body = await r.json();
  const raw = body?.data?.products || body?.products || body?.items || [];
  const out = [];
  for (const p of raw) {
    if (out.length >= 5) break;
    const name = p.name || p.title || p.productName || "";
    if (!name) continue;
    let price = parseFloat(p.price || p.sellingPrice || p.finalPrice || p.mrp || 0);
    if (price > 5000) price /= 100;
    if (!price) continue;
    out.push({ name: name.trim(), price, unit: String(p.quantity || p.unit || ""), imageUrl: p.image || p.imageUrl || "" });
  }
  return out;
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    const url = new URL(request.url);
    const platform = url.pathname.replace(/^\//, "");
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
      return ok({ platform, query: q, items, error: null });
    } catch (e) {
      return ok({ platform, query: q, items: [], error: e.message });
    }
  }
};
