"""English/German UI localization; project values remain language independent."""

import json
from pathlib import Path
import sys
import weakref
import re
import os
import tempfile


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def load_preferences():
    try:
        value = json.loads((app_dir() / "settings.json").read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return {}
        return {
            key: item
            for key, item in value.items()
            if key in ("language", "source", "xextool", "xenia")
            and isinstance(item, str)
            and item.strip()
        }
    except (OSError, ValueError):
        return {}


def save_preferences(**changes):
    value = load_preferences()
    value.update(changes)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=app_dir(), delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, app_dir() / "settings.json")
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


# German source phrases are kept as stable internal keys for existing projects.
TRANSLATIONS = {
    "Nicht eingerichtet": "Not configured",
    "Einrichtung": "Setup",
    "Originalanimation und XexTool werden separat benötigt.\nXenia ist optional für die Shader-Vorschau.": "Provide your original animation and XexTool separately.\nXenia is optional for native shader preview.",
    "XexTool 6.3 selbst bereitstellen. Eine Datei im Ordner tools wird automatisch erkannt.": "Provide XexTool 6.3 yourself. A copy in the tools folder is detected automatically.",
    "Xenia · optionale Shader-Vorschau": "Xenia · optional native shader preview",
    "Xenia auswählen …": "Choose Xenia …",
    "Xenia auswählen": "Choose Xenia",
    "Offizielle Xenia-Version öffnen": "Open official Xenia release",
    "Bitte deine Originalanimation und XexTool auswählen.": "Choose your original animation and XexTool.",
    "Einrichtung erforderlich · Dateien auswählen und Eingabe prüfen.": "Setup required · choose your files and verify the input.",
    "Vorschau-Info": "Preview info",
    "Ersetzen": "Replace",
    "Preset ersetzen": "Replace preset",
    "Die gespeicherten Farben durch deine aktuelle Palette ersetzen?": "Replace the saved colors with your current palette?",
    "Speichern fehlgeschlagen": "Save failed",
    "Farb-Presets": "Color presets",
    "Galerie": "Gallery",
    "Preset speichern": "Save preset",
    "Eigene Presets": "My presets",
    "Eigenes Preset: ": "My preset: ",
    "40 Farbvorlagen · eigene Presets in deiner Bibliothek": "40 built-in palettes · save your own in My presets",
    "Eigene Farbpalette · als Preset speichern": "Custom palette · save it as a preset",
    "Wirbel, Kugel-X, Leuchten und Schrift": "Swirl, sphere X, glow and lettering",
    "Farb-Preset speichern": "Save color preset",
    "Preset umbenennen": "Rename preset",
    "Ein Name für deine Farbpalette": "Give your palette a name",
    "Eigenes Preset gespeichert: ": "My preset saved: ",
    "Eigenes Preset angewendet: ": "My preset applied: ",
    "Deine Farbpalette-Bibliothek": "Your palette library",
    "Importieren …": "Import …",
    "Umbenennen": "Rename",
    "Exportieren …": "Export …",
    "Löschen": "Delete",
    "Anwenden": "Apply",
    "Hauptfarbe": "Main color",
    "Name": "Name",
    "Keine eigenen Presets. Speichere zuerst deine aktuelle Farbpalette.": "No saved presets yet. Save your current palette to get started.",
    "Doppelklick zum Anwenden. Größe, Position und Tempo bleiben erhalten.": "Double-click to apply. Size, position and speed stay unchanged.",
    "Einige Preset-Dateien sind beschädigt und wurden übersprungen.": "Some preset files could not be read and were skipped.",
    "Preset konnte nicht geladen werden": "Could not load preset",
    "Farb-Preset importieren": "Import color preset",
    "Farb-Preset exportieren": "Export color preset",
    "Farb-Preset": "Color preset",
    "Import fehlgeschlagen": "Import failed",
    "Export fehlgeschlagen": "Export failed",
    "Löschen fehlgeschlagen": "Delete failed",
    "Preset löschen": "Delete preset",
    "Dieses eigene Preset aus der Bibliothek entfernen?": "Remove this saved preset from your library?",
    "Die Datei enthält kein unterstütztes Farb-Preset.": "This file is not a supported color preset.",
    "Der Name muss 1 bis 64 Zeichen enthalten.": "Enter a name between 1 and 64 characters.",
    "Das Farb-Preset ist unvollständig.": "This color preset is incomplete.",
    "Das Farb-Preset enthält ungültige Werte.": "This color preset contains invalid values.",
    "Die Preset-Datei ist ungewöhnlich groß.": "This preset file is too large.",
    "Die Datei enthält kein lesbares Farb-Preset.": "This file is not a readable color preset.",
    "Ungültige Preset-ID.": "Invalid preset ID.",
    "Das Preset wurde nicht gefunden.": "Preset not found.",
    "Ein Preset mit diesem Namen existiert bereits.": "A preset with this name already exists.",
    "Bitte außerhalb der Preset-Bibliothek als .nbpalette.json speichern.": "Save outside the preset library as a .nbpalette.json file.",
    "Basis": "Basic",
    "Blau · Standard": "Blue · standard",
    "Cyan · Standard": "Cyan · standard",
    "Violett · Standard": "Purple · standard",
    "Die Zeitleiste steuert die native Animation. Farben werden nach einer kurzen Ladepause aktualisiert.": "The timeline controls the native animation. Colors update after a short reload.",
    "“ übernommen. Hintergrund wird exportiert; Größe, Position und Tempo bleiben erhalten.": "” applied. Background is exported; size, position and speed stay the same.",
    "Shader-Vorschau starten": "Start shader preview",
    "Modell-Vorschau anzeigen": "Show model preview",
    "Native Shader-Vorschau · Originaler Xbox-Renderer über Xenia": "Native shader preview · Original Xbox renderer via Xenia",
    "Originale Shader, Texturen und Kamerafahrt. Emulator-Vorschau; Abgleich auf der Xbox steht noch aus.": "Original shaders, textures and camera. Emulator preview; comparison on Xbox is still pending.",
    "Native Shader werden geladen …": "Loading native shaders …",
    "Shader-Vorschau konnte nicht gestartet werden. Details: ": "Shader preview could not start. Details: ",
    "Die klassische Bootanimation wird nicht mehr unterstützt.": "The classic boot animation is no longer supported.",
    "Öffnen": "Open",
    "Speichern": "Save",
    "Ablauf": "Animation",
    "Dateien": "Files",
    "Ein abgestimmter Farbton": "Main color",
    "40 abgestimmte Presets": "40 color presets",
    "Farben einzeln anpassen": "Customize individual colors",
    "Effekte & Shader": "Effects and lighting",
    "Kugelmaterialien": "Sphere materials",
    "Originaler Schriftzug": "Logo text",
    "Natives Animationstempo": "Animation speed",
    "Was wird exportiert?": "Exported settings",
    "Originaldatei": "Original animation file",
    "Eingabeprüfung": "File check",
    "Projekt": "Project",
    "Neuer Entwurf": "New project",
    "40 Farb-Presets · Native Boot Studio": "40 color presets · Native Boot Studio",
    "Alle Einstellungen auf Original zurückgesetzt. Rückgängig ist verfügbar.": "Original settings restored. You can undo this change.",
    "Dateipfade geändert. Bitte Eingabe prüfen.": "File paths changed. Check the animation file before exporting.",
    "Eingabeprüfung erforderlich. Reiter „Dateien“ → „Eingabe erneut prüfen“.": "Check the animation file in Files → Check files again.",
    "Originaldatei und ausführbare Codebereiche werden geprüft …": "Checking the original animation file …",
    "Originalgeometrie wird geladen …": "Loading animation models …",
    "Ungespeicherte Änderungen": "Unsaved changes",
    "Möchtest du dein aktuelles Projekt zuerst speichern?": "Save your current project first?",
    "XEX wird erstellt, erneut entpackt und bytegenau geprüft …": "Creating bootanim.xex and verifying the exported file …",
    "Originaldatei geprüft. Entwurf bearbeiten und eine neue bootanim.xex exportieren.": "Animation file checked. Customize your project, then export bootanim.xex.",
    "Originaldatei wird geprüft …": "Checking animation file …",
    "Originaldatei noch nicht geprüft": "Animation file has not been checked yet",
    "Gesamtbild": "Full view",
    "Modellansicht": "Model preview",
    "▶ Abspielen": "▶ Play",
    "Ⅱ Pause": "Ⅱ Pause",
    "Violett": "Purple",
    "Blau": "Blue",
    "Grün": "Green",
    "Rot": "Red",
    "Kugel": "Sphere",
    "Blau · klassisch": "Blue · classic",
    "Blau / Schwarz": "Blue / Black",
    "Gold / Schwarz": "Gold / Black",
    "Alle Presets als Vorschau ansehen …": "Browse preset gallery …",
    "Hintergrund · Xbox & Vorschau": "Background",
    "Ausströmender Wirbel": "Swirl color",
    "Kugel-X / Texturen": "Sphere X",
    "Leuchten": "Glow",
    "Helle Effektschicht": "Highlights",
    "Szenenfarbe": "Scene tint",
    "XBOX-Schriftzug": "XBOX text",
    "Shaderfarbe A": "Lighting color A",
    "Shaderfarbe B": "Lighting color B",
    "Größe": "Size",
    "Vertikal": "Vertical",
    "Ausgabe öffnen": "Open export folder",
    "bootanim.xex exportieren …": "Export bootanim.xex …",
    "Übernehmen": "Apply",
    "Eigene Palette": "Custom palette",
    "Preset wählen …": "Choose a preset …",
    "HDD · interne Festplatte": "HDD · Hard drive",
    "NAND · Flash-Abbild": "NAND · Flash memory",
    "HDD: Speichere bootanim.xex auf der Xbox-Festplatte. Die Konsole muss für das Laden von dort eingerichtet sein.": "HDD: Save bootanim.xex to the Xbox hard drive. Your console must be configured to load the animation from there.",
    "NAND: Verwende bootanim.xex beim Erstellen deines NAND-Abbilds. Dieses Programm installiert oder flasht nichts auf die Xbox.": "NAND: Use bootanim.xex when building your NAND image. This program does not install or flash anything to the Xbox.",
    "Projekt gespeichert: ": "Project saved: ",
    "Dateiname": "File name",
    "Die Ausgabe muss die Endung .xex haben.": "The exported file must end in .xex.",
    "Der Export läuft noch. Bitte dessen Abschluss abwarten.": "An export is still running. Please wait for it to finish.",
    "VORSCHAU": "PREVIEW",
    "Hintergrund wird mit exportiert": "Background is included in the export",
    "Originalmodelle · Beleuchtung und Bewegung angenähert": "Original models · Approximate lighting and movement",
    "Farbverläufe zeigen native Ausgangsfarben. Die Xbox-Shader werden nicht emuliert.": "Color samples help you choose a palette. The preview may differ from the Xbox animation.",
    "Drehen": "Rotate",
    "Ansicht, Zoom und Vorschauzeit ändern die exportierte XEX nicht.": "Rotate, zoom and preview time only change this view.",
    "Überträgt den Farbton auf Wirbel, Kugel-X,\nLeuchten und XBOX. Helligkeitsunterschiede bleiben.": "Sets the color of the swirl, sphere X, glow and\nXBOX text while keeping their shading.",
    "Farbe wählen\nHEX oder RGB": "Choose a color\nHEX or RGB",
    "Presets stimmen Hintergrund, Wirbel, Effekte, Kugel\nund Schriftfarben aufeinander ab. Größe und Tempo bleiben.": "Presets coordinate background, swirl, effects, sphere\nand text colors. Size and speed stay the same.",
    "Grundfarben der Materialien. Dynamische Glanzfarben\nkönnen sie in einzelnen Phasen überlagern. Die inneren\nModelle werden in der Vorschau nicht separat gezeigt.": "Sets the base color of each sphere part. Highlights\nmay change its appearance during the animation.\nInner parts are not shown separately in this preview.",
    "0,75 × langsam  ·  1,00 × original  ·  1,25 × schnell\n\nDas Tempo wird in die neue bootanim.xex übernommen.\nDie originalen Bewegungsbahnen bleiben erhalten.\n\nDer Ton bleibt unverändert. Die Synchronität bei\nanderem Tempo ist auf der Xbox noch ungeprüft.": "0.75 × slower  ·  1.00 × original  ·  1.25 × faster\n\nThe exported animation uses this speed.\nThe original movement paths stay the same.\n\nAudio stays unchanged. Audio synchronization at\na different speed has not been tested on Xbox.",
    "✓ Hintergrundfarbe\n✓ Farben von Effekten, Texturen und Wirbel\n✓ Grundfarben der Modelle und des Schriftzugs\n✓ Größe / Position des originalen Schriftzugs\n✓ Natives Tempo\n\nDie Vorschauansicht selbst dient der Betrachtung.\nFreier Text und neue Bewegungsbahnen sind nicht enthalten.": "✓ Background color\n✓ Swirl, sphere X and effect colors\n✓ Sphere and text base colors\n✓ Text size and position\n✓ Animation speed\n\nThe preview camera is only for viewing.\nCustom text and new movement paths are not supported.",
    "Die unveränderte Eingabe bleibt deine Grundlage.\nZum Weiterbearbeiten ein Studio-Projekt öffnen.": "Use your unmodified original as the starting point.\nOpen a saved project to continue editing.",
    "Ein Projekt speichert deine Einstellungen und den\nOriginalpfad. Auf der Xbox wird weiterhin eine\nneu exportierte bootanim.xex verwendet.": "A project saves your editing settings.\nExport bootanim.xex to use your animation\non the Xbox.",
    "XEX-EXPORT": "EXPORT",
    "RGB-Kanäle brauchen ganze Zahlen von 0 bis 255.": "RGB values must be whole numbers from 0 to 255.",
    "Preset auswählen": "Choose a preset",
    "Ein Klick übernimmt die Farben. Originalmodelle mit angenäherter Beleuchtung.": "Click a preset to apply it. Preview lighting is approximate.",
    "Projekt konnte nicht geöffnet werden": "Could not open project",
    "Projekt konnte nicht gespeichert werden": "Could not save project",
    "Meine-Animation.nbstudio.json": "My-Animation.nbstudio.json",
    "Ungültige Einstellungen": "Invalid settings",
    "Original vergleichen": "Compare with original",
    "Ansicht zurücksetzen": "Reset preview",
    "Abgestimmter Farbton": "Main color",
    "Originalen Hintergrund wiederherstellen": "Restore original background",
    "Schriftgröße & Position zurücksetzen": "Reset text size and position",
    "Originaltempo · 1,00 ×": "Original speed · 1.00 ×",
    "Original bootanim.xex auswählen …": "Choose an original bootanim.xex …",
    "XexTool auswählen …": "Choose XexTool …",
    "Eingabe erneut prüfen": "Check files again",
    "Alle Einstellungen zurücksetzen": "Reset all settings",
    "Abbrechen": "Cancel",
    "Zurück zum Entwurf": "Back to editor",
    "Boot-Studio-Projekt": "Boot Studio project",
    "Originaldatei im Reiter „Dateien“ auswählen und prüfen.": "Select and check an animation file in the Files tab.",
    "Eingabeprüfung fehlgeschlagen. Details im Reiter „Dateien“.": "File check failed. See the Files tab for details.",
    "Kugel-X": "Sphere X",
    "Oberfläche": "Surface",
    "Schriftzug": "Text",
    "Farbverläufe": "Color samples",
    "Alle Dateien": "All files",
    "Eingabeprüfung fehlgeschlagen.\n": "File check failed.\n",
    "Export fehlgeschlagen.": "Export failed.",
    "Export fehlgeschlagen": "Export failed",
    "✓ Export geprüft · ": "✓ Export verified · ",
    " geänderte Abbildbytes · Prüfbericht gespeichert": " changed bytes · Report saved",
    "✓ Unterstützte Originalanimation\n✓ Originaldaten geprüft\n": "✓ Supported original animation\n✓ Original data checked\n",
    " Modellvertices · ": " model vertices · ",
    " Textvertices": " text vertices",
    "Vorschaufehler: ": "Preview error: ",
    "Kugeloberfläche": "Sphere surface",
    "Kanten der Vertiefung": "Groove edges",
    "Flächen der Vertiefung": "Groove surface",
    "Inneres Kugelmodell A": "Inner sphere A",
    "Inneres Kugelmodell B": "Inner sphere B",
    "Markenzeichen": "Trademark",
    "Leuchteffekt (Shader)": "Glow effect",
    "Wirbel / Szenenfarbe": "Swirl / scene tint",
    "Keine gültige XEX2-Datei.": "This is not a valid XEX2 file.",
    "Ungültiger XEX-Header.": "Invalid XEX header.",
    "XEX-Dateiformat fehlt.": "XEX file format information is missing.",
    "Interne Prüfung erwartet eine unverschlüsselte, unkomprimierte XEX.": "Verification requires an unencrypted, uncompressed XEX.",
    "Diese Bootanimation wird nicht unterstützt (erwartet: die untersuchte 17559-DLL).": "This animation file is not supported. Use your unmodified modern 17559 original.",
    "Unbekanntes Programmabbild. Keine passenden Offsets garantiert; Export abgebrochen.": "Unknown animation file. Export stopped to avoid changing unsupported data.",
    "Unerwartete Farb- oder Alphawerte.": "Unexpected color or alpha values.",
    "XexTool konnte den Arbeitsschritt nicht abschließen:\n": "XexTool could not complete this step:\n",
    "Ungültige XEX-Seitenbeschreibung.": "Invalid XEX page information.",
    "Der Material-Codebereich ist nicht als ausführbar markiert.": "The animation code area is not marked as executable.",
    "Ungültige XEX-Headerliste.": "Invalid XEX header list.",
    "Ungültige XEX-Pfadbindung.": "Invalid XEX path binding.",
    "Die Eingabedatei darf nicht überschrieben werden.": "The original animation file cannot be overwritten.",
    "XexTool darf nicht überschrieben werden.": "XexTool cannot be overwritten.",
    "Eingabedatei oder XexTool fehlt.": "The animation file or XexTool is missing.",
    "Ausgabedatei oder Prüfbericht existiert bereits.": "The exported file or its report already exists.",
    "Unbekanntes Ausgabeziel.": "Unknown export destination.",
    "Drei RGB-Farben mit Werten zwischen 0 und 1 erforderlich.": "Three RGB colors with values from 0 to 1 are required.",
    "Rückprüfung fehlgeschlagen: entpacktes Programmabbild weicht ab.": "Export verification failed: the unpacked animation does not match.",
    "Änderungen außerhalb der freigegebenen Parameter und Material-Hooks gefunden.": "Export verification found changes outside the supported animation settings.",
    "Title-/DLL-Flags gingen verloren.": "The exported file has incorrect module flags.",
    "Exporttabelle ging verloren.": "The exported file has an incorrect export table.",
    "Medien-/Pfadbindung wurde für HDD nicht vollständig entfernt.": "The HDD export still contains media or path restrictions.",
    "Die ursprüngliche Medien-/Pfadbindung wurde für NAND verändert.": "The NAND export changed the original media or path restrictions.",
    "Die Eingabedatei wurde während des Exports geändert.": "The original file changed while exporting.",
    "Unbekanntes Projektformat.": "Unknown project format.",
    "Animationstempo muss zwischen 0,75 und 1,25 liegen.": "Animation speed must be between 0.75 and 1.25.",
    "Glanzwerte sind in dieser Version nicht editierbar.": "Highlight values cannot be edited in this version.",
    "Ungültige Anzahl von Farbparametern.": "Invalid number of color settings.",
    "Ungültige RGB-Werte im Projekt.": "The project contains invalid RGB values.",
    "Ungültige Farbe für Texturen oder Wirbel.": "Invalid texture, swirl or background color.",
    "Schriftzug-Transformation außerhalb des unterstützten Bereichs.": "Text size or position is outside the supported range.",
    "Der reservierte Codebereich ist nicht leer.": "The original animation code area contains unexpected data.",
    "Unerwartete Instruktion am Hintergrund-Hook.": "Unexpected background code.",
    "Unerwartete Instruktion am Material-Hook.": "Unexpected material code.",
    "Material-Hooks überschreiten den Codebereich.": "Material changes exceed the available code area.",
    "Unerwartete Instruktion in der nativen Zeitberechnung.": "Unexpected animation timing code.",
    "Unerwartete Instruktion am Textur-Hook.": "Unexpected texture code.",
    "Unerwartete Instruktion am Wirbel-Hook.": "Unexpected swirl code.",
    "Wirbel-Hooks überschreiten den Codebereich.": "Swirl changes exceed the available code area.",
    "Unerwarteter Hintergrund-Shader.": "Unexpected background shader.",
    "Bitte eine Farbe als #RRGGBB eingeben, z. B. #0080FF.": "Enter a color as #RRGGBB, for example #0080FF.",
    "Die Projektdatei ist ungewöhnlich groß.": "The project file is too large.",
    "Ein Projekt darf weder die Original-XEX noch XexTool überschreiben.": "A project cannot overwrite the original animation or XexTool.",
    "Das Projekt muss ein JSON-Objekt enthalten.": "The project must contain a JSON object.",
    "Das Ausgabeziel ist ungültig.": "Invalid export destination.",
    "Das Projekt ist unvollständig oder enthält ungültige Werte.": "The project is incomplete or contains invalid values.",
    "Die Datei enthält kein lesbares Boot-Studio-Projekt.": "This file is not a readable Boot Studio project.",
    "Eingabedatei oder XexTool-Pfad fehlt im Projekt.": "The project is missing the animation file or XexTool path.",
    "Dein Entwurf": "Your design",
    "Wirbel · dunkel": "Swirl · dark",
    "Wirbel · mittel": "Swirl · medium",
    "Wirbel · hell": "Swirl · light",
    "Kugel-X · Textur": "Sphere X · texture",
    "Kugel-X · dunkel": "Sphere X · dark",
    "Alle": "All",
    "Klassisch": "Classic",
    "Hell": "Light",
    "Dunkel": "Dark",
    "Pastell": "Pastel",
    "Zweifarbig": "Two-tone",
    "Xbox Original": "Xbox Original",
    "Cyan · klassisch": "Cyan · classic",
    "Violett · klassisch": "Purple · classic",
    "Eisblau": "Ice Blue",
    "Saphir": "Sapphire",
    "Ozean": "Ocean",
    "Limette": "Lime",
    "Lavendel": "Lavender",
    "Koralle": "Coral",
    "Sonnenaufgang": "Sunrise",
    "Blau auf Schwarz": "Blue on Black",
    "Cyan auf Schwarz": "Cyan on Black",
    "Smaragd-Nacht": "Emerald Night",
    "Waldnacht": "Forest Night",
    "Violette Nacht": "Purple Night",
    "Glut": "Ember",
    "Bronze-Nacht": "Bronze Night",
    "Gold auf Schwarz": "Gold on Black",
    "Graphit": "Graphite",
    "Mondlicht": "Moonlight",
    "Eisnebel": "Ice Mist",
    "Fliedernebel": "Lilac Mist",
    "Midnight Blue": "Midnight Blue",
    "Arctic Night": "Arctic Night",
    "Neon Pink": "Neon Pink",
    "Crimson Black": "Crimson Black",
    "Mintnebel": "Mint Mist",
    "Pfirsich": "Peach",
    "Warmes Silber": "Warm Silver",
    "Rosenquarz": "Rose Quartz",
    "Sunset · Orange & Pink": "Sunset · Orange & Pink",
    "Aurora · Türkis & Violett": "Aurora · Teal & Purple",
    "Royal · Violett & Gold": "Royal · Purple & Gold",
    "Vulkan · Rot & Orange": "Volcano · Red & Orange",
    "Champagner · Weiß & Gold": "Champagne · White & Gold",
    "Animation": "Animation",
    "Neu · Wirbel": "Modern · Swirl",
    "Alt · Klassisch": "Classic · Original",
    "Sprache": "Language",
    "Tempo": "Speed",
    "Unbekanntes Farb-Preset.": "Unknown color preset.",
    "Unbekannte Animation im Projekt.": "Unknown animation in the project.",
    "Unbekannter Paketpfad im Projekt.": "Unknown application-relative file path in the project.",
    "Textur-Hooks überschreiten den Codebereich.": "Texture changes exceed the available code area.",
    "Klassische Originalanimation. Farbbearbeitung ist für diese Animation noch nicht verfügbar.": "Classic original animation. Color editing is not yet available for this animation.",
    "Klassische Originalanimation geladen. Wähle HDD oder NAND und exportiere bootanim.xex.": "Classic original animation loaded. Choose HDD or NAND and export bootanim.xex.",
    "“ übernommen. Hintergrund wird exportiert; Größe, Position und Tempo bleiben erhalten.": "” applied. Background is exported; size, position and speed stay the same.",
    "Preset „": "Preset “",
    "Preset: ": "Preset: ",
    "Tipp: „Farbverläufe“ zeigt die Farbwirkung der\nWirbel- und Texturregler ohne angenäherte Beleuchtung.": "Tip: Color samples show the swirl and sphere X\ncolors without preview lighting.",
}

