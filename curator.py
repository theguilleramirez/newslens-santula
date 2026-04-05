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
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")

TARGET_MIN_ITEMS = int(os.environ.get("TARGET_MIN_ITEMS", "8"))
TARGET_MAX_ITEMS = int(os.environ.get("TARGET_MAX_ITEMS", "10"))
MAX_ITEMS_PER_FEED = int(os.environ.get("MAX_ITEMS_PER_FEED", "8"))
MAX_PER_MEDIO = int(os.environ.get("MAX_PER_MEDIO", "2"))

AI_MAX_REQUESTS = int(os.environ.get("AI_MAX_REQUESTS", "8"))
SLEEP_BETWEEN_AI_CALLS = int(os.environ.get("SLEEP_BETWEEN_AI_CALLS", "2"))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "20"))

WEIGHT_IMPACTO = 0.65
WEIGHT_NOVEDAD = 0.35
MIN_RELEVANCE_SCORE = float(os.environ.get("MIN_RELEVANCE_SCORE", "18"))

FEEDS = [
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/", "idioma": "es"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml", "idioma": "es"},
    {"medio": "Xataka", "url": "http://feeds.weblogssl.com/xataka2", "idioma": "es"},
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml", "idioma": "en"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "idioma": "en"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml", "idioma": "en"},
    {"medio": "Wired Science", "url": "https://www.wired.com/feed/category/science/latest/rss", "idioma": "en"},
]

PROMPT_SISTEMA = """
Eres el socio estratégico de Santiago González (Santula).
Analiza noticias basadas en evidencia y genera una FICHA DE PRODUCCIÓN PARA REELS en ESPAÑOL.

Formato exacto de salida:
ÁNGULO EDITORIAL: ...
HOOK: ...
EL DATO: ...
BAJADA SANTULA: ...
REF. CULTURA: ...

Reglas:
- Tono profesional, humano y directo.
- Evitar frases genéricas y repetidas.
- NO repetir exactamente el mismo hook entre notas.
- El ángulo editorial debe ser específico de la noticia, no plantilla.
- Si no hay referencia cultural útil, escribir: "Opcional. No aplica para esta nota."
- Máximo 110 palabras en total.
""".strip()

IMPACTO_KEYWORDS = [
    "salud", "cáncer", "corazón", "diabetes", "alzheimer", "energía", "educación", "empleo", "trabajo",
    "costo", "precio", "hogar", "vivienda", "movilidad", "seguridad", "clima", "aire", "agua",
    "comida", "alimentación", "mental", "bienestar", "consumo", "medicina", "hospital",
    "public health", "health", "cost", "jobs", "education", "climate", "food", "safety",
]

NOVEDAD_KEYWORDS = [
    "estudio", "investigación", "descubr", "hallazgo", "innov", "avance", "ensayo", "tecnología", "ia",
    "inteligencia artificial", "universidad", "científico", "science", "research", "discovery",
    "breakthrough", "innovation", "ai", "machine learning", "trial", "study",
]

LOW_VALUE_KEYWORDS = [
    "opinión", "opinion", "celebrity", "famos", "horoscope", "astrolog", "deportes", "sports",
]

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsLensBot/1.0; +https://github.com/)"
}

CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def normalize_text(value: str) -> str:
    clean = unescape(value or "")
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def keyword_score(text: str, keywords: list[str], max_score: int = 100) -> int:
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)
    return min(max_score, matches * 15)


def low_value_penalty(text: str) -> int:
    text_lower = text.lower()
    matches = sum(1 for kw in LOW_VALUE_KEYWORDS if kw in text_lower)
    return matches * 12


def compute_relevance_score(title: str, summary: str) -> float:
    merged = f"{title} {summary}".strip()
    impacto = keyword_score(merged, IMPACTO_KEYWORDS)
    novedad = keyword_score(merged, NOVEDAD_KEYWORDS)
    score = (impacto * WEIGHT_IMPACTO) + (novedad * WEIGHT_NOVEDAD) - low_value_penalty(merged)
    return max(0.0, min(100.0, round(score, 2)))


def build_fallback_ficha(title: str, summary: str, medio: str, idioma: str) -> str:
    short_summary = summary[:320] if summary else "Nota breve sin resumen expandido en el feed."

    hook_variants = [
        f"Si esto escala, puede cambiar decisiones cotidianas: {title[:80]}.",
        f"Una señal silenciosa con impacto real: {title[:80]}.",
        f"No es una moda: este dato puede afectar tu día a día: {title[:80]}.",
    ]
    hook = hook_variants[hash(title) % len(hook_variants)]

    idioma_label = "inglés" if idioma == "en" else "español"

    return (
        f"ÁNGULO EDITORIAL: {medio} publica una señal concreta con impacto social potencial, traducible al ciudadano común.\n"
        f"HOOK: {hook}\n"
        f"EL DATO: {short_summary}\n"
        f"BAJADA SANTULA: Explicarlo en lenguaje simple, conectándolo con hábitos, costos o decisiones reales del público. (Fuente original en {idioma_label}).\n"
        "REF. CULTURA: Opcional. No aplica para esta nota."
    )


