import urllib.request
import re
import json
from xml.sax.saxutils import escape

BASE = "https://xn----8sbalvbf1agi9b8d7b0b.xn--p1ai"
CATEGORIES = ["/%D0%B1%D0%B0%D0%B4", "/%D0%BA%D1%80%D0%B0%D1%81%D0%BE%D1%82%D0%B0",
              "/%D1%87%D0%B8%D1%81%D1%82%D0%BE%D1%82%D0%B0", "/%D0%BF%D1%80%D0%B8%D0%B1%D0%BE%D1%80%D1%8B"]
BLACKLIST = {"/бад", "/красота", "/чистота", "/приборы", "/cart", "/dostavka", "/privacy", "/register", "/thankyou", "/item"}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")

def is_product_link(path):
    decoded = urllib.parse.unquote(path).lower()
    if decoded in BLACKLIST or "?" in decoded or decoded in ("", "/"):
        return False
    return True

import urllib.parse
product_urls = set()
for cat in CATEGORIES:
    try:
        html = fetch(BASE + cat)
        for href in re.findall(r'href="([^"]+)"', html):
            path = re.sub(r'^https?://[^/]+', '', href)
            if path.startswith("/") and is_product_link(path):
                product_urls.add(BASE + path)
    except Exception:
        pass

offers = []
for url in product_urls:
    try:
        html = fetch(url)
        m = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', html)
        if not m:
            continue
        data = json.loads(m.group(1))
        if data.get("@type") != "Product":
            continue
        offers.append({
            "id": data.get("sku", ""),
            "url": (data.get("offers") or {}).get("url", url),
            "price": (data.get("offers") or {}).get("price", ""),
            "name": data.get("name", ""),
            "picture": data.get("image", ""),
            "description": (data.get("description", "") or "")[:3000],
        })
    except Exception:
        pass

parts = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<yml_catalog date="2026-01-01 00:00">', '<shop>',
         '<name>Тяньши</name>', '<company>Тяньши</company>',
         '<url>https://тяньши-магазин.рф/</url>',
         '<currencies><currency id="RUB" rate="1"/></currencies>',
         '<categories><category id="1">Тяньши</category></categories>', '<offers>']

for o in offers:
    parts.append(f'''<offer id="{escape(str(o['id']))}" available="true">
<url>{escape(o['url'])}</url>
<price>{escape(str(o['price']))}</price>
<currencyId>RUB</currencyId>
<categoryId>1</categoryId>
<picture>{escape(o['picture'])}</picture>
<name>{escape(o['name'])}</name>
<description>{escape(o['description'])}</description>
</offer>''')

parts.append('</offers></shop></yml_catalog>')

with open("feed.xml", "w", encoding="utf-8") as f:
    f.write("\n".join(parts))

print(f"Готово: {len(offers)} товаров")
