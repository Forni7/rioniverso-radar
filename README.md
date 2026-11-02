# 🛰️ Radar Rioniverso

Vigila las noticias del espacio 24/7, las clasifica y las traduce, te avisa al instante por Telegram y lo guarda todo en un panel web. Dos veces al día, Claude verifica las mejores y prepara la ficha de vídeo: gancho, guion, grafismos y fuentes.

| Pieza | Dónde | Cada cuánto | Coste |
|---|---|---|---|
| Radar (20+ fuentes y lanzamientos) | GitHub Actions | cada ~10 min | 0 € |
| Avisos | Bot de Telegram | al instante | 0 € |
| Panel | GitHub Pages (`docs/`) | se actualiza solo | 0 € |
| Fichas de vídeo verificadas | Tarea programada de Claude | 2 veces al día | incluido en tu plan |

## Activarlo (una sola vez)
1. Instala GitHub CLI: descarga el instalador `.pkg` de macOS desde https://cli.github.com y ábrelo.
2. En la Terminal:
   ```bash
   cd ~/Downloads/Rioniverso/radar && python3 configurar.py
   ```
   El asistente te pide iniciar sesión en GitHub y el token de tu bot de Telegram (lo creas con @BotFather). Lo demás lo hace solo.

## Cambiar cosas
- **Fuentes, categorías y palabras clave:** `radar/fuentes.py`.
- **Cómo analiza Claude:** `analisis/INSTRUCCIONES.md`.
- **Lanzarlo a mano:** pestaña *Actions* del repositorio → *Radar Rioniverso* → *Run workflow*.

## Datos (`docs/datos/`)
- `noticias.json`: todas las noticias (45 días).
- `analisis.json`: fichas de Claude.
- `lanzamientos.json`: próximos lanzamientos.
- `estado.json`: memoria interna del radar.
