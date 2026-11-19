#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Ordner-Organigramm v2
=====================

Macht aus einer Ordnerstruktur ein übersichtliches Organigramm zum Verschicken.
Gezeigt werden nur Ordner, keine Dateien und keine Bilder.

Neu in v2, damit auch tiefe Strukturen übersichtlich bleiben:
  - Ordner mit vielen Unterordnern werden gekürzt ("+ 73 weitere").
    In der HTML-Datei lässt sich der Rest per Klick aufklappen.
  - Immer gleich aufgebaute Ordner werden zusammengefasst: Statt 25-mal dieselben
    7 Unterordner steht am Ordner nur ein Buchstabe, der Aufbau einmal darunter.
  - Große Hauptordner werden breiter und nutzen mehrere Spalten.
  - Das PDF wird wenn möglich auf eine Seite eingepasst.

Ergebnis (landet im selben Ordner wie dieses Skript):
  PDF   zum Anhängen an eine Mail oder zum Ausdrucken
  HTML  öffnet in jedem Browser, gleiche Ansicht wie das PDF
  TXT   einfacher Textbaum, z. B. direkt in den Mailtext kopieren

Voraussetzungen
  Python 3.8 oder neuer, keine Zusatzpakete nötig.
  Das PDF wird über Microsoft Edge erzeugt (ist bei Windows 10/11 dabei).

Starten
  Doppelklick auf diese Datei (dafür unten bei ORDNER den Ordner eintragen)
  oder in der Eingabeaufforderung:
      py ordner_organigramm_v2.py "D:\Ordner"
      py ordner_organigramm_v2.py "D:\Ordner" --tiefe 2
      py ordner_organigramm_v2.py "D:\Ordner" --max 0   (nichts kürzen, alles auflisten)
      py ordner_organigramm_v2.py -h                    (zeigt alle Optionen)
