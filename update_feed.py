import urllib.request
import urllib.parse
import re
import json
from xml.sax.saxutils import escape

BASE = "https://xn----8sbalvbf1agi9b8d7b0b.xn--p1ai"
CATEGORIES = ["/%D0%B1%D0%B0%D0%B4", "/%D0%BA%D1%80%D0%B0%D1%81%D0%BE%D1%82%D0%B0",
              "/%D1%87%D0%B8%D1%81%D1%82%D0%BE%D1%82%D0%B0", "/%D0%BF%D1%80%D0%B8%D0%B1%D0%BE%D1%80%D1%8B"]
BLACKLIST = {"/бад", "/красота", "/чистота", "/приборы", "/cart", "/dostavka", "/privacy", "/register", "/thankyou", "/item"}
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")

def safe_url(url):
    # Кодируем путь (кириллицу) в проценты, чтобы urllib смог отправить запрос
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parsed.path, safe="/%")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))

def fetch(url):
    req = urllib.request.Request(safe_url(url), headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9"
    })
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")

def is_product_link(path):
    decoded = urllib.parse.unquote(path).lower()
    if decoded in BLACKLIST or "?" in decoded or decoded in ("", "/"):
        return False
    if "disk2" in decoded or decoded.endswith(IMAGE_EXT):
        return False
    if "/" in decoded[1:]:  # вложенные пути типа /disk2/xx/yy — не товар
        return False
    return True

product_urls = set()
for cat in CATEGORIES:
    url = BASE + cat
    try:
        html = fetch(url)
        print(f"Категория {url}: получено {len(html)} символов HTML")
        hrefs = re.findall(r'href="([^"]+)"', html)
        print(f"  найдено href-ссылок всего: {len(hrefs)}")
        found_here = 0
        for href in hrefs:
            path = re.sub(r'^https?://[^/]+', '', href)
            if path.startswith("/") and is_product_link(path):
                product_urls.add(BASE + path)
                found_here += 1
        print(f"  из них товарных: {found_here}")
    except Exception as e:
        print(f"ОШИБКА при загрузке категории {url}: {repr(e)}")

print(f"\nИтого уникальных товарных ссылок: {len(product_urls)}\n")

offers = []
for url in product_urls:
    try:
        html = fetch(url)
        m = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', html)
        if not m:
            print(f"Нет JSON-LD на странице: {url}")
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
    except Exception as e:
        print(f"ОШИБКА на товаре {url}: {repr(e)}")

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

print(f"\nГотово: {len(offers)} товаров записано в feed.xml")
