# Ordner-Organigramm

Macht aus einer Ordnerstruktur eine Übersicht zum Verschicken: als PDF, als HTML-Datei und als Text. Gezeigt werden nur Ordner, keine Dateien. Der dargestellte Ordner wird nur gelesen und nicht verändert.

Damit auch große Strukturen lesbar bleiben:

- Ordner mit vielen Unterordnern werden gekürzt („+ 72 weitere“). In der HTML-Datei lässt sich der Rest aufklappen.
- Immer gleich aufgebaute Ordner werden zusammengefasst. Statt 25-mal dieselben Unterordner steht dort ein Buchstabe, der Aufbau einmal darunter.
- Große Hauptordner werden breiter und nutzen mehrere Spalten.
- Das PDF wird wenn möglich auf eine Seite eingepasst.

## Download

Auf der [aktuellen GitHub-Release-Seite](https://github.com/zerox80/organigramm_python/releases/latest) die Datei mit der Endung `-Setup.exe` herunterladen und öffnen. Der Assistent installiert das Programm für dein Windows-Konto unter `%LOCALAPPDATA%\Programs\Ordner-Organigramm`. Die Installation braucht keine Administratorrechte und kein Python. Danach findest du **Ordner-Organigramm** im Startmenü.

Das PDF wird über Microsoft Edge oder Google Chrome erzeugt. Ohne einen der beiden Browser bleiben die HTML- und die Textdatei.

Der Installer ist unsigniert. Windows SmartScreen kann deshalb einen Hinweis anzeigen.

## Benutzung

Im Fenster Ordner und Tiefe wählen und auf **Erstellen** klicken. Die Ergebnisse landen auf dem Desktop, außer es wird etwas anderes gewählt.

Ohne Fenster, zum Beispiel als geplante Aufgabe:

```bat
Organigramm.exe --ohne-fenster "D:\Ordner" --ausgabe "D:\Zielordner" --tiefe 4
```

Exit-Code: `0` = alles erstellt, `1` = Ordner oder Ziel nicht nutzbar, `2` = falsche Option, `3` = ohne PDF.

### Ordnerstruktur im Web veröffentlichen

Wähle **Ordner** und **Tiefe** wie gewohnt. Öffne **Web veröffentlichen …** und gib die HTTPS-Adresse der Ablage und den Veröffentlichungsschlüssel ein. Die Adresse kann einen Port und einen Pfad wie `/ablage/` enthalten. Nach erfolgreichem Upload öffnet sich die Website. Das Programm merkt sich die Adresse. Mit **Schlüssel auf diesem Rechner merken** speichert es auch den Schlüssel pro Serveradresse in der Windows-Anmeldeinformationsverwaltung. Entferne den Haken und veröffentliche einmal erfolgreich, um den gespeicherten Schlüssel für diese Adresse zu löschen.

Die Webablage muss Veröffentlichungen unterstützen. Adresse und Schlüssel bekommst du von der Person, die sie betreibt. **Erstellen** speichert weiterhin die PDF-, HTML- und Textdateien.

## Aus dem Quelltext starten

Es werden keine Zusatzpakete gebraucht. Entwickelt und getestet mit Python 3.14.

```bat
py organigramm_gui.py
py ordner_organigramm_v2.py "D:\Ordner" --tiefe 3
py ordner_organigramm_v2.py -h
```

## Windows-Installer bauen und veröffentlichen

1. Mit Python 3.14 für Windows x64 im Repository `bauen.bat` ausführen. PyInstaller erzeugt den Programmordner `dist\Ordner-Organigramm`.
2. In [Inno Setup 6.6 oder neuer](https://jrsoftware.org/inno-setup/downloads) die Datei `installer\Ordner-Organigramm.iss` öffnen und **Build → Compile** wählen. Das Setup landet in `dist\` und übernimmt die Versionsnummer aus dem Programm.
3. Für eine neue GitHub-Version die Versionsangaben in `version_info.txt` aktualisieren und den Commit pushen. Einen passenden Tag wie `v1.2.1` anlegen und mit `git push origin v1.2.1` hochladen. Der [Release-Workflow](https://github.com/zerox80/organigramm_python/actions) baut und testet den Installer und hängt ihn an das neue Release.

## Lizenz

[MIT](LICENSE)
