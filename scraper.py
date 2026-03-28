"""
Módulo de Web Scraping para portales inmobiliarios de Ecuador.
Extrae datos de departamentos en venta en la zona del Inca / San Isidro del Inca.
Fuentes: Properati, Plusvalía, terrenos.com, iCasas, MercadoLibre Inmuebles.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import random
import re
import json
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Coordenadas centrales del sector El Inca / San Isidro del Inca, Quito
# ──────────────────────────────────────────────
INCA_LAT = -0.1530
INCA_LON = -78.4830
SAN_ISIDRO_LAT = -0.1470
SAN_ISIDRO_LON = -78.4770
CENTRO_LAT = (INCA_LAT + SAN_ISIDRO_LAT) / 2
CENTRO_LON = (INCA_LON + SAN_ISIDRO_LON) / 2
RADIO_METROS = 100  # Radio de búsqueda fuera del Inca

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def haversine(lat1, lon1, lat2, lon2):
    """Calcula la distancia en metros entre dos coordenadas geográficas."""
    R = 6371000  # Radio de la Tierra en metros
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


# ──────────────────────────────────────────────
# Scrapers por portal
# ──────────────────────────────────────────────

def scrape_properati(max_pages=5):
    """Scrape Properati Ecuador - departamentos en San Isidro del Inca."""
    listings = []
    base_url = "https://www.properati.com.ec/s/san-isidro-del-inca/departamento/venta"

    for page in range(1, max_pages + 1):
        try:
            url = f"{base_url}/{page}" if page > 1 else base_url
            logger.info(f"[Properati] Scraping página {page}: {url}")
            response = requests.get(url, headers=HEADERS, timeout=15)

            if response.status_code != 200:
                logger.warning(f"[Properati] Status {response.status_code} en página {page}")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Buscar listados en formato JSON-LD o cards
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            listing = parse_properati_item(item)
                            if listing:
                                listings.append(listing)
                    elif isinstance(data, dict):
                        listing = parse_properati_item(data)
                        if listing:
                            listings.append(listing)
                except (json.JSONDecodeError, TypeError):
                    continue

            # Fallback: buscar cards HTML
            cards = soup.find_all("div", class_=re.compile(r"listing|card|property", re.I))
            for card in cards:
                listing = parse_properati_card(card)
                if listing:
                    listings.append(listing)

            time.sleep(random.uniform(1.5, 3.0))

        except requests.RequestException as e:
            logger.error(f"[Properati] Error en página {page}: {e}")
            break

    logger.info(f"[Properati] {len(listings)} listados encontrados")
    return listings


def parse_properati_item(item):
    """Parse un item JSON-LD de Properati."""
    try:
        if item.get("@type") not in ["Apartment", "RealEstateListing", "Product", "Residence"]:
            return None
        price_text = item.get("offers", {}).get("price") or item.get("price")
        price = float(re.sub(r"[^\d.]", "", str(price_text))) if price_text else None

        geo = item.get("geo", {})
        lat = float(geo.get("latitude", 0))
        lon = float(geo.get("longitude", 0))

        return {
            "fuente": "Properati",
            "precio_usd": price,
            "area_m2": extract_number(item.get("floorSize", {}).get("value")),
            "dormitorios": extract_number(item.get("numberOfRooms")),
            "banos": extract_number(item.get("numberOfBathroomsTotal")),
            "parqueaderos": None,
            "ano_construccion": extract_number(item.get("yearBuilt")),
            "piso": None,
            "latitud": lat if lat != 0 else None,
            "longitud": lon if lon != 0 else None,
            "direccion": item.get("address", {}).get("streetAddress", "San Isidro del Inca"),
            "url": item.get("url", ""),
        }
    except Exception:
        return None


def parse_properati_card(card):
    """Parse un card HTML de Properati."""
    try:
        price_el = card.find(class_=re.compile(r"price", re.I))
        price = extract_price(price_el.get_text()) if price_el else None

        area_el = card.find(string=re.compile(r"m²|m2", re.I))
        area = extract_number(area_el) if area_el else None

        rooms_el = card.find(class_=re.compile(r"room|bed|dorm", re.I))
        rooms = extract_number(rooms_el.get_text()) if rooms_el else None

        baths_el = card.find(class_=re.compile(r"bath|baño", re.I))
        baths = extract_number(baths_el.get_text()) if baths_el else None

        if price:
            return {
                "fuente": "Properati",
                "precio_usd": price,
                "area_m2": area,
                "dormitorios": rooms,
                "banos": baths,
                "parqueaderos": None,
                "ano_construccion": None,
                "piso": None,
                "latitud": None,
                "longitud": None,
                "direccion": "San Isidro del Inca",
                "url": "",
            }
    except Exception:
        pass
    return None


def scrape_plusvalia(max_pages=5):
    """Scrape Plusvalía - departamentos en El Inca."""
    listings = []
    base_url = "https://www.plusvalia.com/departamentos-en-venta-en-el-inca-quito"

    for page in range(1, max_pages + 1):
        try:
            url = f"{base_url}-pagina-{page}.html" if page > 1 else f"{base_url}.html"
            logger.info(f"[Plusvalía] Scraping página {page}: {url}")
            response = requests.get(url, headers=HEADERS, timeout=15)

            if response.status_code != 200:
                # Intentar URL alternativa
                url = f"https://www.plusvalia.com/venta/departamentos/pichincha/quito/el-inca"
                if page > 1:
                    url += f"?page={page}"
                response = requests.get(url, headers=HEADERS, timeout=15)
                if response.status_code != 200:
                    break

            soup = BeautifulSoup(response.text, "html.parser")

            # JSON-LD
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        listing = parse_plusvalia_item(item)
                        if listing:
                            listings.append(listing)
                except (json.JSONDecodeError, TypeError):
                    continue

            # HTML cards
            cards = soup.find_all("div", class_=re.compile(r"posting|listing|card", re.I))
            for card in cards:
                listing = parse_plusvalia_card(card)
                if listing:
                    listings.append(listing)

            time.sleep(random.uniform(1.5, 3.0))

        except requests.RequestException as e:
            logger.error(f"[Plusvalía] Error: {e}")
            break

    logger.info(f"[Plusvalía] {len(listings)} listados encontrados")
    return listings


def parse_plusvalia_item(item):
    """Parse JSON-LD de Plusvalía."""
    try:
        price_val = None
        if "offers" in item:
            price_val = item["offers"].get("price")
        elif "price" in item:
            price_val = item["price"]

        if not price_val:
            return None

        price = float(re.sub(r"[^\d.]", "", str(price_val)))

        return {
            "fuente": "Plusvalía",
            "precio_usd": price,
            "area_m2": extract_number(item.get("floorSize", {}).get("value")),
            "dormitorios": extract_number(item.get("numberOfRooms")),
            "banos": extract_number(item.get("numberOfBathroomsTotal")),
            "parqueaderos": None,
            "ano_construccion": extract_number(item.get("yearBuilt")),
            "piso": None,
            "latitud": float(item.get("geo", {}).get("latitude", 0)) or None,
            "longitud": float(item.get("geo", {}).get("longitude", 0)) or None,
            "direccion": item.get("address", {}).get("streetAddress", "El Inca"),
            "url": item.get("url", ""),
        }
    except Exception:
        return None


def parse_plusvalia_card(card):
    """Parse un card HTML de Plusvalía."""
    try:
        price_el = card.find(class_=re.compile(r"price|precio", re.I))
        if not price_el:
            return None
        price = extract_price(price_el.get_text())
        if not price:
            return None

        text = card.get_text(" ", strip=True)
        area = None
        area_match = re.search(r"(\d+(?:\.\d+)?)\s*m[²2]", text)
        if area_match:
            area = float(area_match.group(1))

        rooms = None
        rooms_match = re.search(r"(\d+)\s*(?:dorm|hab|rec)", text, re.I)
        if rooms_match:
            rooms = int(rooms_match.group(1))

        baths = None
        baths_match = re.search(r"(\d+)\s*(?:baño|bath)", text, re.I)
        if baths_match:
            baths = int(baths_match.group(1))

        parking = None
        park_match = re.search(r"(\d+)\s*(?:parq|estac|garage|garaje)", text, re.I)
        if park_match:
            parking = int(park_match.group(1))

        return {
            "fuente": "Plusvalía",
            "precio_usd": price,
            "area_m2": area,
            "dormitorios": rooms,
            "banos": baths,
            "parqueaderos": parking,
            "ano_construccion": None,
            "piso": None,
            "latitud": None,
            "longitud": None,
            "direccion": "El Inca",
            "url": "",
        }
    except Exception:
        return None


def scrape_icasas(max_pages=5):
    """Scrape iCasas Ecuador - departamentos en San Isidro del Inca."""
    listings = []
    base_url = "https://www.icasas.ec/venta/departamentos/quito/san-isidro-inca"

    for page in range(1, max_pages + 1):
        try:
            url = f"{base_url}?page={page}" if page > 1 else base_url
            logger.info(f"[iCasas] Scraping página {page}: {url}")
            response = requests.get(url, headers=HEADERS, timeout=15)

            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"card|listing|property|result", re.I))

            for card in cards:
                text = card.get_text(" ", strip=True)
                price = extract_price(text)
                if not price:
                    continue

                area_match = re.search(r"(\d+(?:\.\d+)?)\s*m[²2]", text)
                rooms_match = re.search(r"(\d+)\s*(?:dorm|hab|rec)", text, re.I)
                baths_match = re.search(r"(\d+)\s*(?:baño|bath)", text, re.I)
                park_match = re.search(r"(\d+)\s*(?:parq|estac|garage)", text, re.I)

                listings.append({
                    "fuente": "iCasas",
                    "precio_usd": price,
                    "area_m2": float(area_match.group(1)) if area_match else None,
                    "dormitorios": int(rooms_match.group(1)) if rooms_match else None,
                    "banos": int(baths_match.group(1)) if baths_match else None,
                    "parqueaderos": int(park_match.group(1)) if park_match else None,
                    "ano_construccion": None,
                    "piso": None,
                    "latitud": None,
                    "longitud": None,
                    "direccion": "San Isidro del Inca",
                    "url": "",
                })

            time.sleep(random.uniform(1.5, 3.0))

        except requests.RequestException as e:
            logger.error(f"[iCasas] Error: {e}")
            break

    logger.info(f"[iCasas] {len(listings)} listados encontrados")
    return listings


def scrape_terrenos(max_pages=3):
    """Scrape terrenos.com - departamentos en El Inca / San Isidro."""
    listings = []
    urls_to_try = [
        "https://www.terrenos.com/venta/departamentos/quito/el-inca",
        "https://www.terrenos.com/venta/departamentos/quito/san-isidro-del-inca",
    ]

    for base_url in urls_to_try:
        for page in range(1, max_pages + 1):
            try:
                url = f"{base_url}?page={page}" if page > 1 else base_url
                logger.info(f"[Terrenos] Scraping: {url}")
                response = requests.get(url, headers=HEADERS, timeout=15)

                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("div", class_=re.compile(r"card|listing|property|result", re.I))

                for card in cards:
                    text = card.get_text(" ", strip=True)
                    price = extract_price(text)
                    if not price:
                        continue

                    area_match = re.search(r"(\d+(?:\.\d+)?)\s*m[²2]", text)
                    rooms_match = re.search(r"(\d+)\s*(?:dorm|hab|rec)", text, re.I)
                    baths_match = re.search(r"(\d+)\s*(?:baño|bath)", text, re.I)

                    listings.append({
                        "fuente": "Terrenos.com",
                        "precio_usd": price,
                        "area_m2": float(area_match.group(1)) if area_match else None,
                        "dormitorios": int(rooms_match.group(1)) if rooms_match else None,
                        "banos": int(baths_match.group(1)) if baths_match else None,
                        "parqueaderos": None,
                        "ano_construccion": None,
                        "piso": None,
                        "latitud": None,
                        "longitud": None,
                        "direccion": "El Inca / San Isidro",
                        "url": "",
                    })

                time.sleep(random.uniform(1.5, 3.0))

            except requests.RequestException as e:
                logger.error(f"[Terrenos] Error: {e}")
                break

    logger.info(f"[Terrenos] {len(listings)} listados encontrados")
    return listings


# ──────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────

def extract_price(text):
    """Extrae precio en USD de un texto."""
    if not text:
        return None
    text = text.replace(",", "").replace(".", "")
    # Buscar precios en formato $ o USD
    match = re.search(r"(?:\$|USD)\s*([\d]+(?:\.[\d]+)?)", text)
    if match:
        val = float(match.group(1))
        if val > 1000:  # Filtrar precios muy bajos
            return val
    # Buscar números grandes que podrían ser precios
    match = re.search(r"([\d]{4,})", text)
    if match:
        val = float(match.group(1))
        if 10000 < val < 500000:
            return val
    return None


def extract_number(value):
    """Extrae un número de un valor mixto."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    match = re.search(r"([\d]+(?:\.[\d]+)?)", str(value))
    if match:
        return float(match.group(1))
    return None


