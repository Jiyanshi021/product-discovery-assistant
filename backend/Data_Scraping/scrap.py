# import os
# import re
# from typing import List, Dict, Optional
# from urllib.parse import urljoin

# import httpx
# from bs4 import BeautifulSoup
# from dotenv import load_dotenv
# from fastapi import HTTPException

# # ---------- CONFIG ----------

# load_dotenv()

# SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
# if not SCRAPER_API_KEY:
#     raise RuntimeError("SCRAPER_API_KEY environment variable is not set.")

# SCRAPER_API_BASE = "http://api.scraperapi.com"
# HUNNIT_BASE = "https://hunnit.com"

# # Old default – ab bhi use kar sakte ho agar sirf bestseller chahiye ho
# HUNNIT_COLLECTION_URL = f"{HUNNIT_BASE}/collections/bestseller"


# # ---------- LOW-LEVEL HELPERS ----------

# def fetch_html(url: str, render: bool = False) -> str:
#     """
#     Fetch HTML for any URL using ScraperAPI.
#     """
#     params = {
#         "api_key": SCRAPER_API_KEY,
#         "url": url,
#     }
#     if render:
#         params["render"] = "true"

#     try:
#         with httpx.Client(timeout=40) as client:
#             r = client.get(SCRAPER_API_BASE, params=params)
#             r.raise_for_status()
#     except httpx.HTTPError as e:
#         raise HTTPException(status_code=502, detail=f"ScraperAPI error for {url}: {e}")

#     return r.text


# def clean_text(s: str) -> str:
#     return " ".join(s.split()).strip()


# # ---------- COLLECTION PAGE PARSING ----------

# def get_product_links_from_collection(
#     collection_url: str,
#     max_products: int = 40,
# ) -> List[str]:
#     """
#     From a Hunnit collection page, collect unique product URLs.
#     We detect any <a> whose href contains '/products/'.

#     collection_url: full URL of a collection
#     """
#     html = fetch_html(collection_url)
#     soup = BeautifulSoup(html, "html.parser")

#     links: List[str] = []
#     seen_handles = set()

#     for a in soup.find_all("a", href=True):
#         href = a["href"]
#         if "/products/" not in href:
#             continue

#         full_url = urljoin(HUNNIT_BASE, href.split("?")[0])

#         # dedupe based on product handle
#         handle = full_url.rstrip("/").split("/")[-1]
#         if handle in seen_handles:
#             continue

#         seen_handles.add(handle)
#         links.append(full_url)

#         if len(links) >= max_products:
#             break

#     if not links:
#         raise HTTPException(
#             status_code=404,
#             detail=f"No product links found on collection page: {collection_url}",
#         )

#     return links


# # ---------- PRODUCT PAGE PARSING ----------

# def extract_title(soup: BeautifulSoup) -> Optional[str]:
#     """
#     First <h1> is usually the product title.
#     """
#     h1 = soup.find("h1")
#     if h1 and h1.get_text(strip=True):
#         return clean_text(h1.get_text())
#     if soup.title and soup.title.string:
#         return clean_text(soup.title.string)
#     return None


# def extract_price(soup: BeautifulSoup) -> Optional[float]:
#     """
#     Try to find a price number like '₹ 2,099' or 'Rs. 2,099.00'
#     We'll search entire text and take the first number that looks like a price.
#     """
#     full_text = soup.get_text(" ", strip=True)
#     m = re.search(r"(?:₹|Rs\.?)\s*([\d,]+(?:\.\d+)?)", full_text)
#     if not m:
#         return None
#     raw = m.group(1).replace(",", "")
#     try:
#         return float(raw)
#     except ValueError:
#         return None


# def extract_features(soup: BeautifulSoup) -> Dict[str, List[str]]:
#     """
#     Gather bullets under 'Product Features', 'Fabric Features', 'Function'.
#     Return dict: {"product_features": [...], "fabric_features": [...], "function": [...]}
#     """
#     features = {
#         "product_features": [],
#         "fabric_features": [],
#         "function": [],
#     }

#     def collect_under_heading(heading_regex, key: str):
#         heading = soup.find(string=re.compile(heading_regex, re.I))
#         if not heading:
#             return
#         parent = heading.parent
#         # find next <ul> or list of <li>
#         ul = parent.find_next("ul")
#         if ul:
#             for li in ul.find_all("li"):
#                 txt = clean_text(li.get_text())
#                 if txt:
#                     features[key].append(txt)
#         else:
#             # fallback: consecutive <li> siblings
#             lis = []
#             node = parent
#             for _ in range(40):
#                 node = node.find_next()
#                 if not node:
#                     break
#                 if node.name == "li":
#                     lis.append(node)
#                 elif lis:
#                     break
#             for li in lis:
#                 txt = clean_text(li.get_text())
#                 if txt:
#                     features[key].append(txt)

