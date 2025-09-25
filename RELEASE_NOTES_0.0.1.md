# Release v0.0.1 – Erste lauffähige Version

**Datum:** 2025-09-25

## Highlights
- Erste lauffähige API mit Matchkalender-Listenansicht und Match-Details.
- Saubere Pydantic-Schemas (`MatchOverview`, `MatchDetail`).
- Zeit/Datum-Normalisierung (z. B. `time` = `HH:MM`).
- Trennung von `league` und `competition` + `league_label` als komfortables Anzeige-Feld.
- Obfuscation-Decoder für Zeit/Ergebnis.
- Docker- und Makefile-Setup.

## Endpunkte
- `GET /postal-codes?query=…`
- `GET /matches?from=YYYY-MM-DD&to=YYYY-MM-DD&area=…`
- `GET /match?link=…`

## Breaking Changes
- `GET /health` entfernt.

## Installation
Siehe README (lokal via venv oder Docker/Compose).

Viel Spaß! 🎉