"""

from __future__ import annotations

import argparse
import collections
import ctypes
import datetime as dt
import fnmatch
import hashlib
import html
import math
import os
import re
import shutil
import stat
import string
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================================
# EINSTELLUNGEN  (hier anpassen, danach einfach per Doppelklick starten)
# ============================================================================

# Welcher Ordner soll dargestellt werden? Leer = beim Start angeben.
# Beispiel: ORDNER = r"D:\Ablage"
ORDNER = ""

# Überschrift. Leer lassen = "Ordnerstruktur <Ordnername>"
TITEL = ""

# Optionale Zeile unter der Überschrift, z. B. "Neue Ablage, gültig ab 01.11.2026"
UNTERTITEL = ""

# Wie viele Ebenen unterhalb des Hauptordners gezeigt werden:
#   0 = alle Ebenen, also die komplette Struktur
#   1 = nur die Hauptordner, 2 = plus deren Unterordner, 3 = noch eine Ebene tiefer ...
# Bei einer Begrenzung wird alles darunter nur als kleine Zahl angedeutet (z. B. "+5").
MAX_TIEFE = 4

# Höchstens so viele Unterordner pro Ordner auflisten (0 = alle).
# Der Rest erscheint dann als "+ 73 weitere".
MAX_PRO_ORDNER = 6

# Direkt unter einem Hauptordner darf es etwas mehr sein (0 = alle).
MAX_UNTER_HAUPTORDNER = 12

# Immer gleich aufgebaute Ordner zusammenfassen? (True / False)
GLEICHE_ZUSAMMENFASSEN = True

# Wie viele Spalten die Seite hat. Große Hauptordner belegen mehrere davon.
# Für A4 quer passen 6 gut, für A4 hoch eher 4.
MAX_SPALTEN = 6

# Anzahl der Dateien je Ordner klein mit anzeigen? (True / False)
DATEIEN_ZAEHLEN = False

# Den vollständigen Pfad oben im Dokument anzeigen? (True / False)
PFAD_ANZEIGEN = True

# Papierformat für das PDF: "A4 landscape" (quer), "A4 portrait" (hoch), "A3 landscape"
PAPIER = "A4 landscape"

# Wohin die Ergebnisse geschrieben werden. Leer = Ordner, in dem dieses Skript liegt.
AUSGABE_ORDNER = ""

# PDF erzeugen und am Ende automatisch öffnen? (True / False)
PDF_ERSTELLEN = True
PDF_OEFFNEN = True

# Ordner mit diesen Namen werden übersprungen (Groß-/Kleinschreibung egal, * und ? erlaubt).
IGNORIEREN = [
    "$RECYCLE.BIN",
    "System Volume Information",
    "#recycle",          # Papierkorb auf Synology-NAS
    "@eaDir",            # Vorschaubilder auf Synology-NAS
    "__pycache__",
    ".*",                # Ordner, die mit einem Punkt beginnen
]

# Versteckte Ordner und Systemordner überspringen? (True / False)
VERSTECKTE_IGNORIEREN = True

# ============================================================================
# Ab hier muss nichts mehr angepasst werden.
# ============================================================================

IST_WINDOWS = os.name == "nt"
VERSTECKT = stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM
VERKNUEPFUNG = stat.FILE_ATTRIBUTE_REPARSE_POINT

# Akzentfarben für die Hauptordner (werden der Reihe nach vergeben)
FARBEN = [
    "#2f6fdb", "#0f9488", "#d4800f", "#7c4ddb", "#d14343",
    "#3f8f45", "#c2417f", "#5b6b7c", "#0e8fb0", "#9a7417",
]

# Fehlen nur so wenige Ordner, werden sie trotzdem gezeigt. "+ 1 weiterer" bräuchte
# genauso viel Platz wie der Ordner selbst.
PUFFER = 2

# Ab wann ein Aufbau als wiederkehrend gilt: mindestens so viele Unterordner ...
MUSTER_MIN_UNTERORDNER = 3
# ... und mindestens so oft in der Struktur.
MUSTER_MIN_ANZAHL = 3

# Schätzwerte für die Aufteilung der Seite
MM_PRO_ZEICHEN = 1.65
MM_PRO_ZEILE = 4.0
MIN_SPALTE_MM = 30
REIHEN_ABSTAND = 2      # in Zeilen

# So weit wird das PDF notfalls verkleinert, damit es auf eine Seite passt
ZOOM_STUFEN = (1.0, 0.94, 0.88, 0.82, 0.76, 0.7)


@dataclass(eq=False)
class Ordner:
    name: str
    kinder: list = field(default_factory=list)
    versteckt: list = field(default_factory=list)   # gekürzt, nur in der HTML aufklappbar
    tiefer: int = 0            # Unterordner unterhalb von MAX_TIEFE
    dateien: int = 0
    fehler: str = ""
    verknuepfung: bool = False
    muster: str = ""           # Buchstabe, wenn der Ordner einen wiederkehrenden Aufbau hat


# ----------------------------------------------------------------------------
# Ordner einlesen
# ----------------------------------------------------------------------------

def natuerlich(name: str):
    """Sortiert wie der Explorer: "2 ..." kommt vor "10 ..."."""
    teile = re.split(r"(\d+)", name)
    return [int(t) if i % 2 else t.casefold() for i, t in enumerate(teile)]


def langer_pfad(pfad: str) -> str:
    """Erlaubt unter Windows auch Pfade mit mehr als 260 Zeichen."""
    if IST_WINDOWS and len(pfad) >= 240 and not pfad.startswith("\\\\?\\"):
        if pfad.startswith("\\\\"):
            return "\\\\?\\UNC\\" + pfad[2:]
        return "\\\\?\\" + pfad
    return pfad


def attribute(eintrag) -> int:
    try:
        return getattr(eintrag.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return 0


class Leser:
    def __init__(self, cfg, melde=print):
        self.cfg = cfg
        self.melde = melde
        self.muster = [m.casefold() for m in cfg.ignorieren]
        self.anzahl = 0

    def ueberspringen(self, eintrag) -> bool:
        name = eintrag.name.casefold()
        if any(fnmatch.fnmatchcase(name, m) for m in self.muster):
            return True
        return bool(self.cfg.versteckte_ignorieren and attribute(eintrag) & VERSTECKT)

    def inhalt(self, pfad: str):
        """Liefert (Unterordner, Anzahl Dateien, Fehlertext)."""
        ordner, dateien = [], 0
        try:
            with os.scandir(langer_pfad(pfad)) as eintraege:
                for e in eintraege:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if not self.ueberspringen(e):
                                ordner.append(e)
                        elif e.is_file(follow_symlinks=False):
                            if not (self.cfg.versteckte_ignorieren and attribute(e) & VERSTECKT):
                                dateien += 1
                    except OSError:
                        continue
        except PermissionError:
            return [], 0, "kein Zugriff"
        except OSError:
            return [], 0, "nicht lesbar"
        ordner.sort(key=lambda e: natuerlich(e.name))
        return ordner, dateien, ""

    def lies(self, pfad: str, name: str, ebene: int = 0) -> Ordner:
        knoten = Ordner(name=name)
        unterordner, knoten.dateien, knoten.fehler = self.inhalt(pfad)
        self.anzahl += 1
        if self.anzahl % 250 == 0:
            self.melde(f"  ... {self.anzahl} Ordner gelesen")

        if self.cfg.tiefe and ebene >= self.cfg.tiefe:
            knoten.tiefer = len(unterordner)
            return knoten

        for e in unterordner:
            if attribute(e) & VERKNUEPFUNG:
                # Verknüpfte Ordner (Junctions) nur nennen, nicht hineingehen
                knoten.kinder.append(Ordner(name=e.name, verknuepfung=True))
            else:
                knoten.kinder.append(self.lies(e.path, e.name, ebene + 1))
        return knoten


def anzahl_ordner(k: Ordner) -> int:
    return sum(1 + anzahl_ordner(c) for c in k.kinder + k.versteckt)


def struktur_lesen(pfad: str, tiefe: int, melde=print) -> dict:
    """Liest den ungekürzten Ordnerbaum für die Webansicht."""
    def als_daten(ordner):
        daten = {"name": ordner.name, "kinder": [als_daten(kind) for kind in ordner.kinder]}
        if ordner.tiefer:
            daten["tiefer"] = ordner.tiefer
        if ordner.fehler or ordner.verknuepfung:
            daten["hinweis"] = ordner.fehler or "Verknüpfung"
        return daten

    wurzel = os.path.abspath(os.path.expandvars(os.path.expanduser(pfad)))
    cfg = einstellungen(["--tiefe", str(tiefe), "--", wurzel])
    baum = Leser(cfg, melde).lies(wurzel, os.path.basename(wurzel.rstrip("\\/")) or wurzel)
    if baum.fehler:
        raise ValueError(f"{wurzel}: {baum.fehler}")
    return {
        "version": 1,
        "quelle": hashlib.sha256(os.path.normcase(wurzel).encode("utf-8")).hexdigest(),
        "pfad": wurzel,
        "stand": dt.date.today().isoformat(),
        "tiefe": cfg.tiefe,
        "baum": als_daten(baum),
    }


def aufgefuehrt(k: Ordner) -> int:
    """Wie viele Ordner tatsächlich einzeln zu sehen sind."""
    return 0 if k.muster else sum(1 + aufgefuehrt(c) for c in k.kinder)


def irgendwo(k: Ordner, merkmal) -> bool:
    if merkmal(k):
        return True
    return not k.muster and any(irgendwo(c, merkmal) for c in k.kinder)


def weitere(n: int, wort: str = "") -> str:
    """"1 weiterer" / "5 weitere", optional mit Wort dahinter."""
    text = f"{n} weiterer" if n == 1 else f"{n} weitere"
    return f"{text} {wort}" if wort else text


def dateien_text(n: int) -> str:
    return f"{n} Datei" if n == 1 else f"{n} Dateien"


# ----------------------------------------------------------------------------
# Struktur vereinfachen
# ----------------------------------------------------------------------------

def finde_muster(baum: Ordner) -> dict:
    """Sucht Ordner, die immer wieder genau dieselben Unterordner haben, und markiert sie.
    Liefert {Buchstabe: Namen der Unterordner}. Hauptordner bleiben immer sichtbar."""
    def aufbau_von(k):
        return tuple(c.name.casefold() for c in k.kinder)

    haeufigkeit = collections.Counter()

    def zaehlen(k):
        if len(k.kinder) >= MUSTER_MIN_UNTERORDNER:
            haeufigkeit[aufbau_von(k)] += 1
        for c in k.kinder:
            zaehlen(c)

    muster, vergeben = {}, {}

    def markieren(k):
        aufbau = aufbau_von(k)
        if len(k.kinder) >= MUSTER_MIN_UNTERORDNER and haeufigkeit[aufbau] >= MUSTER_MIN_ANZAHL:
            if aufbau not in vergeben:
                vergeben[aufbau] = string.ascii_uppercase[len(muster) % 26]
                muster[vergeben[aufbau]] = [c.name for c in k.kinder]
            k.muster = vergeben[aufbau]
        else:
            for c in k.kinder:
                markieren(c)

    for haupt in baum.kinder:
        for c in haupt.kinder:
            zaehlen(c)
    for haupt in baum.kinder:
        for c in haupt.kinder:
            markieren(c)
    return muster


def auswahl(kinder: list, n: int) -> list:
    """Die ersten n Ordner. Haben nur ganz wenige überhaupt eigene Unterordner
    (z. B. ein einziger von 170), bleiben diese auf jeden Fall dabei."""
    besondere = [c for c in kinder if c.kinder or c.tiefer]
    if not 0 < len(besondere) <= 2:
        return kinder[:n]
    rest = [c for c in kinder if not (c.kinder or c.tiefer)]
    behalten = set(besondere + rest[:max(0, n - len(besondere))])
    return [c for c in kinder if c in behalten]


def kuerzen(k: Ordner, cfg, ebene: int = 0):
    """Begrenzt die Unterordner je Ordner. Ebene 0 ist die Wurzel, ihre Unterordner
    sind die Hauptordner und werden nie gekürzt."""
    if k.muster:
        return
    grenze = cfg.max_unter_haupt if ebene == 1 else cfg.max_pro_ordner
    if ebene >= 1 and grenze > 0 and len(k.kinder) > grenze + PUFFER:
        behalten = set(auswahl(k.kinder, grenze))
        k.versteckt = [c for c in k.kinder if c not in behalten]
        k.kinder = [c for c in k.kinder if c in behalten]
    for c in k.kinder + k.versteckt:
        kuerzen(c, cfg, ebene + 1)


def muster_in(k: Ordner) -> set:
    """Welche Buchstaben in einer Karte zu sehen sind."""
    if k.muster:
        return {k.muster}
    gefunden = set()
    for c in k.kinder:
        gefunden |= muster_in(c)
    return gefunden


# ----------------------------------------------------------------------------
# Seite aufteilen
# ----------------------------------------------------------------------------

def seite_mm(papier: str):
    """Bedruckbare Fläche als (Breite, Höhe) in mm."""
    p = papier.casefold()
    lang, kurz = (420, 297) if "a3" in p else (297, 210)
    breite, hoehe = (kurz, lang) if "portrait" in p or "hoch" in p else (lang, kurz)
    return breite - 22, hoehe - 20


def umbruch(text: str, zeichen: int) -> int:
    """Ungefähre Anzahl Zeilen für einen Namen in einer Spalte mit so vielen Zeichen."""
    return 1 + len(text) // max(zeichen, 8)


def zeilen_liste(k: Ordner, zeichen: int) -> int:
    if k.muster:
        return 0
    n = sum(umbruch(c.name, zeichen) + zeilen_liste(c, zeichen - 3) for c in k.kinder)
    return n + (1 if k.versteckt else 0)


def hoehe_in_spalten(bloecke: list, spalten: int) -> int:
    """Kleinste Höhe, mit der die Blöcke der Reihe nach in die Spalten passen."""
    h = max(max(bloecke), math.ceil(sum(bloecke) / spalten))
    while True:
        benutzt, belegt = 1, 0
        for b in bloecke:
            if belegt + b > h:
                benutzt, belegt = benutzt + 1, 0
            belegt += b
        if benutzt <= spalten:
            return h
        h += 1


def laengstes_wort(k: Ordner) -> int:
    if k.muster:
        return 0
    return max((max(max(map(len, c.name.split()), default=0), laengstes_wort(c)) for c in k.kinder), default=0)


def messe_karte(k: Ordner, breite_mm: float, cfg):
    """Schätzt für eine Kartenbreite: (Höhe in Zeilen, Anzahl innerer Spalten)."""
    zeichen = int(breite_mm / MM_PRO_ZEICHEN)
    kopf = umbruch(k.name, zeichen - 6)
    if not (k.kinder or k.versteckt):
        return kopf, 1
    beste = None
    wort = laengstes_wort(k)
    for innen in range(1, max(1, int(breite_mm // MIN_SPALTE_MM)) + 1):
        z = int(((breite_mm - 6 - (innen - 1) * 3.7) / innen - 3.5) / MM_PRO_ZEICHEN)
        bloecke = [umbruch(c.name, z) + zeilen_liste(c, z - 2) for c in k.kinder]
        if k.versteckt:
            bloecke.append(1)
        # Keine Spalten, in denen Wörter mitten durchbrochen würden
        if innen > len(bloecke) or (innen > 1 and wort > z - 1):
            break
        h = hoehe_in_spalten(bloecke, innen)
        if beste is None or h < beste[0]:
            beste = (h, innen)
    legende = sum(umbruch(legende_text(b, cfg), zeichen) for b in muster_in(k))
    return kopf + beste[0] + legende + 1, beste[1]


def plane_karten(baum: Ordner, cfg, zoom: float = 1.0):
    """Verteilt die Hauptordner in Reihen, die Reihenfolge bleibt erhalten. Probiert
    verschiedene Zielhöhen aus und nimmt die Aufteilung, die insgesamt am flachsten ist.
    Kleinere Schrift (zoom) heißt: Es passt mehr in jede Spalte.
    Liefert ([[(Karte, Breite in Spalten, innere Spalten), ...], ...], Gesamthöhe)."""
    breite = seite_mm(cfg.papier)[0] / zoom
    spalte = breite / cfg.spalten
    gemerkt = {}

    def mass(k, s):
        schluessel = (id(k), s)
        if schluessel not in gemerkt:
            gemerkt[schluessel] = messe_karte(k, s * spalte, cfg)
        return gemerkt[schluessel]

    beste = None
    for ziel in range(3, 121):
        reihen, reihe, frei = [], [], cfg.spalten
        for k in baum.kinder:
            s = next((s for s in range(1, cfg.spalten + 1) if mass(k, s)[0] <= ziel), cfg.spalten)
            if s > frei:
                reihen.append(reihe)
                reihe, frei = [], cfg.spalten
            reihe.append([k, s])
            frei -= s
        reihen.append(reihe)

        # Freie Spalten bekommt die höchste Karte, solange sie dadurch flacher wird
        for r in reihen:
            frei = cfg.spalten - sum(s for _, s in r)
            while frei > 0:
                groesste = max(r, key=lambda e: mass(e[0], e[1])[0])
                jetzt = mass(groesste[0], groesste[1])[0]
                if jetzt <= 6 or mass(groesste[0], groesste[1] + 1)[0] >= jetzt:
                    break
                groesste[1] += 1
                frei -= 1

        gesamt = sum(max(mass(k, s)[0] for k, s in r) for r in reihen)
        gesamt += REIHEN_ABSTAND * (len(reihen) - 1)
        if beste is None or gesamt <= beste[1]:
            beste = ([[(k, s, mass(k, s)[1]) for k, s in r] for r in reihen], gesamt)
    return beste


def zeilen_pro_seite(papier: str) -> int:
    """Wie viele Listenzeilen ungefähr unter den Kopf einer Seite passen."""
    return int((seite_mm(papier)[1] - 45) / MM_PRO_ZEILE)


# ----------------------------------------------------------------------------
# HTML / PDF
# ----------------------------------------------------------------------------

CSS = """
:root {
  --text: #1c2632;
  --text2: #4a5866;
  --text3: #7a8693;
  --linie: #9fabb7;
  --rand: #d8dee5;
  --zweig: #c4ccd5;
  --h: 13px;
  --t: 14px;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0 auto; padding: 28px 32px 32px; max-width: 1500px;
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 9.5pt; color: var(--text); background: #fff;
}
@page { size: __PAPIER__; margin: 10mm 11mm; }
@media print { body { padding: 0; max-width: none; zoom: __ZOOM__; } }

