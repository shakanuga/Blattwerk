"""Blattwerk – selbst gehosteter Pflanzen-Tracker.

Nur Python-Standardbibliothek: kein pip install nötig.
Datenquellen:
  * Wikipedia (de) + Wikidata  – Beschreibung, Musterbild, botanischer Name (ohne Key)
  * Perenual                    – Pflege, Licht, Wasser, Winterhärtezone, Giftigkeit (kostenloser Key)
  * Open Plantbook              – Temperatur-, Licht- und Feuchtebereiche (kostenloser Key)
  * Pl@ntNet                    – Erkennung per Foto (kostenloser Key)
"""

import base64
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pocketid

VERSION = "1.0.0"
PORT = int(os.environ.get("PORT", "8080"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
STATIC_DIR = Path(__file__).parent / "static"
KEY_NAMES = ("PLANTNET_API_KEY", "PERENUAL_API_KEY", "OPENPLANTBOOK_CLIENT_ID", "OPENPLANTBOOK_CLIENT_SECRET")


def key(name):
    """API-Key: Umgebungsvariable hat Vorrang, sonst der in der App gespeicherte Wert."""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        with db() as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", ("key_" + name,)).fetchone()
        return (json.loads(row["value"]) or "").strip() if row else ""
    except Exception:
        return ""


def key_source(name):
    if os.environ.get(name, "").strip():
        return "env"
    return "app" if key(name) else None
WIKI_LANG = os.environ.get("WIKI_LANG", "de").strip() or "de"
USER_AGENT = f"Blattwerk/{VERSION} (self-hosted plant tracker; github.com/shakanuga/Blattwerk)"
MAX_BODY = 25 * 1024 * 1024

PHOTO_DIR = DATA_DIR / "photos"
REF_DIR = DATA_DIR / "ref"
DB_PATH = DATA_DIR / "blattwerk.db"

OIDC = pocketid.PocketID()
SESSION_COOKIE = "blattwerk_session"
SESSION_MAX_AGE = 180 * 86400
OPEN_PATHS = ("/manifest.webmanifest", "/icon-180.png", "/icon-192.png", "/icon-512.png", "/icon.svg")
_oidc_key = None


def oidc_key():
    global _oidc_key
    if _oidc_key is None:
        _oidc_key = pocketid.secret_key(DATA_DIR)
    return _oidc_key


DEFAULT_SETTINGS = {"local_min_temp": -15, "region_label": "Mein Garten"}

# --------------------------------------------------------------------------- DB

_db_lock = threading.Lock()


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    for d in (DATA_DIR, PHOTO_DIR, REF_DIR):
        d.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                species_common TEXT,
                species_sci TEXT,
                location TEXT DEFAULT 'drinnen',
                spot TEXT,
                acquired TEXT,
                notes TEXT,
                hardy TEXT DEFAULT 'unbekannt',
                min_temp REAL,
                water_interval INTEGER,
                cover_photo_id INTEGER,
                ref_image TEXT,
                info TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
                file TEXT NOT NULL,
                thumb TEXT,
                caption TEXT,
                taken_at TEXT
            );
            CREATE TABLE IF NOT EXISTS waterings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
                at TEXT NOT NULL,
                kind TEXT DEFAULT 'gegossen'
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                at REAL
            );
            """
        )


def get_settings():
    s = dict(DEFAULT_SETTINGS)
    with db() as c:
        for row in c.execute("SELECT key, value FROM settings WHERE key NOT LIKE 'key\\_%' ESCAPE '\\'"):
            try:
                s[row["key"]] = json.loads(row["value"])
            except Exception:
                s[row["key"]] = row["value"]
    return s


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------ HTTP helper


class UpstreamError(Exception):
    pass


def http_json(url, data=None, headers=None, method=None, timeout=20):
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise UpstreamError(f"{e.code} von {urllib.parse.urlsplit(url).netloc}: {body}")
    except urllib.error.URLError as e:
        raise UpstreamError(f"{urllib.parse.urlsplit(url).netloc} nicht erreichbar: {e.reason}")


_tl = threading.local()


def cached(key, ttl, fn):
    """SQLite-Cache für API-Antworten, schont die Tageslimits.

    ttl=None: dauerhaft gespeichert. „Daten neu abrufen“ setzt _tl.force und
    lädt frisch; schlägt das fehl, wird die gespeicherte Antwort genutzt.
    """
    force = getattr(_tl, "force", False)
    with db() as c:
        row = c.execute("SELECT value, at FROM cache WHERE key=?", (key,)).fetchone()
    if row and not force and (ttl is None or time.time() - row["at"] < ttl):
        return json.loads(row["value"])
    try:
        val = fn()
    except UpstreamError:
        if row:
            return json.loads(row["value"])
        raise
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO cache(key, value, at) VALUES (?,?,?)",
            (key, json.dumps(val), time.time()),
        )
    return val


DAY = 86400

# -------------------------------------------------------------- Wikipedia/Wikidata


def wiki_api(params):
    params = {"format": "json", "formatversion": "2", **params}
    url = f"https://{WIKI_LANG}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    return http_json(url)


def _wiki_pages_to_results(data):
    pages = (data.get("query") or {}).get("pages") or []
    pages = sorted(pages, key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        if p.get("missing"):
            continue
        out.append(
            {
                "title": p.get("title"),
                "extract": (p.get("extract") or "").strip(),
                "thumb": (p.get("thumbnail") or {}).get("source"),
                "wikidata": (p.get("pageprops") or {}).get("wikibase_item"),
            }
        )
    return out


def wiki_search(q, limit=8):
    def run(search):
        return _wiki_pages_to_results(
            wiki_api(
                {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": search,
                    "gsrlimit": str(limit),
                    "gsrnamespace": "0",
                    "prop": "pageimages|extracts|pageprops",
                    "piprop": "thumbnail",
                    "pithumbsize": "300",
                    "exintro": "1",
                    "explaintext": "1",
                    "exsentences": "2",
                    "exlimit": "max",
                    "ppprop": "wikibase_item",
                }
            )
        )

    def go():
        # Erst nur Artikel mit Taxobox (= Pflanzen/Lebewesen), sonst ungefiltert.
        res = run(f"hastemplate:Taxobox {q}")
        if not res:
            res = run(q)
        return res

    return cached(f"wsearch:{WIKI_LANG}:{q.lower()}", 7 * DAY, go)


def wiki_page(title):
    def go():
        data = wiki_api(
            {
                "action": "query",
                "titles": title,
                "redirects": "1",
                "prop": "pageimages|extracts|pageprops|info",
                "piprop": "thumbnail",
                "pithumbsize": "1200",
                "exintro": "1",
                "explaintext": "1",
                "ppprop": "wikibase_item",
                "inprop": "url",
            }
        )
        pages = (data.get("query") or {}).get("pages") or []
        if not pages or pages[0].get("missing"):
            return None
        p = pages[0]
        return {
            "title": p.get("title"),
            "extract": (p.get("extract") or "").strip(),
            "image": (p.get("thumbnail") or {}).get("source"),
            "url": p.get("fullurl")
            or f"https://{WIKI_LANG}.wikipedia.org/wiki/" + urllib.parse.quote(p.get("title", "")),
            "wikidata": (p.get("pageprops") or {}).get("wikibase_item"),
        }

    return cached(f"wpage:{WIKI_LANG}:{title}", None, go)


def wikidata_taxon(qid):
    if not qid:
        return {}

    def go():
        data = http_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
        ent = (data.get("entities") or {}).get(qid) or next(iter((data.get("entities") or {}).values()), {})
        claims = ent.get("claims") or {}

        def first(prop):
            try:
                return claims[prop][0]["mainsnak"]["datavalue"]["value"]
            except Exception:
                return None

        labels = ent.get("labels") or {}
        return {
            "taxon": first("P225"),
            "label_de": (labels.get("de") or {}).get("value"),
            "label_en": (labels.get("en") or {}).get("value"),
        }

    try:
        return cached(f"wd:{qid}", None, go)
    except UpstreamError:
        return {}


# -------------------------------------------------------------------- Perenual

PERENUAL_BASE = "https://perenual.com/api/v2"


def _clean(v):
    """Perenual liefert im Gratis-Tarif teils 'Upgrade Plans…'-Platzhalter."""
    if isinstance(v, str) and ("Upgrade Plan" in v or "subscription-api-pricing" in v):
        return None
    return v


def perenual_care_guide(det):
    """Kurze Pflegeanleitung (Gießen, Licht, Rückschnitt) – englisch, optional."""
    k = key("PERENUAL_API_KEY")
    urls = []
    link = det.get("care_guides") or det.get("care-guides")
    if isinstance(link, str) and link.startswith("http"):
        urls.append(link if "key=" in link else link + ("&" if "?" in link else "?") + "key=" + k)
    q = urllib.parse.urlencode({"key": k, "species_id": det.get("id")})
    urls += [f"{PERENUAL_BASE}/species-care-guide-list?{q}", f"https://perenual.com/api/species-care-guide-list?{q}"]
    for u in urls:
        try:
            data = http_json(u)
        except UpstreamError:
            continue
        out = {}
        for item in data.get("data") or []:
            for sec in item.get("section") or []:
                t, txt = (sec.get("type") or "").lower(), _clean(sec.get("description"))
                if t and isinstance(txt, str) and txt.strip():
                    out[t] = txt.strip()
        if out:
            return out
    return {}


def perenual_find(sci_name):
    if not key("PERENUAL_API_KEY") or not sci_name:
        return None

    def go():
        url = f"{PERENUAL_BASE}/species-list?" + urllib.parse.urlencode({"key": key("PERENUAL_API_KEY"), "q": sci_name})
        data = http_json(url).get("data") or []
        target = sci_name.lower().strip()
        target2 = " ".join(target.split()[:2])
        best = None
        for item in data:
            sci = [s.lower() for s in (item.get("scientific_name") or []) if isinstance(s, str)]
            if any(s == target for s in sci):
                best = item
                break
            if best is None and any(s.startswith(target2) for s in sci):
                best = item
        if best is None and data:
            best = data[0]
        if not best:
            return None
        det = http_json(f"{PERENUAL_BASE}/species/details/{best['id']}?key={key('PERENUAL_API_KEY')}")
        det["_care_guide"] = perenual_care_guide(det)
        return det

    return cached(f"perenual:{sci_name.lower()}", None, go)


SUN_MAP = {
    "full sun": "Sonne",
    "sun": "Sonne",
    "part sun/part shade": "Halbschatten",
    "part shade": "Halbschatten",
    "part sun": "Halbschatten",
    "sun-part shade": "Sonne bis Halbschatten",
    "filtered shade": "Lichter Schatten",
    "deep shade": "Schatten",
    "full shade": "Schatten",
    "shade": "Schatten",
    "bright indirect light": "Hell, keine direkte Sonne",
    "indirect light": "Hell, keine direkte Sonne",
    "low light": "Wenig Licht",
}
WATER_MAP = {"frequent": "viel", "average": "mittel", "minimum": "wenig", "none": "sehr wenig"}
CYCLE_MAP = {
    "perennial": "Mehrjährig",
    "annual": "Einjährig",
    "biennial": "Zweijährig",
    "biannual": "Zweijährig",
    "herbaceous perennial": "Staude",
}
LEVEL_MAP = {"low": "gering", "medium": "mittel", "moderate": "mittel", "high": "hoch"}
SEASON_MAP = {"spring": "Frühling", "summer": "Sommer", "fall": "Herbst", "autumn": "Herbst", "winter": "Winter"}
TYPE_MAP = {
    "tree": "Baum",
    "shrub": "Strauch",
    "herb": "Kraut",
    "flower": "Blume",
    "vine": "Kletterpflanze",
    "climber": "Kletterpflanze",
    "grass": "Gras",
    "fern": "Farn",
    "succulent": "Sukkulente",
    "cactus": "Kaktus",
    "palm": "Palme",
    "conifer": "Nadelgehölz",
    "vegetable": "Gemüse",
    "fruit": "Obst",
    "bulb": "Zwiebelpflanze",
    "groundcover": "Bodendecker",
}


ORIGIN_MAP = {
    "south america": "Südamerika", "central america": "Mittelamerika", "north america": "Nordamerika",
    "mexico": "Mexiko", "caribbean": "Karibik", "west indies": "Karibik", "brazil": "Brasilien",
    "africa": "Afrika", "south africa": "Südafrika", "tropical africa": "Tropisches Afrika", "madagascar": "Madagaskar",
    "asia": "Asien", "east asia": "Ostasien", "southeast asia": "Südostasien", "china": "China", "japan": "Japan",
    "india": "Indien", "himalaya": "Himalaya", "europe": "Europa", "mediterranean": "Mittelmeerraum",
    "southern europe": "Südeuropa", "australia": "Australien", "new zealand": "Neuseeland", "pacific islands": "Pazifikinseln",
    "middle east": "Naher Osten", "turkey": "Türkei", "caucasus": "Kaukasus", "korea": "Korea", "taiwan": "Taiwan",
    "united states": "USA", "canada": "Kanada", "peru": "Peru", "colombia": "Kolumbien", "argentina": "Argentinien",
    "chile": "Chile", "ecuador": "Ecuador", "venezuela": "Venezuela", "bolivia": "Bolivien", "guatemala": "Guatemala",
    "costa rica": "Costa Rica", "panama": "Panama", "philippines": "Philippinen", "indonesia": "Indonesien",
    "malaysia": "Malaysia", "thailand": "Thailand", "vietnam": "Vietnam", "sri lanka": "Sri Lanka",
    "canary islands": "Kanaren", "north africa": "Nordafrika", "western asia": "Westasien", "central asia": "Zentralasien",
}
SOIL_MAP = {
    "well-drained": "durchlässig", "well drained": "durchlässig", "loam": "lehmig", "loamy": "lehmig", "sandy": "sandig",
    "sand": "sandig", "clay": "tonig", "chalky": "kalkhaltig", "acidic": "sauer", "alkaline": "alkalisch",
    "neutral": "neutral", "moist": "feucht", "rich": "nährstoffreich", "humus rich": "humusreich", "peat": "torfig",
}
MONTH_MAP = {m.lower(): d for m, d in zip(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"])}
PROP_MAP = {
    "seed propagation": "Samen", "seed": "Samen", "cutting": "Stecklinge", "cuttings": "Stecklinge",
    "stem cutting": "Stecklinge", "leaf cutting": "Blattstecklinge", "division": "Teilung", "layering": "Absenker",
    "air layering propagation": "Abmoosen", "air layering": "Abmoosen", "grafting propagation": "Veredelung",
    "grafting": "Veredelung", "offsets": "Kindel", "bulb": "Zwiebeln", "tuber": "Knollen", "spores": "Sporen",
}
ATTRACT_MAP = {
    "butterflies": "Schmetterlinge", "bees": "Bienen", "hummingbirds": "Kolibris", "birds": "Vögel",
    "pollinators": "Bestäuber", "insects": "Insekten", "moths": "Nachtfalter",
}


def zone_min_c(zone):
    """USDA-Winterhärtezone -> Untergrenze in °C (Zone 1 = -51,1 °C, je Zone +5,6 °C)."""
    try:
        z = float(re.match(r"\d+(\.\d+)?", str(zone)).group(0))
    except Exception:
        return None
    f = -60 + (z - 1) * 10
    return round((f - 32) * 5 / 9, 1)


def _tr(val, mapping):
    if not isinstance(val, str):
        return None
    k = val.strip().lower()
    return mapping.get(k, val.strip().capitalize())


def map_perenual(d):
    if not d:
        return {}
    out = {"perenual_id": d.get("id")}
    sun = [s for s in (d.get("sunlight") or []) if isinstance(s, str) and _clean(s)]
    if sun:
        de = []
        for s in sun:
            t = _tr(s, SUN_MAP)
            if t and t not in de:
                de.append(t)
        out["light"] = ", ".join(de)
    w = _clean(d.get("watering"))
    if w:
        out["water"] = _tr(w, WATER_MAP)
    bench = d.get("watering_general_benchmark") or {}
    if isinstance(bench, dict) and _clean(bench.get("value")):
        nums = re.findall(r"\d+", str(bench.get("value")))
        if nums:
            n = int(nums[0])
            if "week" in str(bench.get("unit", "")).lower():
                n *= 7
            out["water_interval"] = n
    hz = d.get("hardiness") or {}
    if isinstance(hz, dict) and _clean(hz.get("min")):
        out["hardiness_zone"] = f"{hz.get('min')}–{hz.get('max')}" if hz.get("max") else str(hz.get("min"))
        mt = zone_min_c(hz.get("min"))
        if mt is not None:
            out["min_temp"] = mt
    for src, dst in (("poisonous_to_humans", "toxic_humans"), ("poisonous_to_pets", "toxic_pets")):
        v = _clean(d.get(src))
        if v is not None and v != "":
            out[dst] = bool(v) if not isinstance(v, str) else v.lower() in ("1", "true", "yes")
    if d.get("indoor") is not None and _clean(d.get("indoor")) is not None:
        out["indoor_ok"] = bool(d.get("indoor"))
    for src, dst, mp in (
        ("cycle", "cycle", CYCLE_MAP),
        ("care_level", "care_level", LEVEL_MAP),
        ("growth_rate", "growth_rate", LEVEL_MAP),
        ("type", "plant_type", TYPE_MAP),
    ):
        v = _clean(d.get(src))
        if isinstance(v, str) and v:
            out[dst] = _tr(v, mp)
    fl = _clean(d.get("flowering_season"))
    if isinstance(fl, str) and fl:
        out["flowering"] = _tr(fl, SEASON_MAP)
    if d.get("drought_tolerant"):
        out["drought_tolerant"] = True
    fam = _clean(d.get("family"))
    if isinstance(fam, str) and fam:
        out["family"] = fam
    desc = _clean(d.get("description"))
    if isinstance(desc, str) and desc:
        out["description_en"] = desc
    img = d.get("default_image") or {}
    if isinstance(img, dict):
        u = _clean(img.get("regular_url") or img.get("original_url") or img.get("medium_url"))
        if u and u.startswith("http"):
            out["perenual_image"] = u
    if isinstance(bench, dict) and _clean(bench.get("value")):
        rng = re.findall(r"\d+", str(bench.get("value")))
        if rng:
            out["water_range"] = "–".join(rng[:2])
            if "week" in str(bench.get("unit", "")).lower():
                out["water_range"] += " Wochen"
    origin = _list(d.get("origin"))
    if origin:
        out["origin"] = ", ".join(dict.fromkeys(_tr(o, ORIGIN_MAP) for o in origin))
    soil = _list(d.get("soil"))
    if soil:
        out["soil"] = ", ".join(dict.fromkeys(_tr(x, SOIL_MAP) for x in soil))
    pm = _list(d.get("pruning_month"))
    if pm:
        out["pruning"] = ", ".join(dict.fromkeys(_tr(x, MONTH_MAP) for x in pm))
    prop = _list(d.get("propagation"))
    if prop:
        out["propagation"] = ", ".join(dict.fromkeys(_tr(x, PROP_MAP) for x in prop))
    att = _list(d.get("attracts"))
    if att:
        out["attracts"] = ", ".join(dict.fromkeys(_tr(x, ATTRACT_MAP) for x in att))
    ed = [n for k2, n in (("edible_fruit", "Früchte"), ("edible_leaf", "Blätter")) if _clean(d.get(k2)) is True]
    if ed:
        out["edible"] = "ja – " + " und ".join(ed)
    elif d.get("edible_fruit") is False and d.get("edible_leaf") in (False, None):
        out["edible"] = "nein"
    h = _height(d.get("dimensions") or d.get("dimension"))
    if h:
        out["height"] = h
    if d.get("tropical"):
        out["tropical"] = True
    cg = d.get("_care_guide") or {}
    if cg:
        out["care_guide"] = cg
    return out


def _list(v):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    return [x.strip() for x in v if isinstance(x, str) and x.strip() and _clean(x)]


def _height(dims):
    if isinstance(dims, dict):
        dims = [dims]
    for dm in dims or []:
        if not isinstance(dm, dict) or "height" not in str(dm.get("type", "")).lower():
            continue
        lo, hi, unit = dm.get("min_value"), dm.get("max_value"), str(dm.get("unit") or "").lower()
        f = 30.48 if "feet" in unit or unit == "ft" else 2.54 if "inch" in unit else 100 if unit in ("m", "meter", "meters") else 1
        try:
            vals = [int(round(float(x) * f / 10) * 10) or round(float(x) * f) for x in (lo, hi) if x not in (None, "", 0, "0")]
        except Exception:
            continue
        if not vals:
            continue
        fmt = lambda cm: f"{cm / 100:.1f} m".replace(".", ",") if cm >= 100 else f"{cm} cm"
        return " – ".join(dict.fromkeys(fmt(v) for v in vals))
    return None


def water_sentence(info, interval=None):
    """Gießhinweis als Satz, wie auf einem Pflanzenetikett."""
    w = (info.get("water") or "").lower()
    soil_min = info.get("opb_soil_min")
    rng = info.get("water_range") or (str(interval) if interval else None)
    if w == "viel" or (isinstance(soil_min, (int, float)) and soil_min >= 30):
        txt = "Gut feucht halten, Erde nicht austrocknen lassen."
    elif w == "mittel":
        txt = (f"Etwa alle {rng} Tage gießen, " if rng and "Wochen" not in rng else f"Etwa alle {rng} gießen, " if rng else "Regelmäßig gießen, ")
        txt += "sobald die oberste Erdschicht angetrocknet ist."
    elif w == "wenig":
        txt = "Sparsam gießen, Erde zwischendurch gut abtrocknen lassen."
    elif w == "sehr wenig":
        txt = "Nur selten gießen – verträgt längere Trockenheit."
    elif rng:
        txt = f"Etwa alle {rng} Tage gießen."
    else:
        return None
    if info.get("drought_tolerant") and w not in ("wenig", "sehr wenig"):
        txt += " Verträgt kurze Trockenphasen."
    return txt


# --------------------------------------------------------------- Open Plantbook

OPB_BASE = "https://open.plantbook.io/api/v1"
_opb_token = {"value": None, "exp": 0}


def opb_token():
    if not (key("OPENPLANTBOOK_CLIENT_ID") and key("OPENPLANTBOOK_CLIENT_SECRET")):
        return None
    if _opb_token["value"] and time.time() < _opb_token["exp"] - 60:
        return _opb_token["value"]
    body = urllib.parse.urlencode(
        {"grant_type": "client_credentials", "client_id": key("OPENPLANTBOOK_CLIENT_ID"), "client_secret": key("OPENPLANTBOOK_CLIENT_SECRET")}
    ).encode()
    data = http_json(
        f"{OPB_BASE}/token/", data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"
    )
    _opb_token["value"] = data.get("access_token")
    _opb_token["exp"] = time.time() + float(data.get("expires_in") or 3600)
    return _opb_token["value"]


def opb_find(sci_name):
    if not (key("OPENPLANTBOOK_CLIENT_ID") and key("OPENPLANTBOOK_CLIENT_SECRET")) or not sci_name:
        return None

    def go():
        tok = opb_token()
        h = {"Authorization": f"Bearer {tok}"}
        name = " ".join(sci_name.split()[:2])
        res = http_json(f"{OPB_BASE}/plant/search?" + urllib.parse.urlencode({"alias": name, "limit": 5}), headers=h)
        results = res.get("results") or []
        if not results:
            return None
        pid = results[0].get("pid")
        for r in results:
            if (r.get("pid") or "").lower() == name.lower():
                pid = r["pid"]
                break
        return http_json(f"{OPB_BASE}/plant/detail/{urllib.parse.quote(pid)}/", headers=h)

    return cached(f"opb:{sci_name.lower()}", None, go)


def map_opb(d):
    if not d:
        return {}
    out = {"opb_pid": d.get("pid")}

    def rng(a, b, unit):
        lo, hi = d.get(a), d.get(b)
        if lo is None and hi is None:
            return None
        return f"{lo if lo is not None else '?'}–{hi if hi is not None else '?'} {unit}".strip()

    for key, a, b, unit in (
        ("temp_range", "min_temp", "max_temp", "°C"),
        ("light_lux", "min_light_lux", "max_light_lux", "lx"),
        ("humidity", "min_env_humid", "max_env_humid", "%"),
        ("soil_moisture", "min_soil_moist", "max_soil_moist", "%"),
    ):
        v = rng(a, b, unit)
        if v:
            out[key] = v
    if d.get("min_temp") is not None:
        try:
            out["opb_min_temp"] = float(d["min_temp"])
        except Exception:
            pass
    if d.get("min_soil_moist") is not None:
        try:
            out["opb_soil_min"] = float(d["min_soil_moist"])
        except Exception:
            pass
    if d.get("category"):
        out["category"] = d["category"]
    if d.get("image_url"):
        out["opb_image"] = d["image_url"]
    return out


# ------------------------------------------------------------------- Pl@ntNet


def plantnet_identify(jpeg_bytes, organ="auto"):
    if not key("PLANTNET_API_KEY"):
        raise UpstreamError("Kein Pl@ntNet-Key hinterlegt (PLANTNET_API_KEY).")
    boundary = "----blattwerk" + uuid.uuid4().hex
    parts = []
    parts.append(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"images\"; filename=\"plant.jpg\"\r\n"
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode()
        + jpeg_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"organs\"\r\n\r\n{organ}\r\n".encode())
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    url = "https://my-api.plantnet.org/v2/identify/all?" + urllib.parse.urlencode(
        {"api-key": key("PLANTNET_API_KEY"), "lang": WIKI_LANG, "nb-results": 6, "include-related-images": "true"}
    )
    try:
        data = http_json(
            url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST", timeout=45
        )
    except UpstreamError as e:
        if str(e).startswith("404"):
            return {"results": [], "remaining": None}
        raise
    out = []
    for r in data.get("results") or []:
        sp = r.get("species") or {}
        img = None
        for im in r.get("images") or []:
            u = im.get("url") or {}
            img = u.get("m") or u.get("s") or u.get("o")
            if img:
                break
        out.append(
            {
                "score": round(float(r.get("score") or 0) * 100),
                "sci": sp.get("scientificNameWithoutAuthor") or sp.get("scientificName"),
                "common": (sp.get("commonNames") or [])[:3],
                "family": ((sp.get("family") or {}).get("scientificNameWithoutAuthor")),
                "thumb": img,
            }
        )
    return {"results": out, "remaining": data.get("remainingIdentificationRequests")}


# ---------------------------------------------------------------------- Lookup


def hardy_verdict(min_temp, local_min):
    if min_temp is None:
        return "unbekannt"
    try:
        min_temp = float(min_temp)
        local_min = float(local_min)
    except Exception:
        return "unbekannt"
    if min_temp <= local_min:
        return "ja"
    if min_temp <= local_min + 6:
        return "bedingt"
    return "nein"


def lookup(title=None, sci=None):
    """Sammelt alle Daten zu einer Art und liefert ein vorausgefülltes Pflanzenprofil."""
    warnings = []
    page = None
    if title:
        try:
            page = wiki_page(title)
        except UpstreamError as e:
            warnings.append(f"Wikipedia: {e}")
    if page is None and sci:
        try:
            hits = wiki_search(sci, limit=3)
            if hits:
                page = wiki_page(hits[0]["title"])
        except UpstreamError as e:
            warnings.append(f"Wikipedia: {e}")

    wd = wikidata_taxon(page.get("wikidata")) if page else {}
    sci_name = sci or wd.get("taxon")
    if not sci_name and page:
        m = re.search(r"\(([A-Z][a-z]+ [a-z\-]+)", page.get("extract") or "")
        if m:
            sci_name = m.group(1)

    info = {"sources": []}
    profile = {
        "species_common": (page or {}).get("title") or (wd.get("label_de") if wd else None),
        "species_sci": sci_name,
        "info": info,
    }
    if page:
        info["description"] = page.get("extract")
        info["wiki_url"] = page.get("url")
        info["sources"].append("Wikipedia")
        if page.get("image"):
            profile["ref_image_url"] = page["image"]
            info["ref_credit"] = "Musterbild: Wikipedia / Wikimedia Commons"

    if sci_name:
        try:
            raw = perenual_find(sci_name)
            p = map_perenual(raw)
            care_keys = {"light", "water", "water_interval", "min_temp", "toxic_humans", "toxic_pets"}
            if raw and not (care_keys & set(p)):
                warnings.append("Perenual: Art gefunden, aber im Gratis-Tarif keine Pflegedaten dafür")
            elif not raw:
                warnings.append(f"Perenual: keine Daten zu {sci_name} gefunden")
            if p:
                info.update({k: v for k, v in p.items() if k not in ("min_temp", "water_interval")})
                if "min_temp" in p:
                    profile["min_temp"] = p["min_temp"]
                if "water_interval" in p:
                    profile["water_interval"] = p["water_interval"]
                info["sources"].append("Perenual")
        except UpstreamError as e:
            warnings.append(f"Perenual: {e}")
        try:
            o = map_opb(opb_find(sci_name))
            if o:
                info.update({k: v for k, v in o.items() if k != "opb_min_temp"})
                if profile.get("min_temp") is None and o.get("opb_min_temp") is not None:
                    profile["min_temp"] = o["opb_min_temp"]
                info["sources"].append("Open Plantbook")
        except UpstreamError as e:
            warnings.append(f"Open Plantbook: {e}")

    ws = water_sentence(info, profile.get("water_interval"))
    if ws:
        info["water_text"] = ws

    if not profile.get("ref_image_url"):
        alt = info.get("perenual_image") or info.get("opb_image")
        if alt:
            profile["ref_image_url"] = alt
            info["ref_credit"] = "Musterbild: " + ("Perenual" if info.get("perenual_image") else "Open Plantbook")

    profile["hardy"] = hardy_verdict(profile.get("min_temp"), get_settings()["local_min_temp"])
    if "indoor_ok" in info and info["indoor_ok"] and profile["hardy"] == "nein":
        profile["location"] = "drinnen"
    profile["warnings"] = warnings
    return profile


def download_ref(url, plant_id):
    if not url or not url.startswith("http"):
        return url
    ext = ".png" if url.lower().split("?")[0].endswith(".png") else ".jpg"
    name = f"{plant_id}_{hashlib.sha1(url.encode()).hexdigest()[:10]}{ext}"
    path = REF_DIR / name
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read(15 * 1024 * 1024)
            path.write_bytes(data)
        except Exception:
            return url  # Fallback: extern verlinken
    return f"/ref/{name}"


# ---------------------------------------------------------------------- Plants

PLANT_FIELDS = (
    "name",
    "species_common",
    "species_sci",
    "location",
    "spot",
    "acquired",
    "notes",
    "hardy",
    "min_temp",
    "water_interval",
    "cover_photo_id",
)


def plant_row_to_dict(c, row, full=False):
    p = dict(row)
    try:
        p["info"] = json.loads(p.get("info") or "{}")
    except Exception:
        p["info"] = {}
    last = c.execute(
        "SELECT at FROM waterings WHERE plant_id=? AND kind='gegossen' ORDER BY at DESC LIMIT 1", (p["id"],)
    ).fetchone()
    p["last_watered"] = last["at"] if last else None
    p["next_water_in"] = None
    if p["water_interval"] and p["last_watered"]:
        try:
            d = (date.today() - datetime.fromisoformat(p["last_watered"]).date()).days
            p["next_water_in"] = int(p["water_interval"]) - d
        except Exception:
            pass
    cover = None
    if p.get("cover_photo_id"):
        cover = c.execute("SELECT * FROM photos WHERE id=?", (p["cover_photo_id"],)).fetchone()
    if not cover:
        cover = c.execute(
            "SELECT * FROM photos WHERE plant_id=? ORDER BY taken_at DESC, id DESC LIMIT 1", (p["id"],)
        ).fetchone()
    p["cover"] = (f"/photos/{cover['thumb'] or cover['file']}") if cover else None
    p["photo_count"] = c.execute("SELECT COUNT(*) FROM photos WHERE plant_id=?", (p["id"],)).fetchone()[0]
    if full:
        p["photos"] = [
            {**dict(r), "url": f"/photos/{r['file']}", "thumb_url": f"/photos/{r['thumb'] or r['file']}"}
            for r in c.execute(
                "SELECT * FROM photos WHERE plant_id=? ORDER BY taken_at DESC, id DESC", (p["id"],)
            )
        ]
        p["waterings"] = [
            dict(r)
            for r in c.execute(
                "SELECT * FROM waterings WHERE plant_id=? ORDER BY at DESC LIMIT 60", (p["id"],)
            )
        ]
    return p


def save_image_b64(data_url, prefix):
    if not data_url:
        return None
    m = re.match(r"data:image/(\w+);base64,(.*)", data_url, re.S)
    raw = base64.b64decode(m.group(2) if m else data_url)
    ext = "png" if m and m.group(1) == "png" else "jpg"
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
    (PHOTO_DIR / name).write_bytes(raw)
    return name


def _num(v, cast=float):
    if v in (None, ""):
        return None
    try:
        return cast(v)
    except Exception:
        return None


def upsert_plant(body, plant_id=None):
    vals = {k: body.get(k) for k in PLANT_FIELDS if k in body}
    if "min_temp" in vals:
        vals["min_temp"] = _num(vals["min_temp"])
    if "water_interval" in vals:
        vals["water_interval"] = _num(vals["water_interval"], int)
    if "info" in body:
        vals["info"] = json.dumps(body["info"] or {}, ensure_ascii=False)
    vals["updated_at"] = now_iso()
    with _db_lock, db() as c:
        if plant_id is None:
            if not (body.get("name") or body.get("species_common")):
                raise ValueError("Name fehlt")
            vals.setdefault("name", body.get("species_common"))
            vals["created_at"] = now_iso()
            cols = ",".join(vals)
            cur = c.execute(f"INSERT INTO plants ({cols}) VALUES ({','.join('?' * len(vals))})", list(vals.values()))
            plant_id = cur.lastrowid
        else:
            if not c.execute("SELECT 1 FROM plants WHERE id=?", (plant_id,)).fetchone():
                raise KeyError
            if vals:
                c.execute(
                    f"UPDATE plants SET {','.join(k + '=?' for k in vals)} WHERE id=?", [*vals.values(), plant_id]
                )
    # Musterbild lokal sichern (außerhalb des Locks, kann dauern)
    if "ref_image_url" in body:
        ref = body.get("ref_image_url")
        local = download_ref(ref, plant_id) if ref else None
        with db() as c:
            c.execute("UPDATE plants SET ref_image=? WHERE id=?", (local, plant_id))
    if body.get("photo"):
        add_photo(plant_id, body["photo"], set_cover=True)
    return plant_id


def add_photo(plant_id, payload, set_cover=False):
    full = save_image_b64(payload.get("full"), f"p{plant_id}")
    thumb = save_image_b64(payload.get("thumb"), f"p{plant_id}t") if payload.get("thumb") else None
    with _db_lock, db() as c:
        cur = c.execute(
            "INSERT INTO photos (plant_id, file, thumb, caption, taken_at) VALUES (?,?,?,?,?)",
            (plant_id, full, thumb, payload.get("caption"), payload.get("taken_at") or now_iso()),
        )
        pid = cur.lastrowid
        if set_cover:
            c.execute("UPDATE plants SET cover_photo_id=? WHERE id=?", (pid, plant_id))
    return pid


def delete_files(*names):
    for n in names:
        if n:
            try:
                (PHOTO_DIR / n).unlink(missing_ok=True)
            except Exception:
                pass


# --------------------------------------------------------------------- Handler

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "Blattwerk/" + VERSION

    def log_message(self, fmt, *args):
        if os.environ.get("LOG_REQUESTS"):
            super().log_message(fmt, *args)

    # -- helpers
    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def err(self, status, msg):
        self.send_json({"error": msg}, status)

    def body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("Upload zu groß")
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def send_file(self, path, cache=True):
        try:
            path = path.resolve()
        except Exception:
            return self.err(404, "Nicht gefunden")
        if not path.is_file():
            return self.err(404, "Nicht gefunden")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if cache else "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def safe_join(self, base, rel):
        p = (base / rel).resolve()
        if base.resolve() not in p.parents and p != base.resolve():
            return None
        return p

    # -- routing
    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_DELETE(self):
        self.route("DELETE")

    # -- Anmeldung über Pocket ID (nur wenn OIDC_* gesetzt ist)
    def base_url(self):
        proto = (self.headers.get("X-Forwarded-Proto") or "http").split(",")[0].strip()
        host = (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or f"localhost:{PORT}").split(",")[0]
        return f"{proto}://{host.strip()}"

    def cookie(self, name):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return None

    def set_cookie(self, name, value, max_age):
        secure = "; Secure" if self.base_url().startswith("https://") else ""
        self.send_header("Set-Cookie", f"{name}={value}; Max-Age={max_age}; Path=/; HttpOnly; SameSite=Lax{secure}")

    def redirect(self, location, cookies=()):
        self.send_response(302)
        self.send_header("Location", location)
        for c in cookies:
            self.set_cookie(*c)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def signed_in(self):
        return bool(pocketid.unsign(self.cookie(SESSION_COOKIE), oidc_key(), max_age=SESSION_MAX_AGE))

    def auth_page(self, msg, status=403, cookies=()):
        html = (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                f"<title>Blattwerk</title><body style='font-family:system-ui;max-width:420px;margin:12vh auto;"
                f"padding:0 16px'><h1>🌿 Blattwerk</h1><p>{msg}</p><p><a href='/auth/pocketid'>"
                f"{OIDC.label}</a></p></body>").encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        for c in cookies:
            self.set_cookie(*c)
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def auth(self, method, path, qs):
        """Gibt True zurück, wenn die Anfrage erledigt ist (Weiterleitung, Fehler, Anmeldeschritt)."""
        if path == "/auth/pocketid":
            try:
                url, pending = OIDC.begin(self.base_url() + "/auth/pocketid/zurueck", qs.get("next", "/"))
            except pocketid.OIDCError as e:
                self.auth_page(str(e).replace("<", "&lt;"))
                return True
            self.redirect(url, [(pocketid.PENDING_COOKIE, pocketid.sign(pending, oidc_key()),
                                 pocketid.PENDING_MAX_AGE)])
            return True
        if path == "/auth/pocketid/zurueck":
            pending = pocketid.unsign(self.cookie(pocketid.PENDING_COOKIE), oidc_key())
            try:
                info = OIDC.complete(qs, pending)
            except pocketid.OIDCError as e:
                self.auth_page(str(e).replace("<", "&lt;"))
                return True
            session = pocketid.sign({"sub": info["sub"], "name": info["name"] or info["username"],
                                     "t": int(time.time())}, oidc_key())
            self.redirect(pending["next"], [(SESSION_COOKIE, session, SESSION_MAX_AGE),
                                            (pocketid.PENDING_COOKIE, "", 0)])
            return True
        if path == "/auth/abmelden":
            self.auth_page("Du bist abgemeldet.", 200, [(SESSION_COOKIE, "", 0)])
            return True
        if not OIDC.enabled or path in OPEN_PATHS:
            return False
        if method != "GET":
            origin = self.headers.get("Origin")
            if origin and urllib.parse.urlsplit(origin).netloc != urllib.parse.urlsplit(self.base_url()).netloc:
                self.err(403, "Anfrage von fremder Seite")
                return True
        if self.signed_in():
            return False
        if path.startswith("/api/"):
            self.send_json({"error": "Bitte anmelden", "login": "/auth/pocketid"}, 401)
        else:
            self.redirect("/auth/pocketid?next=" + urllib.parse.quote(self.path, safe="/"))
        return True

    def route(self, method):
        u = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(u.path)
        qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if self.auth(method, path, qs):
                return
            if path.startswith("/api/"):
                return self.api(method, path[5:].strip("/").split("/"), qs)
            if method != "GET":
                return self.err(405, "Methode nicht erlaubt")
            if path.startswith("/photos/"):
                p = self.safe_join(PHOTO_DIR, path[8:])
                return self.send_file(p) if p else self.err(404, "Nicht gefunden")
            if path.startswith("/ref/"):
                p = self.safe_join(REF_DIR, path[5:])
                return self.send_file(p) if p else self.err(404, "Nicht gefunden")
            rel = path.lstrip("/") or "index.html"
            p = self.safe_join(STATIC_DIR, rel)
            if not p or not p.is_file():
                p = STATIC_DIR / "index.html"
            return self.send_file(p, cache=False)
        except BrokenPipeError:
            pass
        except Exception as e:  # noqa
            traceback.print_exc()
            try:
                self.err(500, f"Interner Fehler: {e}")
            except Exception:
                pass

    def api(self, method, parts, qs):
        head = parts[0] if parts else ""

        if head == "config" and method == "GET":
            return self.send_json(
                {
                    "version": VERSION,
                    "keys": {n: key_source(n) for n in KEY_NAMES},
                    "plantnet": bool(key("PLANTNET_API_KEY")),
                    "perenual": bool(key("PERENUAL_API_KEY")),
                    "openplantbook": bool(key("OPENPLANTBOOK_CLIENT_ID") and key("OPENPLANTBOOK_CLIENT_SECRET")),
                    "wiki_lang": WIKI_LANG,
                    "settings": get_settings(),
                }
            )

        if head == "settings" and method == "PUT":
            body = self.body_json()
            with db() as c:
                for k, v in body.items():
                    if k in DEFAULT_SETTINGS:
                        c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (k, json.dumps(v)))
                for name, val in (body.get("keys") or {}).items():
                    if name not in KEY_NAMES or val is None:
                        continue
                    val = str(val).strip()
                    if val:
                        c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", ("key_" + name, json.dumps(val)))
                    else:
                        c.execute("DELETE FROM settings WHERE key=?", ("key_" + name,))
            _opb_token["value"] = None
            return self.send_json({**get_settings(), "keys": {n: key_source(n) for n in KEY_NAMES}})

        if head == "search" and method == "GET":
            q = (qs.get("q") or "").strip()
            if len(q) < 2:
                return self.send_json({"results": []})
            try:
                return self.send_json({"results": wiki_search(q)})
            except UpstreamError as e:
                return self.err(502, str(e))

        if head == "lookup" and method == "GET":
            if not (qs.get("title") or qs.get("sci")):
                return self.err(400, "title oder sci fehlt")
            _tl.force = qs.get("refresh") == "1"
            try:
                return self.send_json(lookup(qs.get("title"), qs.get("sci")))
            finally:
                _tl.force = False

        if head == "identify" and method == "POST":
            body = self.body_json()
            img = body.get("image") or ""
            m = re.match(r"data:image/\w+;base64,(.*)", img, re.S)
            try:
                raw = base64.b64decode(m.group(1) if m else img)
                return self.send_json(plantnet_identify(raw, body.get("organ") or "auto"))
            except UpstreamError as e:
                return self.err(502, str(e))

        if head == "rehardy" and method == "POST":
            # Winterhärte aller Pflanzen nach neuer Ortstemperatur neu bewerten
            local = get_settings()["local_min_temp"]
            with _db_lock, db() as c:
                rows = c.execute("SELECT id, min_temp FROM plants WHERE min_temp IS NOT NULL").fetchall()
                for r in rows:
                    c.execute("UPDATE plants SET hardy=? WHERE id=?", (hardy_verdict(r["min_temp"], local), r["id"]))
            return self.send_json({"updated": len(rows)})

        if head == "plants":
            if len(parts) == 1:
                if method == "GET":
                    with db() as c:
                        rows = c.execute("SELECT * FROM plants ORDER BY name COLLATE NOCASE").fetchall()
                        return self.send_json({"plants": [plant_row_to_dict(c, r) for r in rows]})
                if method == "POST":
                    try:
                        pid = upsert_plant(self.body_json())
                    except ValueError as e:
                        return self.err(400, str(e))
                    with db() as c:
                        r = c.execute("SELECT * FROM plants WHERE id=?", (pid,)).fetchone()
                        return self.send_json(plant_row_to_dict(c, r, full=True), 201)
            try:
                pid = int(parts[1])
            except Exception:
                return self.err(404, "Unbekannte Pflanze")
            sub = parts[2] if len(parts) > 2 else None

            if sub is None:
                if method == "GET":
                    with db() as c:
                        r = c.execute("SELECT * FROM plants WHERE id=?", (pid,)).fetchone()
                        if not r:
                            return self.err(404, "Unbekannte Pflanze")
                        return self.send_json(plant_row_to_dict(c, r, full=True))
                if method == "PUT":
                    try:
                        upsert_plant(self.body_json(), pid)
                    except KeyError:
                        return self.err(404, "Unbekannte Pflanze")
                    with db() as c:
                        r = c.execute("SELECT * FROM plants WHERE id=?", (pid,)).fetchone()
                        return self.send_json(plant_row_to_dict(c, r, full=True))
                if method == "DELETE":
                    with _db_lock, db() as c:
                        photos = c.execute("SELECT file, thumb FROM photos WHERE plant_id=?", (pid,)).fetchall()
                        ref = c.execute("SELECT ref_image FROM plants WHERE id=?", (pid,)).fetchone()
                        c.execute("DELETE FROM plants WHERE id=?", (pid,))
                    for ph in photos:
                        delete_files(ph["file"], ph["thumb"])
                    if ref and ref["ref_image"] and ref["ref_image"].startswith("/ref/"):
                        (REF_DIR / ref["ref_image"][5:]).unlink(missing_ok=True)
                    return self.send_json({"ok": True})

            if sub == "photos" and method == "POST":
                body = self.body_json()
                ph = add_photo(pid, body, set_cover=bool(body.get("set_cover")))
                return self.send_json({"id": ph}, 201)

            if sub == "water" and method == "POST":
                body = self.body_json()
                kind = body.get("kind") or "gegossen"
                at = body.get("at") or now_iso()
                with _db_lock, db() as c:
                    c.execute("INSERT INTO waterings (plant_id, at, kind) VALUES (?,?,?)", (pid, at, kind))
                return self.send_json({"ok": True}, 201)

        if head == "photos" and len(parts) >= 2:
            phid = int(parts[1])
            if method == "DELETE":
                with _db_lock, db() as c:
                    r = c.execute("SELECT * FROM photos WHERE id=?", (phid,)).fetchone()
                    if not r:
                        return self.err(404, "Foto nicht gefunden")
                    c.execute("DELETE FROM photos WHERE id=?", (phid,))
                    c.execute("UPDATE plants SET cover_photo_id=NULL WHERE cover_photo_id=?", (phid,))
                delete_files(r["file"], r["thumb"])
                return self.send_json({"ok": True})
            if method == "PUT":
                body = self.body_json()
                with _db_lock, db() as c:
                    r = c.execute("SELECT plant_id FROM photos WHERE id=?", (phid,)).fetchone()
                    if not r:
                        return self.err(404, "Foto nicht gefunden")
                    if "caption" in body:
                        c.execute("UPDATE photos SET caption=? WHERE id=?", (body["caption"], phid))
                    if body.get("cover"):
                        c.execute("UPDATE plants SET cover_photo_id=? WHERE id=?", (phid, r["plant_id"]))
                return self.send_json({"ok": True})

        if head == "waterings" and len(parts) >= 2 and method == "DELETE":
            with _db_lock, db() as c:
                c.execute("DELETE FROM waterings WHERE id=?", (int(parts[1]),))
            return self.send_json({"ok": True})

        return self.err(404, "Unbekannter Endpunkt")


def main():
    init_db()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"🌿 Blattwerk {VERSION} läuft auf Port {PORT} – Daten in {DATA_DIR}")
    print(
        "   Quellen: Wikipedia ✓  "
        f"Perenual {'✓' if key('PERENUAL_API_KEY') else '–'}  "
        f"Open Plantbook {'✓' if key('OPENPLANTBOOK_CLIENT_ID') and key('OPENPLANTBOOK_CLIENT_SECRET') else '–'}  "
        f"Pl@ntNet {'✓' if key('PLANTNET_API_KEY') else '–'}",
        flush=True,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
