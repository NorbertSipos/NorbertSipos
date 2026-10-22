#!/usr/bin/env python3
"""Local portfolio tracker. Stdlib only: python3 server.py  ->  http://localhost:8000"""
import json, os, sys, time, threading, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8000))
UA = {"User-Agent": "Mozilla/5.0 (portfolio-tracker)"}
FX_SYMBOLS = ["EURRON=X", "EURUSD=X"]
_cache, _lock = {}, threading.Lock()


def load_portfolio():
    with open(os.path.join(ROOT, "portfolio.json"), encoding="utf-8") as f:
        return json.load(f)


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def cached(key, ttl, fn):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    try:
        val = fn()
    except Exception as e:  # serve stale data rather than failing the dashboard
        with _lock:
            if hit:
                return hit[1]
        return {"error": str(e)}
    with _lock:
        _cache[key] = (time.time(), val)
    return val


def quote(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=1d&interval=5m&includePrePost=true")
    res = json.loads(fetch(url))["chart"]["result"][0]
    m = res["meta"]
    price = m.get("regularMarketPrice")
    prev = m.get("chartPreviousClose") or m.get("previousClose")
    closes = [c for c in res["indicators"]["quote"][0].get("close", []) if c is not None]
    return {
        "symbol": symbol, "price": price, "prevClose": prev,
        "change": price - prev if price and prev else None,
        "changePct": (price - prev) / prev * 100 if price and prev else None,
        "currency": m.get("currency"), "marketState": m.get("marketState"),
        "exchange": m.get("fullExchangeName"), "dayHigh": m.get("regularMarketDayHigh"),
        "dayLow": m.get("regularMarketDayLow"), "time": m.get("regularMarketTime"),
        "spark": closes[-80:],
    }


def news(query, limit=8):
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
           + "&hl=en-US&gl=US&ceid=US:en")
    out = []
    for item in ET.fromstring(fetch(url)).iter("item"):
        src = item.find("source")
        try:
            ts = parsedate_to_datetime(item.findtext("pubDate")).timestamp()
        except Exception:
            ts = 0
        out.append({"title": item.findtext("title"), "link": item.findtext("link"),
                    "source": src.text if src is not None else "", "time": ts, "query": query})
        if len(out) >= limit:
            break
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(ROOT, "static"), **k)

    def log_message(self, *a):
        pass

    def send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/portfolio":
            return self.send_json(load_portfolio())
        if path == "/api/quotes":
            p = load_portfolio()
            syms = [h["symbol"] for a in p["accounts"] for h in a["holdings"]] + FX_SYMBOLS
            return self.send_json({s: cached("q:" + s, 10, lambda s=s: quote(s)) for s in syms})
        if path == "/api/news":
            p = load_portfolio()
            qs = [h["newsQuery"] for a in p["accounts"] for h in a["holdings"] if h.get("newsQuery")]
            qs += p.get("marketNews", [])
            items, seen = [], set()
            for q in qs:
                r = cached("n:" + q, 300, lambda q=q: news(q))
                if isinstance(r, list):
                    for it in r:
                        if it["title"] not in seen:
                            seen.add(it["title"]); items.append(it)
            items.sort(key=lambda i: -i["time"])
            return self.send_json(items[:60])
        return super().do_GET()


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Portfolio tracker running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
