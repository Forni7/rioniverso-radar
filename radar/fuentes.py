"""Fuentes que vigila el radar y reglas para clasificar cada noticia."""

# (nombre visible, url del feed, es_oficial)
FEEDS = [
    ("NASA", "https://www.nasa.gov/news-release/feed/", True),
    ("NASA", "https://www.nasa.gov/feed/", True),
    ("NASA Ciencia", "https://science.nasa.gov/feed/", True),
    ("NASA JPL", "https://www.jpl.nasa.gov/feeds/news", True),
    ("ESA", "https://www.esa.int/rssfeed/TopNews", True),
    ("ESA", "https://www.esa.int/rssfeed/Our_Activities/Space_News", True),
    ("ESO", "https://www.eso.org/public/news/feed/", True),
    ("NOIRLab / Rubin", "https://noirlab.edu/public/news/feed/", True),
    ("SpaceNews", "https://spacenews.com/feed/", False),
    ("Spaceflight Now", "https://spaceflightnow.com/feed/", False),
    ("NASASpaceflight", "https://www.nasaspaceflight.com/feed/", False),
    ("Ars Technica", "https://arstechnica.com/space/feed/", False),
    ("European Spaceflight", "https://europeanspaceflight.com/feed/", False),
    ("SpacePolicyOnline", "https://spacepolicyonline.com/feed/", False),
    ("Payload", "https://payloadspace.com/feed/", False),
    ("Space.com", "https://www.space.com/feeds/all", False),
    ("Universe Today", "https://www.universetoday.com/feed/", False),
    ("Phys.org", "https://phys.org/rss-feed/space-news/", False),
    ("Planetary Society", "https://www.planetary.org/rss/articles", False),
    # España: Google Noticias en español con búsquedas concretas
    ("Prensa ES", "https://news.google.com/rss/search?q=%22PLD+Space%22+OR+%22Miura+5%22&hl=es&gl=ES&ceid=ES:es", False),
    ("Prensa ES", "https://news.google.com/rss/search?q=%22Agencia+Espacial+Espa%C3%B1ola%22+OR+%22astronauta+espa%C3%B1ol%22+OR+%22Sara+Garc%C3%ADa%22+astronauta&hl=es&gl=ES&ceid=ES:es", False),
]

# Categorías: (clave, etiqueta, palabras). La primera que encaja gana, así que el orden importa.
CATEGORIAS = [
    ("es", "🇪🇸 España", ["pld space", "miura", "agencia espacial española", "spanish", "spain", "españa", "español",
                         "canarias", "sara garcía", "pablo álvarez", "hisdesat", "sener", "gmv", "teruel", "elche"]),
    ("starship", "🚀 SpaceX", ["starship", "spacex", "super heavy", "raptor", "starbase", "falcon", "starlink", "dragon"]),
    ("luna", "🌙 Luna / Artemis", ["artemis", "lunar", "moon", " luna", "orion", "blue moon", "chang'e", "change-",
                                  "clps", "intuitive machines", "ispace"]),
    ("iss", "🧑‍🚀 Astronautas", ["space station", "iss ", "astronaut", "cosmonaut", "spacewalk", "tiangong", "shenzhou",
                                "crew-", "soyuz", "axiom", "estación espacial", "astronauta"]),
    ("marte", "🔴 Planetas", ["mars", "marte", "perseverance", "curiosity", "jupiter", "saturn", "venus", "mercury",
                             "europa clipper", "juice", "pluto", "titan", "uranus", "neptune", "bepicolombo"]),
    ("ciencia", "🔭 Ciencia", ["webb", "jwst", "hubble", "euclid", "rubin", "roman", "telescope", "galaxy", "galaxies",
                              "exoplanet", "black hole", "comet", "asteroid", "dwarf planet", "supernova", "nebula",
                              "meteor", "aurora", "eclipse", "star ", "stars", "universe", "dark matter", "cometa",
                              "galaxia", "agujero negro", "telescopio"]),
    ("europa", "🇪🇺 Europa", ["esa", "ariane", "vega-c", "isar aerospace", "rocket factory", "exploration company",
                             "space rider", "european", "eumetsat"]),
    ("china", "🇨🇳 China", ["china", "chinese", "cnsa", "long march", "landspace", "zhuque", "galactic energy",
                           "space pioneer"]),
    ("defensa", "🛰️ Defensa", ["military", "space force", "anti-satellite", "missile", "cosmos 2", "kosmos",
                              "spy satellite", "nro", "dod", "pentagon", "golden dome"]),
    ("empresas", "🏢 Cohetes y empresas", ["blue origin", "new glenn", "rocket lab", "neutron", "electron", "ula",
                                          "vulcan", "firefly", "relativity", "virgin galactic", "stoke", "launch"]),
]
CATEGORIA_DEFECTO = ("general", "🌌 Espacio")

# Palabras que hacen subir la importancia (inglés y español)
IMPACTO = ["discover", "descubre", "first ", "primer", "record", "récord", "historic", "histór", "explo",
           "anomaly", "anomalía", "failure", "fails", "falla", "fallo", "scrub", "catch", "atrap", "lands",
           "landing", "aterriz", "dwarf planet", "planeta enano", "water", "agua", "life", "vida", "interstellar",
           "interestelar", "emergency", "emergencia", "leak", "fuga", "delay", "retras", "launch date",
           "fecha", "announce", "anuncia", "confirms", "confirma", "new ", "nuevo", "breakthrough", "crash",
           "estrella", "flight 1", "vuelo 1", "selects", "elige", "budget", "presupuesto"]

# Noticias que no interesan (ofertas, reseñas, horóscopos…)
EXCLUIR = ["deal", "discount", "black friday", "cyber monday", "prime day", "review", "best telescope",
           "best binocular", "best camera", "buying guide", "on sale", "% off", "horoscope", "crossword",
           "quiz", "lego", "gift", "coupon", "podcast", "webinar", "star trek", "star wars", "movie", "tv show",
           "book review", "video game", "videojuego"]

# Estas noticias se guardan pero llegan sin sonido
SILENCIOSAS = ["starlink"]
