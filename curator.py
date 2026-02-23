import os
import feedparser
from google import genai
import json
import time
from datetime import datetime

# Configuración
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

# Lista equilibrada (Español e Inglés)
FEEDS = [
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml"},
    {"medio": "Xataka", "url": "http://feeds.weblogssl.com/xataka2"},
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"},
    {"medio": "Scientific American", "url": "https://www.scientificamerican.com/section/reuters/index.xml"}
]

PROMPT_SISTEMA = """
Eres el socio estratégico de Santiago González (Santula). Tu tarea es analizar noticias basadas en EVIDENCIA.
Genera una FICHA DE PRODUCCIÓN PARA REELS en ESPAÑOL con este formato:

ÁNGULO EDITORIAL: (Enfoque humano)
HOOK: (Frase rompedora de 3 seg)
EL DATO: (Explicación simple del estudio)
BAJADA SANTULA: (Por qué importa al ciudadano o cruce con Paraguay)
REF. CULTURA: (Cita o referencia que sume)

Usa un tono profesional, cercano y directo.
"""

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando NewsLens: {datetime.now()} ---")
    
    for feed in FEEDS:
        print(f"Leyendo: {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        
        # Procesamos las 2 mejores de cada medio para no saturar la API
        for entry in d.entries[:2]:
            try:
                print(f"  -> Analizando: {entry.title[:50]}...")
                
                # Llamada a Gemini 2.0 Flash
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\nInfo: {entry.get('summary', '')[:300]}"
                )
                
                if response.text:
                    articulos_curados.append({
                        "titulo": entry.title,
                        "link": entry.link,
                        "medio": feed['medio'],
                        "fecha": datetime.now().strftime("%d/%m/%Y"),
                        "ficha": response.text
                    })
                    print("     ✅ Ficha generada.")
                
                # Pausa de seguridad para evitar el error 429
                time.sleep(15) 

            except Exception as e:
                print(f"     ⚠️ Error: {e}")
                # Si hay error de cuota, esperamos más tiempo
                if "429" in str(e):
                    time.sleep(60)

    # Guardar resultados finales
    if articulos_curados:
        print(f"--- Éxito: Guardando {len(articulos_curados)} noticias en data.json ---")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    else:
        print("--- Error: No se pudo generar ninguna noticia hoy. ---")

if __name__ == "__main__":
    curar_noticias()
