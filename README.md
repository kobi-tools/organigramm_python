# Ordner-Organigramm

Macht aus einer Ordnerstruktur eine Übersicht zum Verschicken: als PDF, als HTML-Datei und als Text. Gezeigt werden nur Ordner, keine Dateien. Der dargestellte Ordner wird nur gelesen und nicht verändert.

Damit auch große Strukturen lesbar bleiben:

- Ordner mit vielen Unterordnern werden gekürzt („+ 72 weitere“). In der HTML-Datei lässt sich der Rest aufklappen.
- Immer gleich aufgebaute Ordner werden zusammengefasst. Statt 25-mal dieselben Unterordner steht dort ein Buchstabe, der Aufbau einmal darunter.
- Große Hauptordner werden breiter und nutzen mehrere Spalten.
- Das PDF wird wenn möglich auf eine Seite eingepasst.

## Download

Unter [Releases](https://github.com/zerox80/organigramm_python/releases) die ZIP-Datei herunterladen, entpacken und `Organigramm.exe` starten. Python muss nicht installiert sein. Getestet unter Windows 11.

Das PDF wird über Microsoft Edge oder Google Chrome erzeugt. Ohne einen der beiden Browser bleiben die HTML- und die Textdatei.

Die `.exe` ist nicht signiert, Windows SmartScreen oder ein Virenscanner können deshalb warnen.

## Benutzung

Im Fenster Ordner und Tiefe wählen und auf **Erstellen** klicken. Die Ergebnisse landen auf dem Desktop, außer es wird etwas anderes gewählt.

Ohne Fenster, zum Beispiel als geplante Aufgabe:

```bat
Organigramm.exe --ohne-fenster "D:\Ordner" --ausgabe "D:\Zielordner" --tiefe 4
```

Exit-Code: `0` = alles erstellt, `1` = Ordner oder Ziel nicht nutzbar, `2` = falsche Option, `3` = ohne PDF.

### Ordnerstruktur im Web veröffentlichen

Wähle **Ordner** und **Tiefe** wie gewohnt. Öffne **Web veröffentlichen …** und gib die HTTPS-Adresse der Ablage und den Veröffentlichungsschlüssel ein. Die Adresse kann einen Port und einen Pfad wie `/ablage/` enthalten. Nach erfolgreichem Upload öffnet sich die Website. Das Programm merkt sich die Adresse und fragt den Schlüssel beim nächsten Veröffentlichen erneut ab.

Die Webablage muss Veröffentlichungen unterstützen. Adresse und Schlüssel bekommst du von der Person, die sie betreibt. **Erstellen** speichert weiterhin die PDF-, HTML- und Textdateien.

## Aus dem Quelltext starten

Es werden keine Zusatzpakete gebraucht. Entwickelt und getestet mit Python 3.14.

```bat
py organigramm_gui.py
py ordner_organigramm_v2.py "D:\Ordner" --tiefe 3
py ordner_organigramm_v2.py -h
```

`bauen.bat` baut den fertigen Programmordner nach `dist\Ordner-Organigramm`. Dafür wird PyInstaller in einer eigenen Umgebung installiert.

## Lizenz

[MIT](LICENSE)
