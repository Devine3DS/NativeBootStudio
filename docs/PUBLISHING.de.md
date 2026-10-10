# Native Boot Studio auf GitHub veröffentlichen

Die vorbereiteten Pakete laden nichts automatisch auf GitHub hoch. Diese Anleitung beschreibt Quellcode-Repository und Windows-Release.

## 1. Repository anlegen

Entpacke `NativeBootStudio-4.2.1-source.zip` in einen neuen Ordner. Erstelle auf GitHub ein öffentliches Repository, zum Beispiel `NativeBootStudio`. Für den unten gezeigten Git-Ablauf legst du es leer an, ohne automatisch erzeugte README/Lizenz.

Lade den **Inhalt** des entpackten Source-Ordners mit erhaltenen Unterordnern hoch. `README.md` gehört direkt ins Repository-Hauptverzeichnis, neben `README.de.md`, `LICENSE`, `src/`, `tests/`, `docs/`, `scripts/`, `licenses/` und `.github/`. Nimm `.gitignore` und `.gitattributes` mit; im Explorer sind sie eventuell ausgeblendet. Lade nicht nur die Source-ZIP als einzelne Repository-Datei hoch.

Prüfe, dass Xbox-/XEX-/NAND-Dateien, XexTool, Xenia, lokale `settings.json`, private Projekte, `UserPresets` und Build-Caches fehlen. Das Source-Archiv ist so zusammengestellt. Das alte private 4.2-Paket nicht hochladen.

Alternativ kannst du mit installiertem Git im entpackten Source-Hauptordner PowerShell öffnen:

```powershell
git init -b main
git add .
git status --short
git commit -m "Initial public release of Native Boot Studio"
git remote add origin YOUR-REPOSITORY-URL
git push -u origin main
```

Ersetze `YOUR-REPOSITORY-URL` durch die HTTPS-Adresse deines Repositorys. Nutze die normale GitHub-Anmeldung; schreibe keine Zugriffstokens in Code oder Dokumentation. Prüfe `git status` vor dem Commit.

Die README zeigt die englische Übersicht mit Link zur deutschen Fassung. Die MIT-Lizenz gilt für den eigenen Projektcode; Hinweise zu Abhängigkeiten bleiben unter `licenses/`.

## 2. Release v4.2.1 erstellen

Öffne auf GitHub **Releases → Draft a new release**:

1. Erstelle den Tag `v4.2.1` auf dem geprüften Commit von `main`.
2. Titel: **Native Boot Studio 4.2.1**.
3. Übernimm die fertigen [englischen Versionshinweise](releases/v4.2.1.en.md). Hänge bei Bedarf die [deutsche Fassung](releases/v4.2.1.de.md) an.
4. Füge `NativeBootStudio-4.2.1-Windows-x64.zip` und `SHA256SUMS.txt` hinzu. Die saubere Source-ZIP ist optional; GitHub bietet zusätzlich Quellcode-Archive des Tags an.
5. Speichere zunächst den Entwurf, prüfe Dateien und Beschreibung und veröffentliche danach.

Verwende ausschließlich die neuen öffentlichen Archive. Die Windows-ZIP enthält Programm, deutsche/englische Benutzer- und Installationsanleitungen, eine CRC-32-Hilfe und Laufzeit-Lizenzhinweise. Originalanimation, XexTool, optional Xenia und bei der HDD-Variante den Remap stellt jeder Nutzer selbst bereit.

GitHub Actions erstellt bei passenden Pushes Builds und Workflow-Artefakte. Der Workflow erstellt oder veröffentlicht selbst kein Release. Warte bei einem Workflow-Build auf erfolgreiche Prüfungen, bevor du ihn veröffentlichst.

## 3. Weitere Versionen

Aktualisiere `VERSION` in `src/studio.py`, Changelog, Anleitungen/Versionsdateinamen nach Bedarf und Versionshinweise. Führe Formatprüfung, Tests und `python scripts/build_release.py --build` aus. Prüfe die neuen ZIPs, markiere den getesteten Commit mit einem Tag und erstelle ein neues Release. Beschreibe Updates so, dass eigene Presetbibliotheken erhalten bleiben.

Offizielle Hinweise: [GitHub-Releases verwalten](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository), [Repository lizenzieren](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) und unsere [Weitergabehinweise](DISTRIBUTION.de.md).
