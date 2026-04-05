import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime
from html import unescape

import feedparser
import requests
from openai import OpenAI

# =========================
# Configuración general
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# Usamos 4o-mini por estabilidad absoluta en el Tier Pago
MODEL_NAME = "gpt-4o-mini"

TARGET_MIN_ITEMS = 8
TARGET_MAX_ITEMS = 12
MAX_ITEMS_PER_FEED = 10
MAX_PER_MEDIO = 2  # Mantiene la variedad de fuentes

AI_MAX_REQUESTS = 12
SLEEP_BETWEEN_AI_CALLS = 1
REQUEST_TIMEOUT_SECONDS = 20

# Balanceamos: Impacto cotidiano es la prioridad
WEIGHT_IMPACTO = 0.70 
WEIGHT_NOVEDAD = 0.30
MIN_RELEVANCE_SCORE = 18.0

# Mix Estratégico: Prestigio + Divulgación Ágil
FEEDS = [
    {"medio": "Harvard Health", "url": "https://www.health.harvard.edu/blog/feed", "idioma": "en"},
    {"medio": "Pew Research", "url": "https://www.pewresearch.org/feed/", "idioma": "en"},
    {"medio": "Scientific American", "url": "https://www.scientificamerican.com/section/reuters/index.xml", "idioma": "en"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml", "idioma": "en"},
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/", "idioma": "es"},
    {"medio": "Xataka", "url": "http://feeds.weblogssl.com/xataka2", "idioma": "es"},
    {"medio": "Psychology Today", "url": "https://www.psychologytoday.com/intl/front/feed", "idioma": "en"},
    {"medio": "Wired Science", "url": "https://www.wired.com/feed/category/science/latest/rss", "idioma": "en"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "idioma": "en"}
]

PROMPT_SISTEMA = """
Eres el socio estratégico de Santiago González (Santula). Tu tarea es analizar noticias basadas en evidencia pero con interés masivo.
Devuelve una FICHA DE PRODUCCIÓN PARA REELS en ESPAÑOL con este formato exacto:

ÁNGULO EDITORIAL: (Enfoque humano y estratégico: ¿Por qué esto le importa a alguien que está en su casa hoy?)
HOOK: (Frase rompedora de 3 segundos para el inicio del video)
EL DATO: (La evidencia o estudio explicado de forma ultra simple)
BAJADA SANTULA: (Cómo aterrizar esto a la realidad paraguaya o cotidiana)
REF. CULTURA: (Opcional: Una película, libro o frase histórica que ayude a ilustrar el punto)

Reglas:
- Tono profesional, humano y directo. Sin "hype" innecesario.
- Traduce del inglés al español de forma natural.
"""

# Keywords optimizadas para "Historias Útiles"
IMPACTO_KEYWORDS = [
    "salud", "dinero", "hábitos", "sueño", "cerebro", "hijos", "trabajo", "alimentación",
    "estrés", "tecnología", "celular", "tiempo", "longevidad", "bienestar", "apps",
    "vida", "cotidiano", "ahorro", "decisiones", "productivity", "mental", "brain",
    "health", "money", "habits", "parenting", "work", "stress", "longevity"
]

NOVEDAD_KEYWORDS = [
    "estudio", "investigación", "descubrimiento", "nuevo", "sorprendente", "ciencia",
    "hallazgo", "avance", "dato", "study", "research", "discovery", "new", "data"
]

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsLensBot/1.0)"}
CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def normalize_text(value: str) -> str:
    clean = unescape(value or "")
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()

def compute_relevance_score(title: str, summary: str) -> float:
    merged = f"{title} {summary}".lower()
    impacto = sum(15 for kw in IMPACTO_KEYWORDS if kw in merged)
    novedad = sum(10 for kw in NOVEDAD_KEYWORDS if kw in merged)
    score = (min(100, impacto) * WEIGHT_IMPACTO) + (min(100, novedad) * WEIGHT_NOVEDAD)
    return max(0.0, min(100.0, round(score, 2)))

def generate_ai_ficha(title, summary, medio, score):
    if not CLIENT: return None
    try:
        response = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": f"Medio: {medio}\nTítulo: {title}\nResumen: {summary[:1000]}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"     ❌ Error API OpenAI: {e}")
        return None

def curar_noticias():
    print(f"--- Iniciando NewsLens: {datetime.now().strftime('%H:%M:%S')} ---")
    candidates = []
    seen_links = set()

    for feed in FEEDS:
        print(f"Leyendo: {feed['medio']}...")
        try:
            resp = requests.get(feed["url"], headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
                link = entry.get("link", "").strip()
                if not link or link in seen_links: continue
                
                title = normalize_text(entry.get("title", ""))
                summary = normalize_text(entry.get("summary", entry.get("description", "")))
                score = compute_relevance_score(title, summary)
                
                if score >= MIN_RELEVANCE_SCORE:
                    candidates.append({
                        "titulo": title, "link": link, "medio": feed["medio"],
                        "idioma": feed["idioma"], "fecha": datetime.now().strftime("%d/%m/%Y"),
                        "summary": summary, "score": score
                    })
                    seen_links.add(link)
        except Exception as e:
            print(f"⚠️ Error feed {feed['medio']}: {e}")

    candidates.sort(key=lambda x: x["score"], reverse=True)
    counts = defaultdict(int)
    selected = []
    for c in candidates:
        if counts[c["medio"]] < MAX_PER_MEDIO and len(selected) < TARGET_MAX_ITEMS:
            selected.append(c)
            counts[c["medio"]] += 1

    articulos_curados = []
    ai_requests = 0

    for item in selected:
        ficha = None
        provider = "fallback"
        if ai_requests < AI_MAX_REQUESTS:
            print(f"  -> Procesando IA: {item['titulo'][:50]}...")
            ficha = generate_ai_ficha(item["titulo"], item["summary"], item["medio"], item["score"])
            if ficha:
                provider = "openai"
                ai_requests += 1
            time.sleep(SLEEP_BETWEEN_AI_CALLS)

        # Si la IA falla, construimos un mini resumen para no dejar el hueco
        if not ficha:
            ficha = f"ÁNGULO: Noticia relevante de {item['medio']}.\nEL DATO: {item['summary'][:250]}..."

        articulos_curados.append({
            "titulo": item["titulo"], "link": item["link"], "medio": item["medio"],
            "idioma": item["idioma"], "fecha": item["fecha"], "score": item["score"],
            "provider": provider, "ficha": ficha
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    print(f"--- Éxito: {len(articulos_curados)} noticias guardadas ---")

if __name__ == "__main__":
    curar_noticias()
