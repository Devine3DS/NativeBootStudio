# Was darf mitgeliefert werden?

Stand der Prüfung: **10. Oktober 2026**. Hier stehen die für dieses Paket geprüften Erlaubnisse, keine pauschale rechtliche Garantie für jedes Land und jede Herkunft einer Datei.

| Bestandteil | Entscheidung für die Veröffentlichung |
| --- | --- |
| Eigener Native-Boot-Studio-Quellcode | Mit MIT-Lizenzhinweis enthalten. |
| Eingebettete Python-/Tcl-/Tk-/Pillow-/PyInstaller-/packaging-Laufzeit | Mit den Originalhinweisen unter `licenses/runtime/` enthalten. |
| Xenia | Seine BSD-3-Clause-Lizenz erlaubt Quellcode-/Binärweitergabe unter den darin genannten Hinweispflichten. Bei einem Emulatorpaket müssen auch alle enthaltenen Abhängigkeiten geprüft werden. Im schlanken Release separat vom Nutzer bereitgestellt. |
| XexTool 6.3 | Keine ausdrückliche Weitergabeerlaubnis verifiziert. Nicht enthalten; ein Download auf einer Mirror-Seite beweist keine Erlaubnis. |
| Originale Microsoft-`bootanim.xex` | Keine Weitergabeerlaubnis verifiziert. Nicht enthalten. Der Besitz einer Konsole oder Datei erlaubt nicht automatisch deren öffentliche Verbreitung. |
| Umgefärbte oder für die Vorschau angepasste Microsoft-XEX | Enthält weiterhin Microsoft-Code und -Assets. Bearbeitung macht sie nicht zu MIT-Software. Nicht enthalten. |
| Farbpreset-JSON | Enthält Farb-/Einstellungsdaten, keinen Animationscode und keine Xbox-Assets. Das ist die vorgesehene Form zum Teilen von Themes. |

Für Xenia gilt die [offizielle BSD-Lizenz des getesteten Quellcode-Stands](https://github.com/xenia-project/xenia/blob/95a5c3ee2/LICENSE). Bei Weitergabe müssen Copyright, Lizenzbedingungen und Haftungsausschluss erhalten bleiben. Unterstützung durch das Projekt darf nicht suggeriert werden. Die Hauptlizenz beantwortet nicht automatisch die Lizenzfragen sämtlicher Abhängigkeiten eines kompilierten Emulatorpakets.

Bei Microsoft verweist die [offizielle Copyright-Seite](https://www.microsoft.com/en-us/legal/intellectualproperty/copyright/permissions) für Softwareweitergabe auf die jeweilige Softwarelizenz bzw. Bedingungen. Eine Erlaubnis zur Veröffentlichung dieser Bootanimation wurde hier nicht festgestellt. Auch die Einschränkungen für Boot-Screen-Screenshots betreffen die Dokumentation. Dieses Repository verwendet ausschließlich die eigene Preset-Oberfläche.

XexTool stammt von xorloser. Über die [Website des Autors](https://xorloser.com/) konnte bei der Prüfung keine ausdrückliche Weitergabelizenz verifiziert werden. Das bedeutet fehlende Verifikation, nicht die Behauptung, dass der Autor jede Weitergabe pauschal verboten hätte. Vor einer Aufnahme ins Release muss eine passende ausdrückliche Erlaubnis vorliegen.

## Vor der Veröffentlichung

Veröffentliche den Inhalt der sauberen Source-ZIP und die vom öffentlichen Packager erstellte schlanke Windows-ZIP. **Das ältere private 4.2-Paket nicht hochladen**: Es enthält separat bereitgestellte Dateien.

Originale und modifizierte XEX-Dateien, Tools, Emulator-Binärdateien, NAND-Dumps, lokale Einstellungen, persönliche Projekte, Exportbeispiele und private Testordner bleiben draußen. Die Git-Ignorierregeln helfen dabei; der ZIP-Packager verwendet außerdem festgelegte Dateilisten. Prüfe trotzdem das fertige Archiv vor dem Hochladen.

Verwende Screenshots deiner eigenen Programmoberfläche. Teile Themes als `.nbpalette.json`; jeder Nutzer stellt sein kompatibles Original und seine Tools selbst bereit.