GERMAN_TEXT = {
    "Presets stimmen Hintergrund, Wirbel, Effekte, Kugel\nund Schriftfarben aufeinander ab. Größe und Tempo bleiben.": "Farbvorlagen stimmen Hintergrund, Wirbel, Beleuchtung,\nKugel und Schrift aufeinander ab. Größe und Tempo bleiben erhalten.",
    "Ein abgestimmter Farbton": "Hauptfarbe",
    "Abgestimmter Farbton": "Hauptfarbe",
    "40 abgestimmte Presets": "40 Farbvorlagen",
    "Farben einzeln anpassen": "Einzelne Farben ändern",
    "Effekte & Shader": "Effekte und Beleuchtung",
    "Shaderfarbe A": "Beleuchtung A",
    "Shaderfarbe B": "Beleuchtung B",
    "Natives Animationstempo": "Geschwindigkeit",
    "Tempo": "Geschwindigkeit",
    "Hintergrund · Xbox & Vorschau": "Hintergrund",
    "Ausströmender Wirbel": "Wirbelfarbe",
    "Kugel-X / Texturen": "X auf der Kugel",
    "Leuchten": "Leuchteffekt",
    "Helle Effektschicht": "Helle Effekte",
    "Szenenfarbe": "Grundfarbe der Animation",
    "Originalmodelle · Beleuchtung und Bewegung angenähert": "Modellvorschau · Beleuchtung und Bewegung vereinfacht",
    "Farbverläufe zeigen native Ausgangsfarben. Die Xbox-Shader werden nicht emuliert.": "Farbbeispiele helfen bei der Auswahl. Die Vorschau kann von der Xbox-Animation abweichen.",
    "Ansicht, Zoom und Vorschauzeit ändern die exportierte XEX nicht.": "Drehen, Zoom und Vorschauzeit verändern nur diese Ansicht.",
    "Die unveränderte Eingabe bleibt deine Grundlage.\nZum Weiterbearbeiten ein Studio-Projekt öffnen.": "Verwende dein unverändertes Original als Grundlage.\nMit „Öffnen“ ein gespeichertes Projekt laden.",
    "Originaldatei und ausführbare Codebereiche werden geprüft …": "Die Originalanimation wird geprüft …",
    "Originalgeometrie wird geladen …": "Die Vorschau wird geladen …",
}


