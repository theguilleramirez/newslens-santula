import os
import feedparser
import google.generativeai as genai
import json
from datetime import datetime

# Configuración de Gemini
GENAI_API_KEY = "AIzaSyAJegSxeKOl2USgs7x6KwGECrVG4MOkB_Y"
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Fuentes enfocadas en Datos, Ciencia y Tendencias Sociales
FEEDS = [
    {"medio": "Science Daily", "url": "https://www.sciencedaily.com/rss/all.xml"},
    {"medio": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
    {"medio": "Infobae Salud", "url": "https://www.infobae.com/arc/outboundfeeds/rss/category/salud/"},
    {"medio": "El País Ciencia", "url": "https://elpais.com/rss/ciencia/ciencia.xml"},
    {"medio": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"}
]

PROMPT_SISTEMA = """
Eres un consultor estratégico de contenido para el periodista Santiago González (Santula). 
Tu objetivo es filtrar noticias basadas en DATOS REALES, ESTUDIOS, O TENDENCIAS COMPROBABLES.
Ignora política partidaria o chismes. 

Para cada noticia, califica de 1 a 10 su 'Conversabilidad': qué tan fácil es que Santi 
la use para un Reel de TikTok/Instagram bajo el formato 'Traducción de Evidencia'.
"""

def curar_noticias():
    articulos_curados = []
    
    for feed in FEEDS:
        print(f"Leyendo {feed['medio']}...")
        d = feedparser.parse(feed['url'])
        for entry in d.entries[:5]: # Leemos las últimas 5 de cada fuente
            texto_analizar = f"Título: {entry.title}. Resumen: {entry.get('summary', '')}"
            
            # Pedimos a Gemini que evalúe
            response = model.generate_content(f"{PROMPT_SISTEMA}\n\nAnaliza esto: {texto_analizar}")
            
            # Aquí simulamos un scoring simple para el MVP
            # En la versión final, pediremos a Gemini un JSON estructurado
            articulos_curados.append({
                "titulo": entry.title,
                "link": entry.link,
                "medio": feed['medio'],
                "fecha": datetime.now().strftime("%d/%m/%Y")
            })
            
    # Guardamos los resultados
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(articulos_curados, f, indent=4, ensure_all_ascii=False)

if __name__ == "__main__":
    curar_noticias()