def parse_feed_with_requests(url: str):
    try:
        response = requests.get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return feedparser.parse(response.content)
    except Exception as exc:
        print(f"     ⚠️ Feed no disponible ({url}): {exc}")
        return None


def get_candidates() -> list[dict]:
    candidates = []
    seen_links = set()

    for feed in FEEDS:
        print(f"Revisando: {feed['medio']}...")
        parsed = parse_feed_with_requests(feed["url"])
        if not parsed or not getattr(parsed, "entries", None):
            continue

        for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
            link = entry.get("link", "").strip()
            if not link or link in seen_links:
                continue

            title = normalize_text(entry.get("title", ""))
            summary = normalize_text(entry.get("summary", entry.get("description", "")))

            if not title:
                continue

            score = compute_relevance_score(title, summary)
            if score < MIN_RELEVANCE_SCORE:
                continue

            candidates.append(
                {
                    "titulo": title,
                    "link": link,
                    "medio": feed["medio"],
                    "idioma": feed.get("idioma", "es"),
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "summary": summary,
                    "score": score,
                }
            )
            seen_links.add(link)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def select_diverse_candidates(candidates: list[dict]) -> list[dict]:
    """
    Selecciona noticias con diversidad de medios.
    - Máximo MAX_PER_MEDIO por medio.
    - Entre TARGET_MIN_ITEMS y TARGET_MAX_ITEMS si hay suficiente volumen.
    """
    buckets = defaultdict(list)
    for item in candidates:
        buckets[item["medio"]].append(item)

    # Ordenar cada bucket por score descendente
    for medio in buckets:
        buckets[medio].sort(key=lambda x: x["score"], reverse=True)

    medios = sorted(buckets.keys())
    selected = []
    selected_by_medio = defaultdict(int)

    while len(selected) < TARGET_MAX_ITEMS:
        added_in_round = False
        for medio in medios:
            if selected_by_medio[medio] >= MAX_PER_MEDIO:
                continue
            if not buckets[medio]:
                continue

            candidate = buckets[medio].pop(0)
            selected.append(candidate)
            selected_by_medio[medio] += 1
            added_in_round = True

            if len(selected) >= TARGET_MAX_ITEMS:
                break

        if not added_in_round:
            break

    # Si por diversidad quedamos cortos, completar con los mejores restantes
    if len(selected) < TARGET_MIN_ITEMS:
        remaining = []
        for medio in medios:
            remaining.extend(buckets[medio])
        remaining.sort(key=lambda x: x["score"], reverse=True)

        for item in remaining:
            if len(selected) >= TARGET_MIN_ITEMS:
                break
            selected.append(item)

    return selected


def generate_ai_ficha(title: str, summary: str, medio: str, score: float):
    if not CLIENT:
        return None

    user_prompt = (
        f"Medio: {medio}\n"
        f"Relevancia estimada: {score}\n"
        f"Título: {title}\n"
        f"Resumen: {summary[:1200]}\n"
    )

    # Versión compatible y estable para tu caso:
    response = CLIENT.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": user_prompt},
        ],
    )

    if response and response.choices and response.choices[0].message:
        content = response.choices[0].message.content
        if content:
            return content.strip()

    return None


def curar_noticias():
    timestamp_inicio = datetime.now().strftime("%H:%M:%S")
    print(f"--- Iniciando Barrido NewsLens: {timestamp_inicio} ---")

    candidates = get_candidates()
    if not candidates:
        print("--- No se encontraron candidatos en los feeds. Se conserva el data.json existente. ---")
        return

    selected = select_diverse_candidates(candidates)

    articulos_curados = []
    ai_requests_used = 0

    for item in selected:
        ficha = None
        provider = "fallback"

        if ai_requests_used < AI_MAX_REQUESTS:
            try:
                print(f"  -> IA(OpenAI): {item['titulo'][:70]}...")
                ficha = generate_ai_ficha(item["titulo"], item["summary"], item["medio"], item["score"])
                if ficha:
                    provider = "openai"
                    ai_requests_used += 1
                time.sleep(SLEEP_BETWEEN_AI_CALLS)
            except Exception as exc:
                print(f"     ⚠️ Error IA OpenAI: {exc}")

        if not ficha:
            ficha = build_fallback_ficha(item["titulo"], item["summary"], item["medio"], item["idioma"])

        articulos_curados.append(
            {
                "titulo": item["titulo"],
                "link": item["link"],
                "medio": item["medio"],
                "idioma": item["idioma"],
                "fecha": item["fecha"],
                "score": item["score"],
                "provider": provider,
                "ficha": ficha,
            }
        )

    with open("data.json", "w", encoding="utf-8") as file_obj:
        json.dump(articulos_curados, file_obj, indent=4, ensure_ascii=False)

    print(f"--- Éxito: {len(articulos_curados)} fichas generadas ({ai_requests_used} con OpenAI) ---")


if __name__ == "__main__":
    curar_noticias()