class Locale:
    def __init__(self):
        self.language = "en"
        self.variables = []
        self.installed = False
        self.language = load_preferences().get("language", "en")
        if self.language not in ("en", "de"):
            self.language = "en"

    def convert(self, value, reverse=False, mapping=None):
        if not isinstance(value, str):
            return value
        mapping = TRANSLATIONS if mapping is None else mapping
        mapping = {v: k for k, v in mapping.items()} if reverse else mapping
        if value in mapping:
            return mapping[value]
        # Match whole words/phrases in one pass, without translating replacements again.
        alternatives = []
        for key in sorted(mapping, key=len, reverse=True):
            escaped = re.escape(key)
            if key[0].isalnum():
                escaped = r"(?<!\w)" + escaped
            if key[-1].isalnum():
                escaped += r"(?!\w)"
            alternatives.append(escaped)
        return re.sub("|".join(alternatives), lambda match: mapping[match.group()], value)

    def canonical(self, value):
        if isinstance(value, str) and value in TRANSLATIONS:
            return value
        return self.convert(self.convert(value, True, GERMAN_TEXT), True)

    def text(self, value):
        canonical = (
            value if isinstance(value, str) and value in TRANSLATIONS else self.canonical(value)
        )
        return (
            self.convert(canonical)
            if self.language == "en"
            else self.convert(canonical, mapping=GERMAN_TEXT)
        )

    def options(self, kwargs):
        result = dict(kwargs)
        if "text" in result:
            result["text"] = self.text(result["text"])
        if "values" in result:
            result["values"] = [self.text(v) for v in result["values"]]
        return result

    def set(self, language, root=None, persist=True):
        self.language = language
        if persist:
            try:
                save_preferences(language=language)
            except OSError:
                pass
        self.variables = [ref for ref in self.variables if ref() is not None]
        for ref in self.variables:
            variable = ref()
            try:
                variable.set(variable.get())
            except Exception:
                pass
        if root:

            def visit(widget):
                try:
                    if "text" in widget.keys():
                        widget.configure(text=self.text(widget.cget("text")))
                    if "values" in widget.keys():
                        widget.configure(values=[self.text(v) for v in widget.cget("values")])
                    if widget.winfo_class() == "TNotebook":
                        for tab in widget.tabs():
                            widget.tab(tab, text=self.text(widget.tab(tab, "text")))
                    if widget.winfo_class() in ("Tk", "Toplevel"):
                        widget.title(self.text(widget.title()))
                    if widget.winfo_class() == "Canvas":
                        for item in widget.find_all():
                            if widget.type(item) == "text":
                                widget.itemconfigure(
                                    item, text=self.text(widget.itemcget(item, "text"))
                                )
                    for child in widget.winfo_children():
                        visit(child)
                except Exception:
                    pass

            visit(root)

    def install(self):
        if self.installed:
            return
        self.installed = True
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox

        locale = self
        self.RawStringVar = tk.StringVar

        class LocalStringVar(tk.StringVar):
            def __init__(self, *args, **kwargs):
                if "value" in kwargs:
                    kwargs["value"] = locale.text(kwargs["value"])
                super().__init__(*args, **kwargs)
                locale.variables.append(weakref.ref(self))

            def get(self):
                return locale.canonical(super().get())

            def set(self, value):
                super().set(locale.text(value))

        tk.StringVar = LocalStringVar
        base_toplevel = tk.Toplevel

        class LocalToplevel(base_toplevel):
            def title(self, value=None):
                return super().title(locale.text(value)) if value is not None else super().title()

        tk.Toplevel = LocalToplevel
        for module, names in (
            (tk, ("Button", "Label", "Checkbutton")),
            (ttk, ("Button", "Label", "Checkbutton", "Combobox", "Notebook")),
        ):
            for name in names:
                base = getattr(module, name)

                def make(base):
                    class LocalWidget(base):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, **locale.options(kwargs))

                        def configure(self, cnf=None, **kwargs):
                            if isinstance(cnf, dict):
                                cnf = locale.options(cnf)
                            return super().configure(cnf, **locale.options(kwargs))

                        config = configure

                    if issubclass(base, ttk.Notebook):

                        def add(self, child, **kwargs):
                            return base.add(self, child, **locale.options(kwargs))

                        LocalWidget.add = add
                    return LocalWidget

                setattr(module, name, make(base))
        for module, names in (
            (filedialog, ("askopenfilename", "asksaveasfilename")),
            (messagebox, ("showerror", "showinfo", "askyesnocancel", "askyesno")),
        ):
            for name in names:
                original = getattr(module, name)

                def make(original):
                    def localized(*args, **kwargs):
                        args = tuple(locale.text(v) if isinstance(v, str) else v for v in args)
                        for key in ("title", "message", "initialfile"):
                            if key in kwargs:
                                kwargs[key] = locale.text(kwargs[key])
                        if "filetypes" in kwargs:
                            kwargs["filetypes"] = [
                                (locale.text(a), b) for a, b in kwargs["filetypes"]
                            ]
                        return original(*args, **kwargs)

                    return localized

                setattr(module, name, make(original))


locale = Locale()


def t(value):
    return locale.text(value)
