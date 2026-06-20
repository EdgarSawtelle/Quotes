#!/usr/bin/env python3
"""
Collects image URLs for recent/random comics from XKCD, SMBC, and Poorly Drawn Lines,
and writes them to comics.js as `window.COMICS = [...]`.

Stores ONLY links — it does not download or re-host any comic image.
The display device loads each comic live from the creator's own server.
XKCD is Creative Commons (BY-NC); SMBC and Poorly Drawn Lines are linked, not copied.
"""
import json, random, re, sys
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (reTerminal personal e-paper display)"}
TIMEOUT = 20
IMG_RE = re.compile(r'\.(png|jpe?g|gif|webp)(\?|$)', re.I)

def valid_img(u):
    return isinstance(u, str) and u.startswith("http") and bool(IMG_RE.search(u))

def og_image(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    img = None
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', r.text, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text, re.I)
    if m:
        img = m.group(1)
    t = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', r.text, re.I)
    return img, (t.group(1) if t else ""), r.url

def get_xkcd(n=8):
    out = []
    try:
        latest = requests.get("https://xkcd.com/info.0.json", headers=HEADERS, timeout=TIMEOUT).json()["num"]
        for num in random.sample(range(1, latest + 1), min(n, latest)):
            try:
                d = requests.get(f"https://xkcd.com/{num}/info.0.json", headers=HEADERS, timeout=TIMEOUT).json()
                if valid_img(d.get("img")):
                    out.append({"source": "xkcd", "img": d["img"], "title": d.get("title", ""),
                                "link": f"https://xkcd.com/{num}"})
            except Exception as e:
                print("xkcd skip", num, e, file=sys.stderr)
    except Exception as e:
        print("xkcd error", e, file=sys.stderr)
    return out

def get_pdl(n=8):
    out, seen = [], set()
    for _ in range(n * 3):
        if len(out) >= n:
            break
        try:
            img, title, final = og_image("https://poorlydrawnlines.com/?random=true")
            if valid_img(img) and img not in seen:
                seen.add(img)
                out.append({"source": "poorlydrawnlines", "img": img, "title": title, "link": final})
        except Exception as e:
            print("pdl skip", e, file=sys.stderr)
    return out

def get_smbc(n=8):
    out, feed = [], ""
    for url in ("https://www.smbc-comics.com/comic/rss", "https://www.smbc-comics.com/rss.php"):
        try:
            feed = requests.get(url, headers=HEADERS, timeout=TIMEOUT).text
            if "smbc-comics.com/comic/" in feed:
                break
        except Exception as e:
            print("smbc rss skip", url, e, file=sys.stderr)
    seen = set()
    for link in re.findall(r"https://www\.smbc-comics\.com/comic/[A-Za-z0-9\-]+", feed):
        if len(out) >= n:
            break
        if link in seen:
            continue
        seen.add(link)
        try:
            img, title, final = og_image(link)
            if valid_img(img):
                out.append({"source": "smbc", "img": img, "title": title, "link": final})
        except Exception as e:
            print("smbc page skip", link, e, file=sys.stderr)
    return out

def main():
    comics = get_xkcd(8) + get_pdl(8) + get_smbc(8)
    comics = [c for c in comics if valid_img(c.get("img"))]   # final guard
    random.shuffle(comics)
    with open("comics.js", "w", encoding="utf-8") as f:
        f.write("window.COMICS = " + json.dumps(comics, ensure_ascii=False, indent=1) + ";\n")
    print(f"wrote {len(comics)} comics to comics.js")
    if not comics:
        sys.exit("No comics fetched — check the source endpoints.")

if __name__ == "__main__":
    main()