.kopf {
  display: flex; justify-content: space-between; align-items: flex-end; gap: 24px;
  padding-bottom: 7px; margin-bottom: 14px; border-bottom: 2px solid var(--text);
}
.kopf h1 { margin: 0; font-size: 17pt; line-height: 1.15; font-weight: 700; }
.kopf .unter { margin: 3px 0 0; font-size: 10pt; color: var(--text2); }
.kopf .pfad { margin: 4px 0 0; font: 8pt Consolas, "Cascadia Mono", monospace; color: var(--text3); overflow-wrap: anywhere; }
.kopf .meta { text-align: right; font-size: 8.5pt; line-height: 1.55; color: var(--text2); white-space: nowrap; }
.kopf .meta b { color: var(--text); font-weight: 600; }

.wurzel { display: flex; }
.einzeilig .wurzel { justify-content: center; }
.wurzel-box {
  position: relative; padding: 5px 16px; border-radius: 6px;
  background: var(--text); color: #fff; font-size: 11.5pt; font-weight: 600;
}
.wurzel-box::after { content: ""; position: absolute; top: 100%; height: var(--h); border-left: 1.5px solid var(--linie); }
.einzeilig .wurzel-box::after { left: 50%; }
.mehrzeilig .wurzel-box::after { left: var(--t); }
.leer .wurzel-box::after { display: none; }
.reihen { margin-top: var(--h); }

