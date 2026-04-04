# newslens-santula

Herramienta para curar noticias de alto interés general y convertirlas en fichas de producción para reels.

## Qué hace hoy

1. Lee RSS de medios y portales de ciencia/tecnología.
2. Calcula un score de relevancia por noticia (65% impacto cotidiano, 35% novedad científica).
3. Selecciona automáticamente entre 8 y 10 opciones por corrida diaria.
4. Genera fichas con OpenAI para la mayor parte de las noticias.
5. Completa con fallback cuando la IA no responde (el flujo no se rompe).
6. Guarda todo en `data.json`, que consume `index.html`.

## Requisitos

- Python 3.10+
- Dependencias de `requirements.txt`
- Una key válida de OpenAI con crédito

Instalación local:

```bash
pip install -r requirements.txt
