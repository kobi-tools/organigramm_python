"""Überträgt einen Ordnerbaum per HTTPS an eine Ablage-Webansicht."""

import http.client
import json
import os
import ssl
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


MAX_STRUKTUR = 8 * 1024 * 1024


def server_adresse(text):
    text = text.strip()
    url = urlsplit(text if "://" in text else "https://" + text)
    if (url.scheme != "https" or not url.hostname or url.username is not None or
            url.query or url.fragment or url.port == 0 or
            any(c.isspace() or c == "\\" for c in text)):
        raise ValueError("Bitte eine HTTPS-Adresse eingeben, z. B. https://ablage.firma.local.")
    return urlunsplit((url.scheme, url.netloc, url.path.rstrip("/") + "/", "", ""))


def ziel_datei():
    ordner = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config"))
    return ordner / "Ordner-Organigramm" / "web-adresse"


def gespeichertes_ziel():
    try:
        return ziel_datei().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def veroeffentliche(ziel, schluessel, struktur):
    ziel = server_adresse(ziel)
    url = urlsplit(ziel)
    if not schluessel or not schluessel.isascii() or any(c.isspace() for c in schluessel):
        raise ValueError("Bitte den Veröffentlichungsschlüssel eingeben.")
    daten = json.dumps(struktur, ensure_ascii=False).encode("utf-8")
    if len(daten) > MAX_STRUKTUR:
        raise ValueError("Der Baum ist zu groß. Wähle weniger Ebenen und versuche es erneut.")
    try:
        with closing(http.client.HTTPSConnection(url.hostname, url.port, timeout=45)) as server:
            server.request("PUT", url.path + "api/struktur", body=daten, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {schluessel}",
            })
            antwort = server.getresponse()
            status, inhalt = antwort.status, antwort.read(8192)
    except ssl.SSLCertVerificationError as fehler:
        raise ValueError("Das HTTPS-Zertifikat der Ablage konnte nicht geprüft werden.") from fehler
    except (OSError, http.client.HTTPException) as fehler:
        raise ValueError("Die Ablage ist nicht erreichbar. Bitte prüfe Adresse und Verbindung.") from fehler
    if status == 401:
        raise ValueError("Der Veröffentlichungsschlüssel stimmt nicht.")
    if status in (404, 405):
        raise ValueError("Die Ablage nimmt keine Veröffentlichungen an. Prüfe die Adresse und Server-Einrichtung.")
    if status == 413:
        raise ValueError("Der Server meldet einen zu großen Baum. Wähle weniger Ebenen.")
    if 300 <= status < 400:
        raise ValueError("Die Adresse leitet weiter. Gib die endgültige HTTPS-Adresse der Ablage ein.")
    try:
        ok = status == 200 and json.loads(inhalt).get("veroeffentlicht") is True
    except (ValueError, AttributeError):
        ok = False
    if not ok:
        raise ValueError(f"Die Ablage hat den Baum nicht übernommen (HTTP {status}).")
    try:
        datei = ziel_datei()
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(ziel, encoding="utf-8")
    except OSError:
        pass
    return ziel
