# 🌿 Blattwerk

Selbst gehosteter Pflanzen-Tracker. Du fotografierst eine Pflanze, lässt die Art erkennen oder suchst nach ihrem Namen, und Blattwerk holt Beschreibung, Musterbild, Licht- und Wasserbedarf, Winterhärte und Giftigkeit automatisch dazu.

## Funktionen

- **Foto → Art**: Erkennung per Pl@ntNet (optional) oder Suche nach deutschem bzw. botanischem Namen
- **Steckbrief**: Licht, Wasser, Gießintervall, Winterhärte (°C und USDA-Zone), Temperatur- und Feuchtebereiche, Giftigkeit für Menschen und Haustiere, Blütezeit, Wuchsform
- **Musterbild und Beschreibung** aus der deutschen Wikipedia; das Bild wird lokal gespeichert
- **Winterhärte passend zu deinem Ort**: Du stellst deine tiefste Wintertemperatur ein. Pflanzen, die draußen stehen und das nicht aushalten, bekommen von Oktober bis April einen Frost-Hinweis.
- **Gieß-Erinnerung**: Ein Tipp auf „Gegossen“ trägt das Gießen ein, durstige Pflanzen werden markiert
- **Fotoverlauf** pro Pflanze mit wählbarem Titelbild
- Filter nach Drinnen, Balkon, Draußen, durstig, nicht winterhart und giftig für Tiere
- Läuft als Web-App auf dem Handy, die du auf den Home-Bildschirm legen kannst. „Foto“ öffnet dann direkt die Kamera.
- Läuft nur mit der Python-Standardbibliothek; alle Daten liegen in `/data` (SQLite + Bilder)

## Datenquellen

Alle API-Keys sind optional und kostenlos. Du kannst sie entweder als Container-Variable setzen oder direkt in Blattwerk unter **Einstellungen → Datenquellen** eintragen (gespeichert in `/data`, die Container-Variable hat Vorrang). Ohne Keys funktionieren Wikipedia-Suche, Beschreibung und Musterbild, und die übrigen Felder trägst du selbst ein.

| Quelle | Liefert | Key |
|---|---|---|
| Wikipedia + Wikidata | Beschreibung, Musterbild, botanischer Name | – |
| [Pl@ntNet](https://my.plantnet.org/) | Erkennung per Foto (500/Tag) | `PLANTNET_API_KEY` |
| [Perenual](https://perenual.com/docs/api) | Licht, Wasser, Gießintervall, Winterhärtezone, Giftigkeit (100 Abfragen/Tag) | `PERENUAL_API_KEY` |
| [Open Plantbook](https://open.plantbook.io/) | Temperatur, Lux, Luft- und Bodenfeuchte | `OPENPLANTBOOK_CLIENT_ID` + `OPENPLANTBOOK_CLIENT_SECRET` |

API-Antworten werden dauerhaft lokal gespeichert, jede Art kostet also nur eine Abfrage. „Daten neu abrufen“ holt bewusst frische Daten; ist die Quelle dann nicht erreichbar, bleibt die gespeicherte Antwort.

## Installation auf Unraid

**Variante A, fertiges Image (nach dem ersten Push auf GitHub):**
1. Die GitHub Action baut das Image automatisch nach `ghcr.io/shakanuga/blattwerk:latest`. Das Paket unter GitHub → Packages auf *public* stellen.
2. `unraid/blattwerk.xml` als **`my-blattwerk.xml`** nach `/boot/config/plugins/dockerMan/templates-user/` kopieren.
3. In Unraid: Docker → Add Container → Template „blattwerk“ wählen, Keys eintragen, starten.

> **Wichtig:** In `templates-user` darf nur **eine** Datei mit `<Name>blattwerk</Name>` liegen. Unraid nimmt beim Bearbeiten die erste passende Datei. Liegt dort zusätzlich eine unausgefüllte Vorlage, sind die Felder beim nächsten Öffnen leer, obwohl der Container mit den richtigen Werten läuft.

**Variante B, lokal bauen:**
```bash
git clone https://github.com/shakanuga/Blattwerk.git && cd Blattwerk
docker compose up -d --build
```

Danach ist die App unter `http://<server>:8766` erreichbar. Mit einem Reverse Proxy (z. B. Nginx Proxy Manager) davor bekommst du HTTPS.

> Blattwerk hat keine eigene Anmeldung. Gedacht ist es fürs Heimnetz bzw. Tailscale. Für den Zugriff von außen eine Access List im NPM davorsetzen.

## Anmeldung mit Pocket ID

Ohne Einstellungen ist Blattwerk offen für alle, die die Adresse erreichen. Mit Pocket ID fragt Blattwerk vor jedem Zugriff nach einer Anmeldung.

1. In Pocket ID einen OIDC-Client `Blattwerk` anlegen, Callback-URL `https://pflanzen.example.de/auth/pocketid/zurueck`. Unter „Allowed User Groups“ festlegen, wer rein darf.
2. Am Container `OIDC_ISSUER` (z. B. `https://id.example.de`), `OIDC_CLIENT_ID` und `OIDC_CLIENT_SECRET` setzen.
3. Optional: `OIDC_ALLOWED_GROUPS` (zusätzliche Gruppenprüfung in Blattwerk), `OIDC_LABEL` (Text auf dem Knopf), `OIDC_REDIRECT_URI` (falls die Rücksprung-Adresse falsch gebildet wird).

Die Anmeldung gilt 180 Tage. Abmelden über `/auth/abmelden`. Manifest und Icons bleiben ohne Anmeldung erreichbar, damit die App auf dem Homescreen ihr Symbol behält.

## Entwicklung

```bash
DATA_DIR=./data PORT=8080 python app/server.py
```

## Datenschutz

Fotos bleiben auf deinem Server. Nur bei „Pflanze erkennen“ wird das Foto an Pl@ntNet geschickt.
