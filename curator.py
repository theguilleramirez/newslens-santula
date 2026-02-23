import os
import feedparser
from google import genai
import json
from datetime import datetime

# Configuración de la nueva librería de Gemini
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

FEEDS = [
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml"}
]

PROMPT_SISTEMA = """
Eres el socio estratégico del periodista Santiago González (Santula). 
Tu tarea es analizar noticias basadas en EVIDENCIA y DATOS REALES.
Genera una FICHA DE PRODUCCIÓN PARA REELS con este formato:

ÁNGULO EDITORIAL: (Enfoque humano y cercano)
HOOK: (Frase rompedora de 3 seg)
EL DATO: (Explicación simple del estudio)
BAJADA SANTULA: (Por qué importa al ciudadano o cruce con Paraguay si aplica)
REF. CULTURA: (Cita, libro o película - solo si suma)

Sé directo, evita el tono de IA y usa el estilo de 'observador implicado'.
"""

def curar_noticias():
    articulos_curados = []
    for feed in FEEDS:
        print(f"Leyendo {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        
        # Procesamos las primeras 3 noticias de cada feed
        for entry in d.entries[:3]:
            try:
                # Usamos el nuevo método de la librería actualizada
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\n{entry.get('summary', '')}"
                )
                
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": response.text
                })
            except Exception as e:
                print(f"Error procesando noticia: {e}")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_all_ascii=False)

if __name__ == "__main__":
    curar_noticias()
