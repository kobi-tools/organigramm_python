#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ordner-Organigramm mit Fenster
==============================

Ordner auswählen, Tiefe wählen, auf "Erstellen" klicken. Die eigentliche Arbeit
macht ordner_organigramm_v2.py, dieses Fenster sammelt nur die Einstellungen ein.
Zum Verteilen als .exe: bauen.bat
"""

from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, font, messagebox, ttk

import ordner_organigramm_v2 as kern
import web_veroeffentlichen as web

TITEL = "Ordner-Organigramm"
QUELLCODE_URL = "https://github.com/zerox80/organigramm_python"

# Anzeige -> (Papierformat, Spalten)
PAPIERE = {
    "A4 quer": ("A4 landscape", 6),
    "A4 hoch": ("A4 portrait", 4),
    "A3 quer": ("A3 landscape", 6),
}

TIEFEN = {
    "1 Ebene": 1,
    "2 Ebenen": 2,
    "3 Ebenen": 3,
    "4 Ebenen": 4,
    "5 Ebenen": 5,
    "6 Ebenen": 6,
    "Alle Ebenen": 0,
}


def ressource(name: str) -> str:
    """Pfad zu einer mitgelieferten Datei, im Skript wie in der .exe."""
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), name)


def tiefe_text(tiefe: int) -> str:
    return next((text for text, wert in TIEFEN.items() if wert == tiefe), "4 Ebenen")


class Fenster(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITEL)
        self.resizable(True, False)
        self.minsize(560, 0)
        try:
            self.iconbitmap(ressource("organigramm.ico"))
        except tk.TclError:
            pass

        stil = ttk.Style(self)
        if "vista" in stil.theme_names():
            stil.theme_use("vista")
        font.nametofont("TkDefaultFont").configure(size=10)
        font.nametofont("TkTextFont").configure(size=10)
        stil.configure("Ueberschrift.TLabel", font=("Segoe UI Semibold", 15))
        stil.configure("Hinweis.TLabel", foreground="#5b6b7c")
        stil.configure("Link.TLabel", foreground="#2f6fdb", font=("Segoe UI", 9, "underline"))
        stil.configure("Haupt.TButton", font=("Segoe UI Semibold", 10), padding=(18, 6))

        self.nachrichten = queue.Queue()
        self.laeuft = False
        self.ergebnis = None

        self.ordner = tk.StringVar(value=kern.ORDNER)
        self.tiefe = tk.StringVar(value=tiefe_text(kern.MAX_TIEFE))
        self.ziel = tk.StringVar(value=str(kern.desktop_ordner()))
        self.erweitert = tk.BooleanVar(value=False)
        self.ueberschrift = tk.StringVar(value=kern.TITEL)
        self.untertitel = tk.StringVar(value=kern.UNTERTITEL)
        self.papier = tk.StringVar(value="A4 quer")
        self.max_ordner = tk.StringVar(value=str(kern.MAX_PRO_ORDNER))
        self.max_haupt = tk.StringVar(value=str(kern.MAX_UNTER_HAUPTORDNER))
        self.alles = tk.BooleanVar(value=False)
        self.zusammenfassen = tk.BooleanVar(value=kern.GLEICHE_ZUSAMMENFASSEN)
        self.dateien = tk.BooleanVar(value=kern.DATEIEN_ZAEHLEN)
        self.pfad = tk.BooleanVar(value=kern.PFAD_ANZEIGEN)
        self.status = tk.StringVar(value="Bereit.")

        self.baue_oberflaeche()
        self.protocol("WM_DELETE_WINDOW", self.schliessen)
        self.bind("<Return>", lambda _: self.starten())

    # ------------------------------------------------------------------------
    # Oberfläche
    # ------------------------------------------------------------------------

    def baue_oberflaeche(self):
        rahmen = ttk.Frame(self, padding=(18, 14, 18, 14))
        rahmen.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        rahmen.columnconfigure(1, weight=1)

        ttk.Label(rahmen, text=TITEL, style="Ueberschrift.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(
            rahmen, style="Hinweis.TLabel",
            text="Erstellt aus einem Ordner eine Übersicht zum Verschicken. Der Ordner selbst wird nicht verändert.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 12))

        self.zeile_pfad(rahmen, 2, "Ordner:", self.ordner, "Welcher Ordner soll dargestellt werden?")

        ttk.Label(rahmen, text="Tiefe:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(
            rahmen, textvariable=self.tiefe, values=list(TIEFEN), state="readonly", width=14,
        ).grid(row=3, column=1, sticky="w", padx=(8, 8), pady=4)

        self.zeile_pfad(rahmen, 4, "Speichern in:", self.ziel, "Wohin sollen die Ergebnisse?")

        ttk.Checkbutton(
            rahmen, text="Erweiterte Einstellungen", variable=self.erweitert, command=self.erweitert_umschalten,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 2))

        self.bereich_erweitert = self.baue_erweitert(rahmen)
        self.bereich_erweitert.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(2, 4))
        self.bereich_erweitert.grid_remove()

        ttk.Separator(rahmen).grid(row=7, column=0, columnspan=3, sticky="ew", pady=(10, 10))

        self.balken = ttk.Progressbar(rahmen, mode="determinate", maximum=100)
        self.balken.grid(row=8, column=0, columnspan=3, sticky="ew")
        self.statuszeile = ttk.Label(rahmen, textvariable=self.status, wraplength=620, justify="left")
        self.statuszeile.grid(row=9, column=0, columnspan=3, sticky="w", pady=(6, 10))
        rahmen.bind("<Configure>", lambda e: self.statuszeile.configure(wraplength=max(e.width - 40, 300)))

        aktionen = ttk.Frame(rahmen)
        aktionen.grid(row=10, column=0, columnspan=3, sticky="ew")
        aktionen.columnconfigure(0, weight=1)
        self.knopf_web = ttk.Button(aktionen, text="Web veröffentlichen …", command=self.web_starten)
        self.knopf_web.grid(row=0, column=0, sticky="w", padx=(0, 12))
        knoepfe = ttk.Frame(aktionen)
        knoepfe.grid(row=0, column=1, sticky="e")
        self.knopf_ergebnis = ttk.Button(knoepfe, text="Ergebnis öffnen", command=self.ergebnis_oeffnen, state="disabled")
        self.knopf_ergebnis.grid(row=0, column=0, padx=(0, 6))
        self.knopf_ziel = ttk.Button(knoepfe, text="Speicherort öffnen", command=self.ziel_oeffnen, state="disabled")
        self.knopf_ziel.grid(row=0, column=1, padx=(0, 12))
        self.knopf_start = ttk.Button(knoepfe, text="Erstellen", style="Haupt.TButton", command=self.starten)
        self.knopf_start.grid(row=0, column=2)
        self.knopf_start.focus_set()

        link = ttk.Label(rahmen, text="Quellcode: Github", style="Link.TLabel", cursor="hand2")
        link.grid(row=11, column=0, columnspan=3, sticky="sw", pady=(8, 0))
        link.bind("<Button-1>", lambda _: self.quellcode_oeffnen())

    def zeile_pfad(self, eltern, zeile: int, text: str, variable: tk.StringVar, frage: str):
        ttk.Label(eltern, text=text).grid(row=zeile, column=0, sticky="w", pady=4)
        ttk.Entry(eltern, textvariable=variable, width=62).grid(row=zeile, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(
            eltern, text="Auswählen ...", command=lambda: self.ordner_waehlen(variable, frage),
        ).grid(row=zeile, column=2, pady=4)

    def baue_erweitert(self, eltern) -> ttk.Frame:
        f = ttk.LabelFrame(eltern, padding=(10, 6, 10, 8))
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="Überschrift:").grid(row=0, column=0, sticky="w", pady=(3, 0))
        ttk.Entry(f, textvariable=self.ueberschrift).grid(row=0, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=(3, 0))
        ttk.Label(f, text="Leer lassen = „Ordnerstruktur <Ordnername>“", style="Hinweis.TLabel").grid(
            row=1, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(0, 3))
        ttk.Label(f, text="Untertitel:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(f, textvariable=self.untertitel).grid(row=2, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(f, text="Papierformat:").grid(row=3, column=0, sticky="w", pady=(8, 3))
        ttk.Combobox(f, textvariable=self.papier, values=list(PAPIERE), state="readonly", width=10).grid(
            row=3, column=1, sticky="w", padx=(8, 0), pady=(8, 3))

        ttk.Label(f, text="Unterordner je Ordner:").grid(row=4, column=0, sticky="w", pady=3)
        self.feld_ordner = ttk.Spinbox(f, from_=1, to=200, textvariable=self.max_ordner, width=6)
        self.feld_ordner.grid(row=4, column=1, sticky="w", padx=(8, 0), pady=3)
        ttk.Label(f, text="Direkt unter Hauptordnern:").grid(row=5, column=0, sticky="w", pady=3)
        self.feld_haupt = ttk.Spinbox(f, from_=1, to=200, textvariable=self.max_haupt, width=6)
        self.feld_haupt.grid(row=5, column=1, sticky="w", padx=(8, 0), pady=3)

        ttk.Checkbutton(
            f, text="Nichts kürzen, alle Ordner auflisten (wird schnell mehrseitig)",
            variable=self.alles, command=self.grenzen_umschalten,
        ).grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 1))
        ttk.Checkbutton(f, text="Gleich aufgebaute Ordner zusammenfassen", variable=self.zusammenfassen).grid(
            row=7, column=0, columnspan=4, sticky="w", pady=1)
        ttk.Checkbutton(f, text="Anzahl Dateien je Ordner anzeigen", variable=self.dateien).grid(
            row=8, column=0, columnspan=4, sticky="w", pady=1)
        ttk.Checkbutton(f, text="Pfad oben im Dokument anzeigen", variable=self.pfad).grid(
            row=9, column=0, columnspan=4, sticky="w", pady=1)
        return f

    def erweitert_umschalten(self):
        if self.erweitert.get():
            self.bereich_erweitert.grid()
        else:
            self.bereich_erweitert.grid_remove()
        # Hat jemand das Fenster schon breiter gezogen, passt Tk die Höhe nicht mehr selbst an
        self.update_idletasks()
        self.geometry(f"{self.winfo_width()}x{self.winfo_reqheight()}")

    def grenzen_umschalten(self):
        zustand = "disabled" if self.alles.get() else "normal"
        self.feld_ordner.configure(state=zustand)
        self.feld_haupt.configure(state=zustand)

    def ordner_waehlen(self, variable: tk.StringVar, frage: str):
        start = variable.get().strip()
        gewaehlt = filedialog.askdirectory(
            parent=self, title=frage, mustexist=True, initialdir=start if os.path.isdir(start) else None,
        )
        if gewaehlt:
            variable.set(os.path.normpath(gewaehlt))

    # ------------------------------------------------------------------------
    # Ablauf
    # ------------------------------------------------------------------------

    def argumente(self):
        """Baut aus den Eingaben die Argumente für den Kern. None bei falschen Eingaben."""
        ordner = self.ordner.get().strip().strip('"').strip()
        ziel = self.ziel.get().strip().strip('"').strip()
        if not ordner:
            messagebox.showinfo(TITEL, "Bitte zuerst einen Ordner auswählen.", parent=self)
            return None
        if not ziel:
            messagebox.showinfo(TITEL, "Bitte auswählen, wo die Ergebnisse gespeichert werden sollen.", parent=self)
            return None

        if self.alles.get():
            max_ordner, max_haupt = 0, 0
        else:
            try:
                max_ordner, max_haupt = int(self.max_ordner.get()), int(self.max_haupt.get())
                if max_ordner < 1 or max_haupt < 1:
                    raise ValueError
            except ValueError:
                messagebox.showinfo(
                    TITEL, "Bei den erweiterten Einstellungen bitte ganze Zahlen ab 1 eintragen.", parent=self,
                )
                return None

        papier, spalten = PAPIERE[self.papier.get()]
        teile = [
            f"--tiefe={TIEFEN[self.tiefe.get()]}",
            f"--spalten={spalten}",
            f"--papier={papier}",
            f"--max={max_ordner}",
            f"--max-haupt={max_haupt}",
            f"--ausgabe={ziel}",
            f"--titel={self.ueberschrift.get()}",
            f"--untertitel={self.untertitel.get()}",
            "--nicht-oeffnen",
        ]
        if not self.zusammenfassen.get():
            teile.append("--nicht-zusammenfassen")
        if self.dateien.get():
            teile.append("--dateien")
        if not self.pfad.get():
            teile.append("--ohne-pfad")
        return teile + ["--", ordner]

    def starten(self):
        if self.laeuft:
            return
        teile = self.argumente()
        if teile is None:
            return
        self.ergebnis = None
        self.knopf_ergebnis.configure(state="disabled")
        self.knopf_ziel.configure(state="disabled")
        self.arbeit_beginnen()
        self.status.set("Lese Ordnerstruktur ...")
        threading.Thread(target=self.arbeiten, args=(teile,), daemon=True).start()
        self.after(100, self.nachrichten_holen)

    def arbeit_beginnen(self):
        self.laeuft = True
        self.knopf_start.configure(state="disabled")
        self.knopf_web.configure(state="disabled")
        self.balken.configure(mode="indeterminate", value=0)
        self.balken.start(12)

    def web_starten(self):
        if self.laeuft:
            return
        ordner = self.ordner.get().strip().strip('"').strip()
        if not ordner:
            messagebox.showinfo(TITEL, "Bitte zuerst einen Ordner auswählen.", parent=self)
            return
        tiefe_text = self.tiefe.get()
        dialog = tk.Toplevel(self)
        dialog.title("Web veröffentlichen")
        dialog.transient(self)
        dialog.resizable(True, False)
        dialog.columnconfigure(0, weight=1)
        dialog.grab_set()
        rahmen = ttk.Frame(dialog, padding=18)
        rahmen.grid(sticky="nsew")
        rahmen.columnconfigure(0, weight=1)
        ziel = tk.StringVar(master=dialog, value=web.gespeichertes_ziel())
        schluessel = tk.StringVar(master=dialog)
        ttk.Label(rahmen, text=f"{ordner} · {tiefe_text}", wraplength=420).grid(row=0, column=0, sticky="w")
        ttk.Label(rahmen, text="Adresse der Ablage").grid(row=1, column=0, sticky="w", pady=(12, 2))
        adresse = ttk.Entry(rahmen, textvariable=ziel, width=50)
        adresse.grid(row=2, column=0, sticky="ew")
        ttk.Label(rahmen, text="Veröffentlichungsschlüssel").grid(row=3, column=0, sticky="w", pady=(12, 2))
        passwort = ttk.Entry(rahmen, textvariable=schluessel, show="•")
        passwort.grid(row=4, column=0, sticky="ew")
        aktionen = ttk.Frame(rahmen)
        aktionen.grid(row=5, column=0, sticky="e", pady=(14, 0))

        def senden(_event=None):
            try:
                server = web.server_adresse(ziel.get())
                schluessel_text = schluessel.get().strip()
                if not schluessel_text:
                    raise ValueError("Bitte den Veröffentlichungsschlüssel eingeben.")
            except ValueError as fehler:
                messagebox.showinfo(dialog.title(), str(fehler), parent=dialog)
                return "break"
            dialog.destroy()
            self.arbeit_beginnen()
            self.status.set("Lese den Ordnerbaum für die Website …")
            threading.Thread(
                target=self.web_arbeiten, args=(ordner, TIEFEN[tiefe_text], server, schluessel_text), daemon=True,
            ).start()
            self.after(100, self.nachrichten_holen)
            return "break"

        ttk.Button(aktionen, text="Abbrechen", command=dialog.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(aktionen, text="Veröffentlichen", style="Haupt.TButton", command=senden).grid(row=0, column=1)
        dialog.bind("<Return>", senden)
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        (passwort if ziel.get() else adresse).focus_set()

    def web_arbeiten(self, ordner, tiefe, server, schluessel):
        try:
            struktur = kern.struktur_lesen(ordner, tiefe)
            self.nachrichten.put(("status", "Übertrage Ordnerbaum an die Website …"))
            self.nachrichten.put(("web_fertig", web.veroeffentliche(server, schluessel, struktur)))
        except (OSError, ValueError, RecursionError) as fehler:
            self.nachrichten.put(("web_fehler", str(fehler)))

    def arbeiten(self, teile: list):
        """Läuft im Hintergrund, damit das Fenster bedienbar bleibt."""
        def melde(text: str):
            self.nachrichten.put(("status", " ".join(text.split())))

        try:
            cfg = kern.einstellungen(teile)
            self.nachrichten.put(("fertig", kern.erstelle(cfg, melde)))
        except kern.OrganigrammFehler as fehler:
            self.nachrichten.put(("fehler", str(fehler)))
        except OSError as fehler:
            self.nachrichten.put(("fehler", f"Die Ergebnisse konnten nicht gespeichert werden:\n{fehler}"))
        except (Exception, SystemExit) as fehler:
            self.nachrichten.put(("fehler", f"Unerwarteter Fehler:\n{fehler}"))

    def nachrichten_holen(self):
        try:
            while True:
                art, inhalt = self.nachrichten.get_nowait()
                if art == "status":
                    self.status.set(inhalt)
                elif art == "fertig":
                    self.fertig(inhalt)
                    return
                elif art == "web_fertig":
                    self.arbeit_beendet(True)
                    self.status.set("Ordnerstruktur veröffentlicht.")
                    webbrowser.open(inhalt)
                    return
                elif art == "web_fehler":
                    self.gescheitert(inhalt, "Veröffentlichen fehlgeschlagen.")
                    return
                else:
                    self.gescheitert(inhalt)
                    return
        except queue.Empty:
            pass
        self.after(100, self.nachrichten_holen)

    def arbeit_beendet(self, geklappt: bool):
        self.laeuft = False
        self.balken.stop()
        self.balken.configure(mode="determinate", value=100 if geklappt else 0)
        self.knopf_start.configure(state="normal")
        self.knopf_web.configure(state="normal")

    def fertig(self, e: kern.Ergebnis):
        self.arbeit_beendet(True)
        self.ergebnis = e
        self.knopf_ergebnis.configure(state="normal")
        self.knopf_ziel.configure(state="normal")
        umfang = f"{e.gesamt} Ordner gelesen, {e.aufgefuehrt} davon einzeln aufgeführt"
        ort = f"Gespeichert in: {e.ausgabe}"
        if e.pdf_datei:
            self.status.set(f"Fertig: {e.pdf_datei.name} ({kern.seiten_text(e)}). {umfang}.\n{ort}")
            kern.oeffne(e.pdf_datei)
        else:
            self.status.set(f"Fertig, aber ohne PDF: {e.html_datei.name}. {umfang}.\n{ort}")
            messagebox.showwarning(
                TITEL,
                f"Das PDF konnte nicht erstellt werden: {e.pdf_meldung}\n\n"
                "Die HTML-Datei wird jetzt geöffnet. Daraus geht es von Hand:\n"
                "Strg+P drücken und „Als PDF speichern“ wählen.",
                parent=self,
            )
            kern.oeffne(e.html_datei)

    def gescheitert(self, text: str, status="Nicht erstellt."):
        self.arbeit_beendet(False)
        self.status.set(status)
        messagebox.showerror(TITEL, text, parent=self)

    def ergebnis_oeffnen(self):
        if self.ergebnis:
            kern.oeffne(self.ergebnis.pdf_datei or self.ergebnis.html_datei)

    def ziel_oeffnen(self):
        if self.ergebnis:
            kern.oeffne(self.ergebnis.ausgabe)

    def quellcode_oeffnen(self):
        webbrowser.open(QUELLCODE_URL)

    def schliessen(self):
        if self.laeuft and not messagebox.askyesno(
            TITEL, "Die Verarbeitung läuft noch. Trotzdem schließen?", parent=self,
        ):
            return
        self.destroy()


def ohne_fenster(teile: list) -> int:
    """Für geplante Aufgaben: Organigramm.exe --ohne-fenster "D:\\Ordner" --ausgabe "D:\\Ziel"
    Exit-Code: 0 = alles erstellt, 1 = Ordner oder Ziel nicht nutzbar, 3 = ohne PDF."""
    cfg = kern.einstellungen(teile)
    cfg.ausgabe = cfg.ausgabe or str(kern.desktop_ordner())
    try:
        e = kern.erstelle(cfg, melde=lambda _: None)
    except (kern.OrganigrammFehler, OSError):
        return 1
    return 0 if e.pdf_datei or not cfg.pdf else 3


def main() -> int:
    if "--ohne-fenster" in sys.argv[1:]:
        return ohne_fenster([a for a in sys.argv[1:] if a != "--ohne-fenster"])
    if kern.IST_WINDOWS:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)   # sonst wirkt das Fenster verschwommen
        except (AttributeError, OSError):
            pass
    Fenster().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