.reihe {
  position: relative; display: grid; align-items: start;
  grid-template-columns: repeat(var(--spalten), minmax(0, 1fr));
}
.einzeilig .reihe { justify-content: center; grid-template-columns: repeat(var(--spalten), minmax(0, 68mm)); }
.mehrzeilig .reihe { padding-left: calc(2 * var(--t)); padding-bottom: 9px; }
.mehrzeilig .reihe::before { content: ""; position: absolute; left: var(--t); top: 0; bottom: 0; border-left: 1.5px solid var(--linie); }
.mehrzeilig .reihe:last-child { padding-bottom: 0; }
.mehrzeilig .reihe:last-child::before { bottom: auto; height: 1px; }

.ast { position: relative; padding: var(--h) 4px 0; min-width: 0; }
.ast::before, .ast::after {
  content: ""; position: absolute; top: 0; width: 50%; height: var(--h);
  border-top: 1.5px solid var(--linie);
}
.ast::before { left: 0; }
.ast::after { left: 50%; border-left: 1.5px solid var(--linie); }
.ast:first-child::before, .ast:last-child::after { border-top-color: transparent; }
.mehrzeilig .ast:first-child::before { left: calc(-1 * var(--t)); width: calc(50% + var(--t)); border-top-color: var(--linie); }