#     collect_under_heading(r"Product Features", "product_features")
#     collect_under_heading(r"Fabric Features", "fabric_features")
#     collect_under_heading(r"Function", "function")

#     return features


# def extract_main_image_url(soup: BeautifulSoup, title: Optional[str]) -> Optional[str]:
#     """
#     Try to find a primary product image:
#     - Prefer <img> whose alt contains the product title
#     - Fallback to first CDN-ish image from hunnit.com / shopify
#     """
#     if title:
#         img = soup.find("img", alt=lambda a: a and title.lower() in a.lower())
#         if img and img.get("src"):
#             return urljoin(HUNNIT_BASE, img["src"])

#     for img in soup.find_all("img", src=True):
#         src = img["src"]
#         if "hunnit.com" in src or "cdn.shopify.com" in src:
#             return urljoin(HUNNIT_BASE, src)

#     return None


# # ---------- CLEAN DESCRIPTION BUILDER ----------

# def build_clean_description(
#     title: Optional[str],
#     price: Optional[float],
#     category: Optional[str],
#     features: Dict[str, List[str]],
# ) -> str:
#     """
#     Build a clean, human-readable description from title + price + features.
#     No JS/CSS, no noisy text. Perfect for frontend rendering + embeddings.
#     """
#     pf = features.get("product_features") or []
#     ff = features.get("fabric_features") or []

#     parts: List[str] = []

#     # 1) Opening sentence
#     if title and category and price:
#         parts.append(f"{title} – a bestselling {category.lower()} priced at ₹{int(price)}.")
#     elif title and category:
#         parts.append(f"{title} – a bestselling {category.lower()}.")
#     elif title:
#         parts.append(title)

#     # 2) Product features
#     if pf:
#         parts.append("Key features: " + "; ".join(pf))

#     # 3) Fabric features
#     if ff:
#         parts.append("Fabric details: " + "; ".join(ff))

#     return " ".join(parts).strip()


# # ---------- MAIN PARSER ----------

# def parse_hunnit_product(url: str, category: str = "Bestseller") -> Dict:
#     """
#     Parse a single product page into a clean, structured dict.

#     Returned structure:
#     {
#         "title": str | None,
#         "price": float | None,
#         "description": str (clean),
#         "features": { "product_features": [...], "fabric_features": [...], "function": [...] },
#         "image_url": str | None,
#         "category": category string,
#         "product_url": url
#     }
#     """
#     html = fetch_html(url)
#     soup = BeautifulSoup(html, "html.parser")

#     title = extract_title(soup)
#     price = extract_price(soup)
#     features = extract_features(soup)
#     image_url = extract_main_image_url(soup, title)

#     # 👇 Clean, generated description – no JS/CSS noise
#     description = build_clean_description(
#         title=title,
#         price=price,
#         category=category,
#         features=features,
#     )

#     product = {
#         "title": title,
#         "price": price,
#         "description": description,  # clean text
#         "features": features,        # full structured data
#         "image_url": image_url,
#         "category": category,
#         "product_url": url,
#     }

#     return product




import os
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import HTTPException

# ---------- CONFIG ----------

load_dotenv()

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
if not SCRAPER_API_KEY:
    raise RuntimeError("SCRAPER_API_KEY environment variable is not set.")

SCRAPER_API_BASE = "http://api.scraperapi.com"
HUNNIT_BASE = "https://hunnit.com"

# Old default bestseller collection
HUNNIT_COLLECTION_URL = f"{HUNNIT_BASE}/collections/bestseller"


# ---------- LOW-LEVEL HELPERS ----------

def fetch_html(url: str, render: bool = False) -> str:
    """
    Fetch HTML for any URL using ScraperAPI.
    """
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
    }
    if render:
        params["render"] = "true"

    try:
        with httpx.Client(timeout=40) as client:
            r = client.get(SCRAPER_API_BASE, params=params)
            r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"ScraperAPI error for {url}: {e}")

    return r.text


def clean_text(s: str) -> str:
    return " ".join(s.split()).strip()


# ---------- COLLECTION PAGE PARSING ----------

