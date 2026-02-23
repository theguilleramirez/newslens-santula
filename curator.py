import os
import feedparser
from google import genai
import json
from datetime import datetime

# Configuración de la nueva librería de Gemini
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

FEEDS = [
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml"},
    {"medio": "Xataka", "url": "http://feeds.weblogssl.com/xataka2"},
    {"medio": "National Geographic Esp", "url": "https://www.nationalgeographic.com.es/feeds/tags/ciencia.xml"},
    {"medio": "Agencia SINC", "url": "https://www.agenciasinc.es/rss/all"},
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"},
    {"medio": "Nature News", "url": "https://www.nature.com/nature.rss"},
    {"medio": "Nautilus", "url": "https://nautil.us/feed/"},
    {"medio": "The Atlantic Science", "url": "https://www.theatlantic.com/feed/channel/science/"},
    {"medio": "Scientific American", "url": "https://www.scientificamerican.com/section/reuters/index.xml"}
]

PROMPT_SISTEMA = """
Eres el socio estratégico del periodista Santiago González (Santula). 
Tu tarea es analizar noticias basadas en EVIDENCIA y DATOS REALES para crear Reels de edutainment.
Si la noticia está en inglés, traduce el análisis al ESPAÑOL.

Formato de salida:
ÁNGULO EDITORIAL: ...
HOOK: ...
EL DATO: ...
BAJADA SANTULA: ...
REF. CULTURA: ...
"""

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando Curaduría: {datetime.now()} ---")
    
    for feed in FEEDS:
        nombre_medio = feed['medio']
        print(f"Conectando a: {nombre_medio}...")
        d = feedparser.parse(feed['url'])
        
        # Si el feed está vacío, saltar
        if not d.entries:
            print(f"⚠️ {nombre_medio} no devolvió entradas.")
            continue

        for entry in d.entries[:5]: # Leemos 5 noticias por fuente
            try:
                # Limpiar el título y resumen para el prompt
                titulo = entry.title
                resumen = entry.get('summary', '')[:500] # Limitar a 500 caracteres
                
                print(f"  Procesando noticia: {titulo[:50]}...")
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {titulo}\nContenido: {resumen}"
                )
                
                if response.text:
                    articulos_curados.append({
                        "titulo": titulo,
                        "link": entry.link,
                        "medio": nombre_medio,
                        "fecha": datetime.now().strftime("%d/%m/%Y"),
                        "ficha": response.text
                    })
            except Exception as e:
                print(f"  ❌ Error en noticia: {e}")

    # Guardar incluso si la lista es pequeña
    print(f"--- Guardando {len(articulos_curados)} noticias en data.json ---")
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    curar_noticias()
