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
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"}
]

PROMPT_SISTEMA = "Eres socio estratégico de Santula. Analiza esta noticia para un Reel educativo. Responde en español: ÁNGULO EDITORIAL, HOOK, EL DATO y BAJADA ESTRATÉGICA."

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando Curaduría: {datetime.now()} ---")
    
    for feed in FEEDS:
        print(f"Conectando a: {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        
        # Bajamos a 2 noticias por medio para asegurar que la API no nos bloquee
        for entry in d.entries[:2]:
            try:
                print(f"  -> Analizando: {entry.title[:50]}...")
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\nInfo: {entry.get('summary', '')[:200]}"
                )
                
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": response.text if response.text else "Análisis no disponible."
                })

                print("     ⏳ Pausa de seguridad (12s)...")
                time.sleep(12) # Pausa para respetar el límite de 15 RPM

            except Exception as e:
                if "429" in str(e):
                    print("     ⚠️ LÍMITE ALCANZADO. Esperando 60 segundos para enfriar...")
                    time.sleep(60)
                else:
                    print(f"     ❌ Error: {e}")

    if articulos_curados:
        print(f"--- Guardando {len(articulos_curados)} noticias ---")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(articulos_curados, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    curar_noticias()
