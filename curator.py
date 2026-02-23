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
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"medio": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"}
]

PROMPT_SISTEMA = "Analiza esta noticia para un video educativo. Genera: HOOK, EL DATO y BAJADA ESTRATÉGICA."

def curar_noticias():
    articulos_curados = []
    print(f"--- Iniciando Curaduría: {datetime.now()} ---")
    
    for feed in FEEDS:
        print(f"Conectando a: {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        
        for entry in d.entries[:5]:
            try:
                print(f"  -> Procesando: {entry.title[:50]}...")
                
                # Intento de generación con Gemini
                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=f"{PROMPT_SISTEMA}\n\nNoticia: {entry.title}\nInfo: {entry.get('summary', '')[:300]}"
                    )
                    ficha_texto = response.text if response.text else "Ficha no generada."
                except Exception as ai_err:
                    print(f"     ⚠️ Error Gemini: {ai_err}")
                    ficha_texto = "Error al generar análisis con IA."

                articulos_curados.append({
                    "titulo": entry.title,
                    "link": entry.link,
                    "medio": feed['medio'],
                    "fecha": datetime.now().strftime("%d/%m/%Y"),
                    "ficha": ficha_texto
                })
            except Exception as e:
                print(f"     ❌ Error General: {e}")

    # GUARDADO FORZADO: Esto asegura que el archivo no sea [] si hay artículos
    if articulos_curados:
        print(f"--- Guardando {len(articulos_curados)} noticias en data.json ---")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(articulos_curados, f, indent=4, ensure_ascii=False)
    else:
        print("--- ⚠️ No se recolectaron noticias. El archivo quedará vacío. ---")

if __name__ == "__main__":
    curar_noticias()
