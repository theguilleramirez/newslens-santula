import os
import feedparser
from google import genai
import json
import time # Importamos tiempo para las pausas
from datetime import datetime

# Configuración de la nueva librería de Gemini
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

PROMPT_SISTEMA = "Analiza esta noticia para un video educativo de Santiago González. Genera en español: ÁNGULO EDITORIAL, HOOK, EL DATO y BAJADA ESTRATÉGICA."

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando Curaduría: {datetime.now()} ---")
    
    for feed in FEEDS:
        print(f"Conectando a: {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        
        # Procesamos solo las 3 más nuevas de cada medio para cuidar la cuota
        for entry in d.entries[:3]:
            try:
                print(f"  -> Procesando: {entry.title[:50]}...")
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\nInfo: {entry.get('summary', '')[:300]}"
                )
                
                ficha_texto = response.text if response.text else "Ficha no generada."
                
                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": ficha_texto
                })

                # --- PAUSA ESTRATÉGICA ---
                # Esperamos 10 segundos antes de la siguiente noticia para no agotar la cuota gratuita
                print("     ⏳ Esperando 10 segundos para cuidar la cuota...")
                time.sleep(10)

            except Exception as ai_err:
                if "429" in str(ai_err):
                    print(f"     ⚠️ Límite de cuota alcanzado. Saltando a la siguiente fuente...")
                    time.sleep(30) # Si da error 429, esperamos 30 segundos
                else:
                    print(f"     ❌ Error: {ai_err}")

    if articulos_curados:
        print(f"--- Guardando {len(articulos_curados)} noticias en data.json ---")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    else:
        print("--- ⚠️ No se recolectaron noticias. ---")

if __name__ == "__main__":
    curar_noticias()