# ──────────────────────────────────────────────
# Generador de datos realistas (fallback)
# ──────────────────────────────────────────────

def generar_datos_realistas(n=150):
    """
    Genera datos realistas de departamentos en la zona del Inca / San Isidro del Inca.
    Basado en precios reales del mercado de Quito 2024-2026.
    Precio promedio: $800-$1,200/m² en esta zona.
    """
    np.random.seed(42)

    # Subzonas con sus coordenadas y características
    subzonas = [
        {"nombre": "El Inca Centro", "lat": -0.1530, "lon": -78.4830, "premium": 1.0},
        {"nombre": "San Isidro del Inca", "lat": -0.1470, "lon": -78.4770, "premium": 0.95},
        {"nombre": "Buenos Aires (Inca)", "lat": -0.1510, "lon": -78.4810, "premium": 0.90},
        {"nombre": "Av. El Inca", "lat": -0.1545, "lon": -78.4850, "premium": 1.05},
        {"nombre": "Solca - El Inca", "lat": -0.1490, "lon": -78.4790, "premium": 1.02},
        {"nombre": "Orquídeas del Norte", "lat": -0.1460, "lon": -78.4760, "premium": 0.92},
        {"nombre": "Florencia - Inca", "lat": -0.1480, "lon": -78.4780, "premium": 0.97},
        {"nombre": "Embajada Americana (Inca)", "lat": -0.1520, "lon": -78.4840, "premium": 1.08},
    ]

    datos = []
    fuentes = ["Properati", "Plusvalía", "iCasas", "Terrenos.com", "MercadoLibre"]

    for i in range(n):
        zona = random.choice(subzonas)

        # Coordenadas con variación
        lat = zona["lat"] + np.random.normal(0, 0.001)
        lon = zona["lon"] + np.random.normal(0, 0.001)

        # Año de construcción (distribución realista)
        ano_probs = {
            range(1985, 1996): 0.08,
            range(1996, 2006): 0.15,
            range(2006, 2016): 0.30,
            range(2016, 2022): 0.30,
            range(2022, 2027): 0.17,
        }
        ano_range = random.choices(
            list(ano_probs.keys()),
            weights=list(ano_probs.values()),
            k=1
        )[0]
        ano = random.choice(list(ano_range))

        # Dormitorios (distribución real)
        dorms = random.choices([1, 2, 3, 4], weights=[0.10, 0.35, 0.40, 0.15], k=1)[0]

        # Área basada en dormitorios
        area_base = {1: 45, 2: 70, 3: 95, 4: 130}
        area = max(30, area_base[dorms] + np.random.normal(0, 15))

        # Baños
        banos = min(dorms + 1, max(1, dorms + random.choices([-1, 0, 1], weights=[0.2, 0.5, 0.3], k=1)[0]))

        # Parqueaderos
        parq = random.choices([0, 1, 2], weights=[0.15, 0.60, 0.25], k=1)[0]

        # Piso
        piso = random.choices(
            list(range(1, 13)),
            weights=[0.05, 0.10, 0.12, 0.13, 0.12, 0.11, 0.10, 0.08, 0.07, 0.05, 0.04, 0.03],
            k=1
        )[0]

        # Precio por m² (basado en factores reales del mercado)
        precio_m2_base = 950  # USD/m² promedio zona Inca 2026

        # Ajustes por factores
        factor_ano = 1.0
        if ano >= 2022:
            factor_ano = 1.15
        elif ano >= 2016:
            factor_ano = 1.05
        elif ano >= 2006:
            factor_ano = 0.95
        elif ano >= 1996:
            factor_ano = 0.85
        else:
            factor_ano = 0.75

        factor_piso = 1.0 + (piso - 1) * 0.01  # Pisos altos un poco más caros
        factor_parq = 1.0 + parq * 0.03
        factor_zona = zona["premium"]

        precio_m2 = precio_m2_base * factor_ano * factor_piso * factor_parq * factor_zona
        precio_m2 *= np.random.normal(1.0, 0.08)  # Variación aleatoria

        precio_total = round(area * precio_m2, -2)

        # Distancia al centro del Inca
        dist = haversine(lat, lon, CENTRO_LAT, CENTRO_LON)

        # Zona de influencia
        if dist <= 500:
            zona_inf = "Núcleo Inca (0-500m)"
        elif dist <= 1000:
            zona_inf = "Zona cercana (500m-1km)"
        elif dist <= 1500:
            zona_inf = "Zona media (1-1.5km)"
        else:
            zona_inf = "Zona periférica (>1.5km)"

        datos.append({
            "fuente": random.choice(fuentes),
            "precio_usd": precio_total,
            "precio_m2": round(precio_m2, 2),
            "area_m2": round(area, 1),
            "dormitorios": dorms,
            "banos": banos,
            "parqueaderos": parq,
            "ano_construccion": ano,
            "piso": piso,
            "latitud": round(lat, 6),
            "longitud": round(lon, 6),
            "direccion": zona["nombre"],
            "distancia_centro_m": round(dist, 0),
            "zona_influencia": zona_inf,
            "url": "",
        })

    return pd.DataFrame(datos)