def get_product_links_from_collection(
    collection_url: str,
    max_products: int = 40,
) -> List[str]:
    """
    From a Hunnit collection page, collect unique product URLs.
    We detect any <a> whose href contains '/products/'.
    """
    html = fetch_html(collection_url)
    soup = BeautifulSoup(html, "html.parser")

    links: List[str] = []
    seen_handles = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/products/" not in href:
            continue

        full_url = urljoin(HUNNIT_BASE, href.split("?")[0])

        # dedupe based on product handle
        handle = full_url.rstrip("/").split("/")[-1]
        if handle in seen_handles:
            continue

        seen_handles.add(handle)
        links.append(full_url)

        if len(links) >= max_products:
            break

    if not links:
        raise HTTPException(
            status_code=404,
            detail=f"No product links found on collection page: {collection_url}",
        )

    return links


# ---------- PRODUCT PAGE PARSING ----------

def extract_title(soup: BeautifulSoup) -> Optional[str]:
    """
    First <h1> is usually the product title.
    """
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return clean_text(h1.get_text())
    if soup.title and soup.title.string:
        return clean_text(soup.title.string)
    return None


def extract_price(soup: BeautifulSoup) -> Optional[float]:
    """
    Try to find a price number like '₹ 2,099' or 'Rs. 2,099.00'
    We'll search entire text and take the first number that looks like a price.
    """
    full_text = soup.get_text(" ", strip=True)
    m = re.search(r"(?:₹|Rs\.?)\s*([\d,]+(?:\.\d+)?)", full_text)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def extract_features(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """
    Gather bullets under 'Product Features', 'Fabric Features', 'Function'.
    Return dict: {"product_features": [...], "fabric_features": [...], "function": [...]}
    """
    features = {
        "product_features": [],
        "fabric_features": [],
        "function": [],
    }

    def collect_under_heading(heading_regex, key: str):
        heading = soup.find(string=re.compile(heading_regex, re.I))
        if not heading:
            return
        parent = heading.parent
        # find next <ul> or list of <li>
        ul = parent.find_next("ul")
        if ul:
            for li in ul.find_all("li"):
                txt = clean_text(li.get_text())
                if txt:
                    features[key].append(txt)
        else:
            # fallback: consecutive <li> siblings
            lis = []
            node = parent
            for _ in range(40):
                node = node.find_next()
                if not node:
                    break
                if node.name == "li":
                    lis.append(node)
                elif lis:
                    break
            for li in lis:
                txt = clean_text(li.get_text())
                if txt:
                    features[key].append(txt)

    collect_under_heading(r"Product Features", "product_features")
    collect_under_heading(r"Fabric Features", "fabric_features")
    collect_under_heading(r"Function", "function")

    return features


def extract_main_image_url(soup: BeautifulSoup, title: Optional[str]) -> Optional[str]:
    """
    Try to find a primary product image:
    - Prefer <img> whose alt contains the product title
    - Fallback to first CDN-ish image from hunnit.com / shopify
    """
    if title:
        img = soup.find("img", alt=lambda a: a and title.lower() in a.lower())
        if img and img.get("src"):
            return urljoin(HUNNIT_BASE, img["src"])

    for img in soup.find_all("img", src=True):
        src = img["src"]
        if "hunnit.com" in src or "cdn.shopify.com" in src:
            return urljoin(HUNNIT_BASE, src)

    return None


# ---------- CLEAN DESCRIPTION BUILDER ----------

def build_clean_description(
    title: Optional[str],
    price: Optional[float],
    category: Optional[str],
    features: Dict[str, List[str]],
) -> str:
    """
    Build a clean, human-readable description from title + price + features.
    No JS/CSS, no noisy text. Perfect for frontend rendering + embeddings.
    """
    pf = features.get("product_features") or []
    ff = features.get("fabric_features") or []

    parts: List[str] = []

    # 1) Opening sentence
    if title and category and price:
        parts.append(f"{title} – a bestselling {category.lower()} priced at ₹{int(price)}.")
    elif title and category:
        parts.append(f"{title} – a bestselling {category.lower()}.")
    elif title:
        parts.append(title)

    # 2) Product features
    if pf:
        parts.append("Key features: " + "; ".join(pf))

    # 3) Fabric features
    if ff:
        parts.append("Fabric details: " + "; ".join(ff))

    return " ".join(parts).strip()


# ---------- MAIN PARSER ----------

def parse_hunnit_product(url: str, category: str = "Bestseller") -> Dict:
    """
    Parse a single product page into a clean, structured dict.
    """
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)
    price = extract_price(soup)
    features = extract_features(soup)
    image_url = extract_main_image_url(soup, title)

    description = build_clean_description(
        title=title,
        price=price,
        category=category,
        features=features,
    )

    product = {
        "title": title,
        "price": price,
        "description": description,
        "features": features,
        "image_url": image_url,
        "category": category,
        "product_url": url,
    }

    return product
