# fussballde-machtkalender-scraper-api

FastAPI-basierte API zum Sammeln & Durchsuchen von Spielen auf **FUSSBALL.DE** anhand von PLZ/Ort.  
Enthält robuste Parser inkl. Obfuscation-Decoder (CSS/WOFF) sowie Normalisierung von Datum/Uhrzeit.

> **Hinweis/Disclaimer**  
> Dies ist **inoffiziell** und steht in **keiner Verbindung** zu FUSSBALL.DE/DFB.  
> Es gibt keine stabile Public-API; diese Implementierung nutzt öffentliche HTML-/JSON-Endpunkte.  
> Bitte die Nutzungsbedingungen (ToS), robots.txt und faire Abrufraten respektieren.

---

## Repository

- **Name:** `fussballde-machtkalender-scraper-api`  
- **URL:** <https://github.com/ClemensRau1337/fussballde-machtkalender-scraper-api>

---

## Features

- 📅 **Matchkalender** nach PLZ/Zeitraum (Listenansicht)
- 📄 **Match-Details** inkl. Venue, Schiedsrichter*innen, Assistenzen (soweit vorhanden)
- 🧠 **Obfuscation-Decoder** (Zeit/Ergebnis)
- ⏱️ **Normalisierung**:  
  - `time` immer `HH:MM`  
  - `date_label` standardisiert `DD.MM.YYYY` (lange Form optional als `date_label_long`)  
- 🏷️ **Ligafelder getrennt**:  
  - `league` (Spielklasse, z. B. „Verbandsliga“)  
  - `competition` (Wettbewerb, z. B. „B-Mädchen-Oberliga (MBOL)“)  
  - optionales Anzeige-Feld `league_label = competition or league`
- 🧩 Saubere **Pydantic-Schemas**: `MatchOverview` (Liste) & `MatchDetail` (Detail)
- 💾 **Caching** (Datei-Cache) konfigurierbar
- 🔁 Root **/** leitet zur Swagger-Doku **/docs**

---

## Quickstart (lokal)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger/OpenAPI: <http://localhost:8000/docs>  
ReDoc: <http://localhost:8000/redoc>

### Docker

```bash
docker build -t fussballde-machtkalender-scraper-api:latest .
docker run --rm -p 8000:8000 --env-file .env \
  -v "$PWD/.cache_fussballde:/app/.cache_fussballde" \
  fussballde-machtkalender-scraper-api:latest
```

---

## Konfiguration

Umgebungsvariablen (siehe `app/config.py` bzw. `.env.example`):

| Variable              | Default              | Beschreibung                          |
|-----------------------|----------------------|---------------------------------------|
| `REQUEST_TIMEOUT`     | `15`                 | HTTP-Timeout in Sekunden              |
| `SLEEP_SEC`           | `0.5`                | Pause zwischen Paginierungs-Requests  |
| `USE_CACHE_DEFAULT`   | `true`               | Cache standardmäßig aktiv             |
| `CACHE_DIR`           | `.cache_fussballde`  | Cache-Verzeichnis                     |
| `USER_AGENT`          | (projektintern)      | eigener UA-String für Requests        |

Lege bei Bedarf eine `.env` an (oder nutze `.env.example` als Vorlage).

---

## Endpoints

### PLZ-Autocomplete
`GET /postal-codes?query=Hamburg`  
Antwort: `PostalCode[]`  
```json
{"postalCode":"22041","city":"Hamburg","district":"Wandsbek"}
```

### Matchkalender (Liste)
`GET /matches?from=YYYY-MM-DD&to=YYYY-MM-DD&area=Hamburg`  
Antwort: `MatchOverview[]`

**Schema `MatchOverview`:**
```json
{
  "date_label": "25.09.2025",
  "time": "18:30",
  "age_group": "B-Juniorinnen",
  "league": "Verbandsliga",
  "home": "Condor 1.B-Mäd.",
  "away": "Walddörfer 1.B-Mäd.",
  "score": null,
  "game_id": "02U3863ODC000000VS5489BUVS8CK5KT",
  "link": "https://www.fussball.de/spiel/condor-1b-maed-walddoerfer-1b-maed/-/spiel/02U3863ODC000000VS5489BUVS8CK5KT"
}
```

### Match-Details
`GET /match?link=<RELATIVE-ODER-ABSOLUTER-LINK>`  
Antwort: `MatchDetail`

**Zusätzliche Felder in `MatchDetail`:**
```json
{
  "competition": "B-Mädchen-Oberliga (MBOL)",
  "league_label": "B-Mädchen-Oberliga (MBOL)",
  "staffel_id": "02THF0HR4G000005VS5489BUVS7GO5S8-G",
  "spielnummer": "032201010",
  "staffelnummer": "032201",
  "venue": "Kunstrasenplatz ...",
  "referee": "Kai Planz",
  "assistant_1": "Vorname Nachname",
  "assistant_2": "Vorname Nachname"
}
```

### Bekannte Limitierungen
- HTML/Struktur auf FUSSBALL.DE kann sich ändern  
- Nicht jede Seite liefert vollständige Daten (z. B. SR/SRA)  
- Live/obfuskiertes Ergebnis kann in der Listenansicht fehlen → Detailseite dekodiert zuverlässiger


## Sicherheit & Fair Use

- Kein exzessives Crawling: kleine Paginierung + Pausen  
- Cache nutzen, keine personenbezogenen Daten speichern  
- Pull Requests willkommen 🙌

---

### Lokale Entwicklung mit `make`

Ohne manuelles Aktivieren der venv – alle Tools laufen über `venv/bin/*`.

```bash
# Einmalig erstellen + deps installieren
make venv
make install

# Starten (uvicorn --reload)
make run

# Linting / Format / Tests
make lint
make format
make test

# Aufräumen
make clean
```


## Lizenz

Siehe [`LICENSE`](LICENSE) (MIT).
