import os
import feedparser
from google import genai
import json
from datetime import datetime

# Configuración de la nueva librería de Gemini
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

# Mezcla estratégica de fuentes (Español + Inglés)
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

Si la noticia original está en inglés, traduce el análisis y la ficha al ESPAÑOL.

Genera una FICHA DE PRODUCCIÓN PARA REELS con este formato:
ÁNGULO EDITORIAL: (Enfoque humano y cercano, no de cátedra)
HOOK: (Frase rompedora de 3 seg para captar atención)
EL DATO: (Explicación simple y clara del estudio o tendencia)
BAJADA SANTULA: (Por qué esto le importa al ciudadano o el cruce con Paraguay si aplica)
REF. CULTURA: (Cita, libro, película o mito que eleve el tema - solo si es muy relevante)

Estilo: Observador implicado, lenguaje directo, frases cortas, cero cursilería.
"""

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando Curaduría: {datetime.now()} ---")
    
    for feed in FEEDS:
        nombre_medio = feed['medio']
        print(f"Leyendo {nombre_medio}...")
        d = feedparser.parse(feed['url'])
        
        for entry in d.entries[:2]:
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia original: {entry.title}\nResumen: {entry.get('summary', '')}"
                )
                
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": nombre_medio,
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": response.text
                })
            except Exception as e:
                print(f"Error procesando {entry.title}: {e}")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    print("--- Proceso Finalizado con Éxito ---")

if __name__ == "__main__":
    curar_noticias()
