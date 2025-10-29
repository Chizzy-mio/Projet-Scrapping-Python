from pathlib import Path
import requests
import pandas as pd
from scrapy import Selector

base_dir = Path.cwd()
csv_dir = base_dir / "csv"
images_dir = base_dir / "images"
csv_dir.mkdir(exist_ok=True)
images_dir.mkdir(exist_ok=True)

url = "https://books.toscrape.com/"

rows = []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 ',
    "Accept-Language": "fr-FR,fr;q=0.9"
}

# Choisis ici la catégorie à garder :
target_category = "Politics" # ou ["Travel", "Politics"]

# -------- TOUS LES LIVRES (pagination) --------
page_url = url

while page_url:
    sel_page = Selector(text=requests.get(page_url, headers=headers, timeout=10).text)

    for book in sel_page.css("article.product_pod"):
        # Titre du livre
        title = book.css("h3 a::attr(title)").get()

        # L'url du livre (absolue et robuste)
        relative_link = book.css("h3 a::attr(href)").get()
        link = requests.compat.urljoin(page_url, relative_link) if relative_link else "No link"

        # Prix du livre
        price = book.css("p.price_color::text").get()

        # Stock du livre
        stock = ''.join(book.css("p.instock.availability::text").getall()).strip()

        # L'url de l'image (absolue)
        image_url = requests.compat.urljoin(page_url, book.css("div.image_container img::attr(src)").get())

        # Prendre upc et category de chaque livre
        book_page = Selector(text=requests.get(link, headers=headers, timeout=10).text)
        upc = book_page.xpath('//th[text()="UPC"]/following-sibling::td/text()').get()
        category = book_page.xpath('//ul[@class="breadcrumb"]/li[3]/a/text()').get()

        # Note du livre
        rating = book.css("p.star-rating::attr(class)").get()
        rating = rating.split(" ")[1] if rating else "No rating"

        if category != target_category:
            continue

        # Données CSV
        rows.append({
            "title": title,
            "link": link,
            "price": price,
            "stock": stock,
            "image_url": image_url,
            "category": category,
            "upc": upc,
            "rating": rating
        })

        #-----------------PRINT--------------------
        print("📽️ Title:", title)
        print("🔗 Link:", link)
        print("💰 Price:", price)
        print("✅ Stock:", stock)
        print("📷 URL Image:", image_url)
        print("📚 Category:", category)
        print("🔖 UPC:", upc)
        print("⭐ Rating:", rating)
        print("------")

    # Page suivante
    next_rel = sel_page.css("li.next a::attr(href)").get()
    page_url = requests.compat.urljoin(page_url, next_rel) if next_rel else None


all_quotes = []
page_count = 0
max_pages = 5  #
url = "http://quotes.toscrape.com/"

while url and page_count < max_pages:
    print(f"Scraping {url} ...")

    r = requests.get(url)
    response = Selector(text=r.text)
    page_count += 1

    quotes = response.css("span.text::text").getall()
    all_quotes.extend(quotes)

    next_page = response.css("li.next a::attr(href)").get()
    url = requests.compat.urljoin(url, next_page) if next_page else None

for i, quote in enumerate(all_quotes, 1):
    print(f"{i}. {quote}")


#-----------------CSV---------------

from pathlib import Path
import re

df = pd.DataFrame(rows).drop_duplicates(subset=["upc"])
outdir = Path("csv"); outdir.mkdir(exist_ok=True)

for cat, group in df.groupby("category", dropna=False):
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", (cat or "Unknown").strip())
    group.to_csv(outdir / f"categorie_{slug}.csv", index=False, encoding="utf-8-sig")

print("✅ Fichiers CSV par catégorie crée.")


#-----------------IMAGES---------------

from urllib.parse import urlparse
from os.path import splitext
import time

# Fonction de nettoyage de texte pour les noms de fichiers/dossiers
def slugify(s):
    return re.sub(r'[^A-Za-z0-9_-]+', '_', str(s or "Unknown")).strip('_')

# Dossier racine "images"
root_images = Path("images")
root_images.mkdir(exist_ok=True)

print("\n📸 Téléchargement des images...\n")

for _, row in df.iterrows():
    img_url = requests.compat.urljoin("https://books.toscrape.com/", str(row["image_url"]))
    category = slugify(row["category"])
    title_slug = slugify(row["title"])

    # Création automatique du sous-dossier par catégorie
    folder = root_images / category
    folder.mkdir(parents=True, exist_ok=True)

    # Nom du fichier image
    ext = splitext(urlparse(img_url).path)[1] or ".jpg"
    out_path = folder / f"{title_slug}{ext}"

    # Éviter les doublons (si deux titres identiques)
    i = 1
    while out_path.exists():
        out_path = folder / f"{title_slug}_{i}{ext}"
        i += 1

    # Téléchargement robuste avec gestion d’erreurs
    try:
        r = requests.get(img_url, headers=headers, timeout=(5, 20))
        r.raise_for_status()
        out_path.write_bytes(r.content)
        print(f"✅ Image enregistrée → {out_path}")
        time.sleep(0.1)  # petite pause pour ménager le site
    except Exception as e:
        print(f"Erreur téléchargement {row.get('title','(sans titre)')} : {e}")

print("\n📂 Téléchargement terminé — toutes les images sont classées dans 'images/<catégorie>/'")
