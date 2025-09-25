# Changelog

All notable changes to this project will be documented in this file.

## [0.0.1] - 2025-09-25
### Added
- Erste lauffähige Version der **fussballde-machtkalender-scraper-api**.
- Endpunkte:
  - `GET /postal-codes` – PLZ/Ort-Autocomplete
  - `GET /matches` – Matchkalender-Übersicht (normalisierte `time`/`date_label`)
  - `GET /match` – Match-Details (Venue, SR/SRA, `competition`, `league_label`)
- Normalisierung von Datum/Uhrzeit und optionale `date_label_long`.
- Trennung von `league` (Spielklasse) und `competition` (Wettbewerb).
- Root `/` leitet zu `/docs`.
- Dockerfile + `docker-compose.yml`.
- Makefile mit Targets (`run`, `lint`, `format`, `test`, `docker-*`, `compose-*`).
- MIT-Lizenz und aktualisierte README.

### Removed
- `GET /health`-Endpoint – nicht mehr vorhanden.

### Notes
- Inoffizielle Nutzung der öffentlichen HTML/JSON-Endpunkte von FUSSBALL.DE.
