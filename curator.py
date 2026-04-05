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
# Forzamos gpt-4o-mini por estabilidad y costo, compatible con la nueva librería
MODEL_NAME = "gpt-4o-mini"

TARGET_MIN_ITEMS = 8
TARGET_MAX_ITEMS = 12
MAX_ITEMS_PER_FEED = 10
MAX_PER_MEDIO = 2 # Evita que un solo medio (como Xataka) domine el feed

AI_MAX_REQUESTS = 12
SLEEP_BETWEEN_AI_CALLS = 1
REQUEST_TIMEOUT_SECONDS = 20

WEIGHT_IMPACTO = 0.65
WEIGHT_NOVEDAD = 0.35
# Subimos a 25 para filtrar el ruido y quedarnos con lo mejor
MIN_RELEVANCE_SCORE = 25.0

# Fuentes optimizadas: Mayor peso institucional y diversidad
FEEDS = [
    {"medio": "Harvard Health", "url": "https://www.health.harvard.edu/blog/feed", "idioma": "en"},
    {"medio": "Pew Research", "url": "https://www.pewresearch.org/feed/", "idioma": "en"},
    {"medio": "Scientific American", "url": "https://www.scientificamerican.com/section/reuters/index.xml", "idioma": "en"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "idioma": "en"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml", "idioma": "en"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml", "idioma": "es"},
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/", "idioma": "es"},
    {"medio": "Psychology Today", "url": "https://www.psychologytoday.com/intl/front/feed", "idioma": "en"},
    {"medio": "Mayo Clinic", "url": "https://newsnetwork.mayoclinic.org/category/health-tips/feed/", "idioma": "en"}
]

PROMPT_SISTEMA = """
Eres el socio estratégico de Santiago González (Santula). Tu tarea es analizar noticias basadas en evidencia.
Devuelve una FICHA DE PRODUCCIÓN PARA REELS en ESPAÑOL con este formato exacto:

ÁNGULO EDITORIAL: ...
HOOK: ...
EL DATO: ...
BAJADA SANTULA: ...
REF. CULTURA: ...

Reglas:
- Tono profesional, humano y directo. Sin clichés.
- Si la noticia está en inglés, tradúcela y sintetízala directamente al español.
- Mantener foco en el impacto estratégico para la vida cotidiana.
""".strip()

IMPACTO_KEYWORDS = [
    "salud", "cáncer", "corazón", "diabetes", "alzheimer", "energía", "educación", "empleo",
    "costo", "precio", "vivienda", "seguridad", "clima", "alimentación", "mental", "bienestar",
    "public health", "health", "cost", "jobs", "education", "climate", "food", "longevity"
]

NOVEDAD_KEYWORDS = [
    "estudio", "investigación", "descubr", "hallazgo", "innov", "avance", "ensayo", "tecnología", "ia",
    "inteligencia artificial", "universidad", "científico", "science", "research", "discovery",
    "breakthrough", "innovation", "ai", "machine learning", "trial", "study"
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
    novedad = sum(15 for kw in NOVEDAD_KEYWORDS if kw in merged)
    score = (min(100, impacto) * WEIGHT_IMPACTO) + (min(100, novedad) * WEIGHT_NOVEDAD)
    return max(0.0, min(100.0, round(score, 2)))

def build_fallback_ficha(title, summary, medio):
    return (
        f"ÁNGULO EDITORIAL: Análisis pendiente (IA en pausa).\n"
        f"HOOK: Noticia de {medio}: {title[:70]}...\n"
        f"EL DATO: {summary[:200] if summary else 'Sin resumen disponible.'}\n"
        f"BAJADA SANTULA: Revisar fuente original para extraer ángulo local.\n"
        f"REF. CULTURA: N/A"
    )

def generate_ai_ficha(title, summary, medio, score):
    if not CLIENT: return None
    try:
        response = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": f"Medio: {medio}\nScore: {score}\nTítulo: {title}\nResumen: {summary[:1000]}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"     ❌ Error en llamada API: {e}")
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

    # Selección diversa: max por medio
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

        if not ficha:
            ficha = build_fallback_ficha(item["titulo"], item["summary"], item["medio"])

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
