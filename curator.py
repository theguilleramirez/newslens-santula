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
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml"}
]

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando Prueba: {datetime.now()} ---")
    
    # AGREGAMOS UNA NOTICIA DE PRUEBA MANUAL
    # Esto nos dirá si el problema es de permisos de escritura
    articulos_curados.append({
        "titulo": "Noticia de Prueba del Sistema",
        "link": "https://google.com",
        "medio": "SISTEMA",
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "ficha": "Si ves esto, el robot SI puede escribir en el repositorio. El problema anterior era la API de Gemini."
    })

    for feed in FEEDS:
        print(f"Probando {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        for entry in d.entries[:2]:
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Resumen corto de: {entry.title}"
                )
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": response.text
                })
                time.sleep(12)
            except Exception as e:
                print(f"Error: {e}")

    # Forzamos la escritura
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    print(f"Hecho. Se guardaron {len(articulos_curados)} elementos.")

if __name__ == "__main__":
    curar_noticias()