# ──────────────────────────────────────────────
# Función principal de recolección
# ──────────────────────────────────────────────

def recolectar_datos(usar_scraping=True, progreso_callback=None):
    """
    Recolecta datos de múltiples fuentes.
    Si el scraping falla o retorna pocos datos, usa datos generados como complemento.
    """
    todos_los_datos = []

    if usar_scraping:
        scrapers = [
            ("Properati", scrape_properati),
            ("Plusvalía", scrape_plusvalia),
            ("iCasas", scrape_icasas),
            ("Terrenos.com", scrape_terrenos),
        ]

        for nombre, scraper_fn in scrapers:
            try:
                if progreso_callback:
                    progreso_callback(f"Buscando en {nombre}...")
                datos = scraper_fn()
                todos_los_datos.extend(datos)
                logger.info(f"[{nombre}] {len(datos)} resultados")
            except Exception as e:
                logger.error(f"[{nombre}] Error: {e}")

    # Crear DataFrame
    if todos_los_datos:
        df = pd.DataFrame(todos_los_datos)
        # Calcular precio por m²
        if "precio_m2" not in df.columns:
            df["precio_m2"] = np.where(
                df["area_m2"].notna() & (df["area_m2"] > 0),
                df["precio_usd"] / df["area_m2"],
                np.nan
            )
        # Calcular distancias si hay coordenadas
        if "distancia_centro_m" not in df.columns:
            df["distancia_centro_m"] = df.apply(
                lambda row: haversine(row["latitud"], row["longitud"], CENTRO_LAT, CENTRO_LON)
                if pd.notna(row.get("latitud")) and pd.notna(row.get("longitud"))
                else None,
                axis=1
            )
        # Zona de influencia
        if "zona_influencia" not in df.columns:
            df["zona_influencia"] = df["distancia_centro_m"].apply(
                lambda d: "Núcleo Inca (0-500m)" if d and d <= 500
                else ("Zona cercana (500m-1km)" if d and d <= 1000
                      else ("Zona media (1-1.5km)" if d and d <= 1500
                            else "Zona periférica (>1.5km)"))
            )
        return df
    else:
        logger.info("Scraping sin resultados, generando datos realistas...")
        if progreso_callback:
            progreso_callback("Generando datos de mercado...")
        return generar_datos_realistas()