.karte {
  background: #fff; border: 1px solid var(--rand); border-top: 3px solid var(--farbe, var(--text3));
  border-radius: 5px; overflow-wrap: break-word; -webkit-hyphens: auto; hyphens: auto;
  break-inside: avoid; page-break-inside: avoid;
}
.karte h2 {
  display: flex; flex-wrap: wrap; align-items: baseline; column-gap: 8px;
  margin: 0; padding: 5px 9px; font-size: 10.5pt; line-height: 1.25; font-weight: 600;
  background: color-mix(in srgb, var(--farbe, #888) 9%, #fff);
}
.karte h2:not(:last-child) { border-bottom: 1px solid color-mix(in srgb, var(--farbe, #888) 22%, #fff); }
.anzahl { margin-left: auto; font-size: 7.5pt; font-weight: 400; color: var(--text2); white-space: nowrap; }

.baum, .baum ul { list-style: none; margin: 0; padding: 0; }
.baum { padding: 5px 9px 6px 7px; }
.baum li { position: relative; padding-left: 13px; line-height: 1.32; }
.baum > li { font-size: 9.2pt; color: var(--text); }
.baum ul > li { font-size: 8.6pt; color: var(--text2); }
.baum ul ul > li { font-size: 8.2pt; color: var(--text3); }
.baum > li:has(> ul) > .name { font-weight: 600; }
.baum li::before {
  content: ""; position: absolute; left: 3px; top: 0; width: 7px; height: 0.72em;
  border-left: 1px solid var(--zweig); border-bottom: 1px solid var(--zweig);
}
.baum li:not(:last-child)::after {
  content: ""; position: absolute; left: 3px; top: 0.72em; bottom: 0;
  border-left: 1px solid var(--zweig);
}
/* Tiefe Ebenen weniger einrücken, sonst bricht in schmalen Spalten jedes Wort um */
.baum ul ul ul li { padding-left: 8px; }
.baum ul ul ul li::before { left: 1px; width: 5px; }
.baum ul ul ul li:not(:last-child)::after { left: 1px; }

/* Breite Karten: Unterordner laufen in mehreren Spalten, jeder als eigener Block */
.baum.gruppen { column-gap: 14px; padding-left: 9px; }
.baum.gruppen > li { padding-left: 0; padding-bottom: 4px; break-inside: avoid; page-break-inside: avoid; }
.baum.gruppen > li::before, .baum.gruppen > li::after { display: none; }
.baum.gruppen > li > .name { font-weight: 600; }
.baum.liste { column-gap: 14px; }
.baum.liste > li { break-inside: avoid; page-break-inside: avoid; }

.plus, .muster {
  display: inline-block; margin-left: 5px; padding: 0 4px; border-radius: 3px;
  font-size: 7pt; font-weight: 600; line-height: 1.45; vertical-align: 1px;
  white-space: nowrap; font-style: normal;
}
.plus { background: #edf0f3; color: var(--text2); }
.muster {
  font-weight: 700;
  background: color-mix(in srgb, var(--farbe, #888) 16%, #fff);
  color: color-mix(in srgb, var(--farbe, #888) 72%, #000);
}
.legende {
  margin: 0; padding: 4px 9px 5px; border-top: 1px solid var(--rand);
  font-size: 7.8pt; line-height: 1.35; color: var(--text2);
}
.legende .muster { margin: 0 4px 0 0; }
.am-stueck { white-space: nowrap; }
.info, .fehler { margin-left: 5px; font-size: 7pt; font-weight: 400; white-space: nowrap; }
.info { color: var(--text3); }
.fehler { color: #b42318; }
.mehr { font-style: italic; color: var(--text3); }
.mehr summary { list-style: none; cursor: pointer; }
.mehr summary::-webkit-details-marker { display: none; }
.mehr summary:hover { color: var(--text); text-decoration: underline; }
.mehr ul { font-style: normal; }
.hinweis-leer { margin-top: 14px; text-align: center; font-style: italic; color: var(--text3); }

.fuss {
  margin-top: 10px; padding-top: 5px; border-top: 1px solid var(--rand);
  font-size: 7.3pt; line-height: 1.45; color: var(--text3);
}
.fuss .plus { margin: 0 2px 0 0; }
.fuss.oben { margin: -8px 0 10px; padding-top: 0; border-top: 0; }

/* Sehr große Strukturen: Karten laufen wie Zeitungsspalten über die Seiten */
.fluss .wurzel-box::after { display: none; }
.fluss .reihen { margin-top: 14px; columns: var(--spalten); column-gap: 10px; }
.fluss .ast { padding: 0 0 10px; }
.fluss .ast::before, .fluss .ast::after { display: none; }
.fluss .karte { break-inside: auto; page-break-inside: auto; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.fluss .karte.kurz { break-inside: avoid; page-break-inside: avoid; }
.fluss .karte h2 { break-after: avoid; page-break-after: avoid; }
.fluss .baum li { break-inside: avoid; }
.fluss .baum li:has(> ul) { break-inside: auto; }
"""


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def legende_text(buchstabe: str, cfg) -> str:
    return "jeweils gleicher Aufbau: " + " · ".join(cfg.muster[buchstabe])


def zusatz_html(k: Ordner, cfg) -> str:
    teile = []
    if k.muster:
        teile.append(f'<span class="muster" title="{esc(legende_text(k.muster, cfg))}">{k.muster}</span>')
    if k.tiefer:
        teile.append(f'<span class="plus" title="{k.tiefer} weitere Unterordner">+{k.tiefer}</span>')
    if cfg.dateien and k.dateien:
        teile.append(f'<span class="info">{dateien_text(k.dateien)}</span>')
    if k.verknuepfung:
        teile.append('<span class="info">Verknüpfung</span>')
    if k.fehler:
        teile.append(f'<span class="fehler">{esc(k.fehler)}</span>')
    return "".join(teile)


def eintrag_html(k: Ordner, cfg) -> str:
    return f'<li><span class="name">{esc(k.name)}</span>{zusatz_html(k, cfg)}{liste_html(k, cfg)}</li>'


def liste_html(k: Ordner, cfg, attr: str = "") -> str:
    if k.muster or not (k.kinder or k.versteckt):
        return ""
    teile = [f"<ul{attr}>"]
    teile += [eintrag_html(c, cfg) for c in k.kinder]
    if k.versteckt:
        rest = "".join(eintrag_html(c, cfg) for c in k.versteckt)
        teile.append(
            f'<li class="mehr"><details><summary>+ {weitere(len(k.versteckt))}</summary>'
            f"<ul>{rest}</ul></details></li>"
        )
    teile.append("</ul>")
    return "".join(teile)


def karte_html(k: Ordner, farbe: str, cfg, breite: int = 1, innen: int = 1, kurz: bool = True) -> str:
    if innen > 1:
        art = "gruppen" if any(c.kinder or c.muster for c in k.kinder) else "liste"
        attr = f' class="baum {art}" style="columns:{innen}"'
    else:
        attr = ' class="baum"'
    gesamt = anzahl_ordner(k)
    anzahl = f'<span class="anzahl">{gesamt} Ordner</span>' if gesamt else ""
    legende = "".join(
        f'<p class="legende"><span class="muster">{b}</span>jeweils gleicher Aufbau: '
        + " · ".join(f'<span class="am-stueck">{esc(n)}</span>' for n in cfg.muster[b])
        + "</p>"
        for b in sorted(muster_in(k))
    )
    klasse = "karte kurz" if kurz else "karte"
    stil = f' style="grid-column:span {breite}"' if breite > 1 else ""
    return (
        f'<section class="ast"{stil}><div class="{klasse}" style="--farbe:{farbe}">'
        f'<h2><span><span class="name">{esc(k.name)}</span>{zusatz_html(k, cfg)}</span>{anzahl}</h2>'
        f"{liste_html(k, cfg, attr)}{legende}</div></section>"
    )


def hinweise(baum: Ordner, cfg, als_html: bool) -> list:
    umfang = f"bis zur {cfg.tiefe}. Ebene" if cfg.tiefe else "alle Ebenen"
    zeilen = [f"Gezeigt werden nur Ordner (keine Dateien), {umfang} unterhalb von „{baum.name}“."]
    if irgendwo(baum, lambda k: k.versteckt):
        beispiel = "„+ 73 weitere“" if als_html else "„... und 73 weitere Ordner“"
        text = f"{beispiel} bedeutet: Der Ordner hat mehr Unterordner, als hier aufgelistet sind."
        zeilen.append(text + (" In der HTML-Datei lassen sie sich per Klick aufklappen." if als_html else ""))
    if irgendwo(baum, lambda k: k.tiefer):
        plus = '<span class="plus">+4</span>' if als_html else "„+4 Unterordner“"
        zeilen.append(
            f"{plus} bedeutet: Der Ordner enthält 4 weitere Unterordner, "
            "die hier nicht einzeln aufgeführt sind."
        )
    return zeilen


def html_dokument(baum: Ordner, wurzelpfad: str, titel: str, cfg, heute: dt.date,
                  zoom: float = 1.0, fluss: bool = False) -> str:
    farbe = {id(k): FARBEN[i % len(FARBEN)] for i, k in enumerate(baum.kinder)}
    wurzel_box = f'<div class="wurzel"><div class="wurzel-box">{esc(baum.name)}</div></div>'
    if not baum.kinder:
        chart = (
            f'<main class="chart einzeilig leer">{wurzel_box}'
            '<p class="hinweis-leer">In diesem Ordner gibt es keine Unterordner.</p></main>'
        )
    elif fluss:
        grenze = zeilen_pro_seite(cfg.papier)
        spalte = seite_mm(cfg.papier)[0] / cfg.spalten
        karten = "".join(
            karte_html(k, farbe[id(k)], cfg, kurz=messe_karte(k, spalte, cfg)[0] <= grenze)
            for k in baum.kinder
        )
        chart = (
            f'<main class="chart fluss">{wurzel_box}'
            f'<div class="reihen" style="--spalten:{cfg.spalten}">{karten}</div></main>'
        )
    else:
        plan = plane_karten(baum, cfg, zoom)[0]
        modus = "einzeilig" if len(plan) == 1 else "mehrzeilig"
        reihen_html = "".join(
            f'<div class="reihe" style="--spalten:{sum(s for _, s, _ in r) if modus == "einzeilig" else cfg.spalten}">'
            + "".join(karte_html(k, farbe[id(k)], cfg, s, innen) for k, s, innen in r)
            + "</div>"
            for r in plan
        )
        chart = f'<main class="chart {modus}">{wurzel_box}<div class="reihen">{reihen_html}</div></main>'

    kopf = [f"<h1>{esc(titel)}</h1>"]
    if cfg.untertitel:
        kopf.append(f'<p class="unter">{esc(cfg.untertitel)}</p>')
    if cfg.pfad_anzeigen:
        kopf.append(f'<p class="pfad">{esc(wurzelpfad)}</p>')
    kopf_html = "".join(kopf)

    umfang = f"bis Ebene {cfg.tiefe}" if cfg.tiefe else "gesamt"
    meta = (
        f"Stand <b>{heute:%d.%m.%Y}</b><br>"
        f"{len(baum.kinder)} Hauptordner · {anzahl_ordner(baum)} Ordner {umfang}"
    )
    fuss = "<br>".join(hinweise(baum, cfg, als_html=True))
    # Bei mehrseitigen Dokumenten steht der Hinweis oben, sonst landet er
    # womöglich allein auf einer leeren letzten Seite.
    if fluss:
        oben, unten = f'<footer class="fuss oben">{fuss}</footer>', ""
    else:
        oben, unten = "", f'<footer class="fuss">{fuss}</footer>'
    papier = re.sub(r"[^A-Za-z0-9 .]", "", cfg.papier).strip() or "A4 landscape"
    css = CSS.replace("__PAPIER__", papier).replace("__ZOOM__", f"{zoom:.2f}")
    seitentitel = esc(titel)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{seitentitel}</title>
<style>{css}</style>
</head>
<body>
<header class="kopf"><div>{kopf_html}</div><div class="meta">{meta}</div></header>
{oben}{chart}
{unten}
</body>
</html>
"""


def finde_browser():
    """Sucht Microsoft Edge (oder Chrome), um daraus das PDF zu drucken."""
    eigener = os.environ.get("ORGANIGRAMM_BROWSER")
    if eigener and os.path.isfile(eigener):
        return eigener
    if IST_WINDOWS:
        basen = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        basen = [b for b in basen if b]
        kandidaten = [os.path.join(b, "Microsoft", "Edge", "Application", "msedge.exe") for b in basen]
        kandidaten += [os.path.join(b, "Google", "Chrome", "Application", "chrome.exe") for b in basen]
        for k in kandidaten:
            if os.path.isfile(k):
                return k
    for name in ("msedge", "microsoft-edge", "google-chrome", "chrome", "chromium", "chromium-browser"):
        gefunden = shutil.which(name)
        if gefunden:
            return gefunden
    return None


def erstelle_pdf(html_datei: Path, pdf_datei: Path):
    """Druckt die HTML-Datei mit Edge/Chrome (unsichtbar) als PDF. Liefert (ok, Meldung)."""
    browser = finde_browser()
    if not browser:
        return False, "Microsoft Edge oder Google Chrome wurde nicht gefunden."

    # Eigenes, leeres Profil: so stört ein bereits geöffnetes Edge-Fenster nicht.
    profil = tempfile.mkdtemp(prefix="organigramm_")
    befehl = [
        browser,
        "--headless",
        "--disable-gpu",
        "--disable-sync",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        f"--user-data-dir={profil}",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_datei}",
        Path(os.path.abspath(html_datei)).as_uri(),
    ]
    flags = subprocess.CREATE_NO_WINDOW if IST_WINDOWS else 0
    try:
        subprocess.run(befehl, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=90, creationflags=flags)
    except subprocess.TimeoutExpired:
        return False, "Der Browser hat zu lange gebraucht."
    except OSError as ex:
        return False, f"Der Browser konnte nicht gestartet werden ({ex})."
    finally:
        for _ in range(20):
            if pdf_datei.exists() and pdf_datei.stat().st_size > 0:
                break
            time.sleep(0.25)
        shutil.rmtree(profil, ignore_errors=True)

    if pdf_datei.exists() and pdf_datei.stat().st_size > 0:
        return True, ""
    return False, "Der Browser hat kein PDF erzeugt."


def seitenzahl(pdf_datei: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf_datei.read_bytes()))


def drucke_passend(erzeuge_html, versuche: list, ziel_html: Path, ziel_pdf: Path):
    """Druckt so lange mit kleinerer Schrift, bis das PDF auf eine Seite passt.
    Im kurzen Temp-Pfad, weil der Browser an sehr langen Pfaden scheitert.
    Liefert (ok, Meldung, Seiten, Zoom)."""
    tmp = tempfile.mkdtemp(prefix="organigramm_")
    try:
        probe_html, probe_pdf = Path(tmp) / "o.html", Path(tmp) / "o.pdf"
        for zoom, fluss in versuche:
            text = erzeuge_html(zoom, fluss)
            probe_html.write_text(text, encoding="utf-8")
            if probe_pdf.exists():
                probe_pdf.unlink()
            ok, meldung = erstelle_pdf(probe_html, probe_pdf)
            if not ok:
                return False, meldung, 0, zoom
            seiten = seitenzahl(probe_pdf)
            if seiten <= 1 or fluss:
                break
        ziel_html.write_text(text, encoding="utf-8")
        shutil.copyfile(probe_pdf, ziel_pdf)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True, "", seiten, zoom


# ----------------------------------------------------------------------------
# Textbaum
# ----------------------------------------------------------------------------

def zusatz_text(k: Ordner, cfg) -> str:
    teile = []
    if k.muster:
        teile.append(f"Aufbau {k.muster}")
    if k.tiefer:
        teile.append(f"+{k.tiefer} Unterordner")
    if cfg.dateien and k.dateien:
        teile.append(dateien_text(k.dateien))
    if k.verknuepfung:
        teile.append("Verknüpfung")
    if k.fehler:
        teile.append(k.fehler)
    return f"  ({', '.join(teile)})" if teile else ""


def text_baum(baum: Ordner, wurzelpfad: str, titel: str, cfg, heute: dt.date) -> str:
    z = [titel]
    if cfg.untertitel:
        z.append(cfg.untertitel)
    z.append(f"Stand: {heute:%d.%m.%Y}")
    if cfg.pfad_anzeigen:
        z.append(f"Pfad:  {wurzelpfad}")
    z += ["", baum.name]

    def zweig(k: Ordner, praefix: str, ebene: int):
        if k.muster:
            return
        eintraege = [(kind.name + zusatz_text(kind, cfg), kind) for kind in k.kinder]
        if k.versteckt:
            eintraege.append((f"... und {weitere(len(k.versteckt), 'Ordner')}", None))
        for i, (text, kind) in enumerate(eintraege):
            letzter = i == len(eintraege) - 1
            z.append(praefix + ("└── " if letzter else "├── ") + text)
            if kind is not None:
                zweig(kind, praefix + ("    " if letzter else "│   "), ebene + 1)
            if ebene == 0 and not letzter:
                z.append(praefix + "│")   # Leerzeile zwischen den Hauptordnern

    zweig(baum, "", 0)
    if not baum.kinder:
        z.append("(keine Unterordner)")
    z.append("")
    for buchstabe in sorted(muster_in_baum(baum)):
        z.append(f"Aufbau {buchstabe}: {', '.join(cfg.muster[buchstabe])}")
    z += hinweise(baum, cfg, als_html=False)
    return "\n".join(z) + "\n"


def muster_in_baum(baum: Ordner) -> set:
    gefunden = set()
    for k in baum.kinder:
        gefunden |= muster_in(k)
    return gefunden


# ----------------------------------------------------------------------------
# Ablauf
# ----------------------------------------------------------------------------

def dateiname(text: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "", text).strip()
    return re.sub(r"\s+", "_", s) or "Ordnerstruktur"


def ist_schreibbar(ordner: Path) -> bool:
    try:
        ordner.mkdir(parents=True, exist_ok=True)
        probe = ordner / ".organigramm_probe"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def oeffne(pfad: Path):
    try:
        if IST_WINDOWS:
            os.startfile(str(pfad))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pfad)])
        else:
            subprocess.Popen(["xdg-open", str(pfad)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def desktop_ordner() -> Path:
    """Der echte Desktop, auch wenn er z. B. nach OneDrive umgeleitet ist."""
    if IST_WINDOWS:
        puffer = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(0, 0x10, 0, 0, puffer) == 0 and puffer.value:
            return Path(puffer.value)
    return Path.home() / "Desktop"


def einstellungen(argumente=None):
    p = argparse.ArgumentParser(
        description="Erstellt aus einer Ordnerstruktur ein Organigramm als PDF, HTML und TXT "
                    "(nur Ordner, keine Dateien).",
    )
    p.add_argument("ordner", nargs="?", default=ORDNER, help="Ordner, der dargestellt werden soll")
    p.add_argument("--tiefe", type=int, default=MAX_TIEFE, help=f"Anzahl Ebenen, 0 = alle (Standard: {MAX_TIEFE or 'alle'})")
    p.add_argument("--titel", default=TITEL, help="Überschrift")
    p.add_argument("--untertitel", default=UNTERTITEL, help="Zeile unter der Überschrift")
    p.add_argument("--spalten", type=int, default=MAX_SPALTEN, help=f"Spalten pro Seite (Standard {MAX_SPALTEN})")
    p.add_argument("--max", dest="max_pro_ordner", type=int, default=MAX_PRO_ORDNER,
                   help=f"höchstens so viele Unterordner je Ordner auflisten, 0 = nichts kürzen (Standard {MAX_PRO_ORDNER})")
    p.add_argument("--max-haupt", dest="max_unter_haupt", type=int, default=None,
                   help=f"dasselbe direkt unter den Hauptordnern (Standard {MAX_UNTER_HAUPTORDNER})")
    p.add_argument("--nicht-zusammenfassen", dest="zusammenfassen", action="store_false",
                   default=GLEICHE_ZUSAMMENFASSEN, help="gleich aufgebaute Ordner einzeln auflisten")
    p.add_argument("--dateien", action="store_true", default=DATEIEN_ZAEHLEN, help="Anzahl Dateien je Ordner anzeigen")
    p.add_argument("--ohne-pfad", dest="pfad_anzeigen", action="store_false", default=PFAD_ANZEIGEN,
                   help="Pfad nicht im Dokument anzeigen")
    p.add_argument("--papier", default=PAPIER, help='z. B. "A4 landscape", "A4 portrait", "A3 landscape"')
    p.add_argument("--ausgabe", default=AUSGABE_ORDNER, help="Ordner für die Ergebnisse")
    p.add_argument("--kein-pdf", dest="pdf", action="store_false", default=PDF_ERSTELLEN, help="kein PDF erzeugen")
    p.add_argument("--nicht-oeffnen", dest="oeffnen", action="store_false", default=PDF_OEFFNEN,
                   help="Ergebnis am Ende nicht automatisch öffnen")
    cfg = p.parse_args(argumente)
    cfg.ignorieren = IGNORIEREN
    cfg.versteckte_ignorieren = VERSTECKTE_IGNORIEREN
    cfg.tiefe = max(0, cfg.tiefe)
    cfg.spalten = max(1, cfg.spalten)
    cfg.max_pro_ordner = max(0, cfg.max_pro_ordner)
    if cfg.max_unter_haupt is None:
        # --max 0 heißt: wirklich gar nichts kürzen
        cfg.max_unter_haupt = MAX_UNTER_HAUPTORDNER if cfg.max_pro_ordner else 0
    cfg.max_unter_haupt = max(0, cfg.max_unter_haupt)
    cfg.muster = {}
    return cfg


class OrganigrammFehler(Exception):
    """Ein Problem, das sich dem Anwender verständlich erklären lässt."""


@dataclass
class Ergebnis:
    ausgabe: Path
    html_datei: Path
    txt_datei: Path
    pdf_datei: Path = None     # None, wenn kein PDF entstanden ist
    pdf_meldung: str = ""
    seiten: int = 0
    zoom: float = 1.0
    gesamt: int = 0
    aufgefuehrt: int = 0


def erstelle(cfg, melde=print) -> Ergebnis:
    """Liest den Ordner und schreibt PDF, HTML und TXT. Fortschritt geht an melde()."""
    # In CMD wird aus "D:\Ordner\" ein D:\Ordner" - das Anführungszeichen entfernen
    roh = cfg.ordner.strip().strip('"').strip()
    if not roh:
        # Ohne diese Prüfung würde abspath() den aktuellen Ordner nehmen
        raise OrganigrammFehler(
            "Es ist kein Ordner angegeben.\n\n"
            "Bitte oben im Skript bei ORDNER eintragen oder beim Start angeben:\n"
            '  py ordner_organigramm_v2.py "D:\\Ordner"'
        )
    wurzel = os.path.abspath(os.path.expandvars(os.path.expanduser(roh)))
    if not os.path.isdir(wurzel):
        raise OrganigrammFehler(
            f"Ordner nicht gefunden:\n  {wurzel}\n\n"
            "Bitte prüfen:\n"
            "  - Ist der Pfad richtig geschrieben?\n"
            "  - Ist das Netzlaufwerk verbunden (im Explorer erreichbar)?\n"
            "  - Läuft das Programm als Administrator? Dann sind Netzlaufwerke oft unsichtbar."
        )

    name = os.path.basename(wurzel.rstrip("\\/")) or wurzel
    titel = cfg.titel.strip() or f"Ordnerstruktur {name}"

    umfang = f"bis Ebene {cfg.tiefe}" if cfg.tiefe else "alle Ebenen"
    melde(f"Lese Ordnerstruktur ({umfang}):\n  {wurzel}")
    start = time.time()
    leser = Leser(cfg, melde)
    baum = leser.lies(wurzel, name)
    if baum.fehler:
        raise OrganigrammFehler(f"Der Ordner kann nicht gelesen werden ({baum.fehler}):\n  {wurzel}")
    gesamt = anzahl_ordner(baum)
    if cfg.zusammenfassen:
        cfg.muster = finde_muster(baum)
    kuerzen(baum, cfg)
    melde(f"  {len(baum.kinder)} Hauptordner, {gesamt} Ordner gelesen ({time.time() - start:.1f} s), "
          f"{aufgefuehrt(baum)} davon einzeln aufgeführt")

    ausgabe = Path(os.path.abspath(cfg.ausgabe)) if cfg.ausgabe else Path(os.path.dirname(os.path.abspath(__file__)))
    if not ist_schreibbar(ausgabe):
        ersatz = desktop_ordner()
        ausgabe = ersatz if ist_schreibbar(ersatz) else Path.home()
        melde(f"  Hinweis: Im Zielordner darf nicht geschrieben werden, nehme stattdessen {ausgabe}")

    heute = dt.date.today()
    basis = f"{dateiname(titel)}_{heute:%Y-%m-%d}"
    html_datei = ausgabe / f"{basis}.html"
    txt_datei = ausgabe / f"{basis}.txt"
    pdf_datei = ausgabe / f"{basis}.pdf"

    hoehe = plane_karten(baum, cfg)[1] if baum.kinder else 0
    seite = zeilen_pro_seite(cfg.papier)

    def erzeuge_html(zoom: float, fluss: bool) -> str:
        return html_dokument(baum, wurzel, titel, cfg, heute, zoom, fluss)

    # Viel zu groß für eine Seite (z. B. mit --max 0)? Dann gleich über mehrere Seiten
    versuche = [] if hoehe > 2.5 * seite else [(z, False) for z in ZOOM_STUFEN]
    versuche.append((1.0, True))
    # Ohne PDF zählt die Schätzung: So passt auch der Ausdruck aus dem Browser
    geschaetzt = max(min(ZOOM_STUFEN), min(1.0, seite / max(hoehe, 1)))
    html_datei.write_text(erzeuge_html(geschaetzt, hoehe > 2.5 * seite), encoding="utf-8")
    txt_datei.write_text(text_baum(baum, wurzel, titel, cfg, heute), encoding="utf-8-sig")

    pdf_ok, meldung, seiten, zoom = False, "", 0, 1.0
    if cfg.pdf:
        if pdf_datei.exists():
            try:
                pdf_datei.unlink()
            except OSError:   # z. B. noch im PDF-Viewer geöffnet
                pdf_datei = ausgabe / f"{basis}_{dt.datetime.now():%H%M%S}.pdf"
        melde("Erstelle PDF ...")
        pdf_ok, meldung, seiten, zoom = drucke_passend(erzeuge_html, versuche, html_datei, pdf_datei)

    return Ergebnis(ausgabe, html_datei, txt_datei, pdf_datei if pdf_ok else None, meldung,
                    seiten, zoom, gesamt, aufgefuehrt(baum))


def seiten_text(e: Ergebnis) -> str:
    groesse = f", Schrift auf {e.zoom:.0%} verkleinert" if e.zoom < 1 else ""
    return ("1 Seite" if e.seiten <= 1 else f"{e.seiten} Seiten") + groesse


def main() -> int:
    cfg = einstellungen()
    try:
        e = erstelle(cfg)
    except OrganigrammFehler as fehler:
        print(f"\n{fehler}")
        return 1

    print(f"\nFertig. Gespeichert in:\n  {e.ausgabe}\n")
    if e.pdf_datei:
        print(f"  {e.pdf_datei.name}   -> zum Verschicken an die Mail anhängen ({seiten_text(e)})")
    print(f"  {e.html_datei.name}  -> öffnet im Browser, gekürzte Ordner lassen sich aufklappen")
    print(f"  {e.txt_datei.name}   -> Text kann direkt in eine Mail kopiert werden")
    if cfg.pdf and not e.pdf_datei:
        print(f"\nPDF konnte nicht automatisch erstellt werden: {e.pdf_meldung}")
        print("So geht es von Hand: HTML-Datei öffnen, Strg+P drücken, 'Als PDF speichern' wählen.")

    if cfg.oeffnen:
        oeffne(e.pdf_datei or e.html_datei)
    return 0


if __name__ == "__main__":
    per_doppelklick = len(sys.argv) == 1
    try:
        code = main()
    except KeyboardInterrupt:
        code = 1
    except Exception as fehler:  # damit das Fenster bei Doppelklick nicht einfach verschwindet
        import traceback
        traceback.print_exc()
        print(f"\nFEHLER: {fehler}")
        code = 1
    if per_doppelklick and IST_WINDOWS:
        try:
            input("\nEnter drücken zum Schließen ...")
        except EOFError:
            pass
    sys.exit(code)
