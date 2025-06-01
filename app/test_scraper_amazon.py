import requests
from bs4 import BeautifulSoup

# Arama terimi
query = "headphones"
url = f"https://www.amazon.com/s?k={query}"

# Gerçekçi User-Agent ile istek yapalım
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    print("❌ HTTP Error:", response.status_code)
    exit()

# Sayfa içeriğini al
soup = BeautifulSoup(response.text, "html.parser")

# # Ürünleri bul (HTML yapısına göre güncelle!)
# products = soup.select("div.s-main-slot div.s-result-item")

# print(f"✅ Toplam Ürün: {len(products)}")

# list_items = soup.select('div.s-main-slot div[role="listitem"]')
# print(f"✅ Toplam Ürün: {len(list_items)}")


# for i, list_item in enumerate(list_items[:3], start=1):
#     title = list_item.select_one("h2 span")
#     review_count_elem = list_item.select_one("span[data-component-type='s-client-side-analytics']")
    # image_tag = list_item.select_one("img.s-image")
    # link_tag = list_item.select_one("a")
    # price_whole = list_item.select_one(".a-price .a-offscreen")
    # rating = list_item.select_one("i.a-icon-star-small span")

    # print(f"\n🍑 Ürün {i}")
    # print("Başlık:", title.get_text(strip=True) if title else "Yok")
    # print("Review:", review_count_elem.get_text(strip=True) if review_count_elem else "Yok")
    # print("Image:", image_tag.get("src") if title else "Yok")
    # print("Link:", link_tag["href"] if link_tag else "Yok")
    # print("Fiyat :", price_whole.get_text(strip=True) if price_whole else "Yok")
    # print("Puan  :", rating.get_text(strip=True) if rating else "Yok")


current_hash = soup.select_one("div.s-main-slot").prettify()
print(current_hash)