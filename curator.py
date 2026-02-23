import os
import feedparser
from google import genai
import json
import time
from datetime import datetime

# Configuración de API
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

# Lista ampliada de fuentes para tener variedad
FEEDS = [
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml"},
    {"medio": "Xataka", "url": "http://feeds.weblogssl.com/xataka2"},
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"},
    {"medio": "Scientific American", "url": "https://www.scientificamerican.com/section/reuters/index.xml"},
    {"medio": "Wired Science", "url": "https://www.wired.com/feed/category/science/latest/rss"}
]

PROMPT_SISTEMA = """
Eres el socio estratégico de Santiago González (Santula). Tu tarea es analizar noticias basadas en EVIDENCIA.
Genera una FICHA DE PRODUCCIÓN PARA REELS en ESPAÑOL con este formato:

ÁNGULO EDITORIAL: (Enfoque humano y estratégico)
HOOK: (Frase rompedora de 3 segundos para video)
EL DATO: (Explicación simple del estudio o evidencia)
BAJADA SANTULA: (Por qué importa al ciudadano o posible cruce con Paraguay)
REF. CULTURA: (Cita, película o referencia histórica que sume profundidad)

Usa un tono profesional, humano y directo. Sin frases hechas.
"""

def curar_noticias():
    articulos_curados = []
    timestamp_inicio = datetime.now().strftime('%H:%M:%S')
    print(f"--- Iniciando Barrido NewsLens: {timestamp_inicio} ---")
    
    for feed in FEEDS:
        print(f"Revisando: {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        
        # Tomamos las 2 noticias principales de cada fuente para un total de ~16 opciones
        for entry in d.entries[:2]:
            try:
                print(f"  -> Procesando: {entry.title[:50]}...")
                
                response = client.models.generate_content(
                    model="gemini-1.5-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\nResumen: {entry.get('summary', '')[:300]}"
                )
                
                if response.text:
                    articulos_curados.append({
                        "titulo": entry.title,
                        "link": entry.link,
                        "medio": feed['medio'],
                        "fecha": datetime.now().strftime("%d/%m/%Y"),
                        "ficha": response.text
                    })
                    print("     ✅ Ficha lista.")
                
                # LA ESTRATEGIA DE GOTEO: Pausa de 20 segundos entre peticiones
                # Esto evita el error 429 por velocidad.
                time.sleep(20) 

            except Exception as e:
                print(f"     ⚠️ Error en esta noticia: {e}")
                # Guardamos el error de forma simplificada para no ensuciar el JSON
                if "429" in str(e):
                    print("     (!) Cuota agotada por el momento. Esperando 30s extra...")
                    time.sleep(30)

    # Guardar los resultados finales (siempre sobreescribe para mantenerlo fresco)
    if articulos_curados:
        print(f"--- Éxito: Se generaron {len(articulos_curados)} fichas ---")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    else:
        print("--- No se pudieron generar fichas nuevas en esta pasada ---")

if __name__ == "__main__":
    curar_noticias()
