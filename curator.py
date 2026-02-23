import os
import feedparser
from google import genai
import json
import time
from datetime import datetime

# Configuración
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

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
Eres el socio estratégico de Santula. Analiza esta noticia basada en EVIDENCIA.
Genera una FICHA DE PRODUCCIÓN PARA REELS en ESPAÑOL:
ÁNGULO EDITORIAL, HOOK, EL DATO, BAJADA SANTULA y REF. CULTURA.
"""

def curar_noticias():
    articulos_curados = []
    print(f"--- Ejecución iniciada: {datetime.now().strftime('%H:%M:%S')} ---")
    
    for feed in FEEDS:
        print(f"Leyendo: {feed['medio']}")
        d = feedparser.parse(feed['url'])
        
        for entry in d.entries[:2]:
            try:
                print(f"  -> Analizando: {entry.title[:40]}...")
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\nInfo: {entry.get('summary', '')[:200]}"
                )
                
                ficha_resultado = response.text if response.text else "Análisis vacío por parte de la IA."
                
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), # Agregamos hora para debug
                    "ficha": ficha_resultado
                })
                print("     ✅ Éxito.")
                time.sleep(12) # Pausa obligatoria para evitar el error 429

            except Exception as e:
                error_msg = str(e)
                print(f"     ⚠️ Error: {error_msg}")
                # Guardamos el error para que aparezca en la web y sepamos qué pasa
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": f"ERROR TÉCNICO: {error_msg}"
                })

    # Guardar siempre, incluso si hay errores, para actualizar la fecha del archivo
    print(f"--- Guardando {len(articulos_curados)} elementos en data.json ---")
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    curar_noticias()
