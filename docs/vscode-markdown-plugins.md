# Plugin VS Code per Markdown / Knowledge base

Promemoria personale sui plugin VS Code utili per editing markdown stile Obsidian
e per visualizzare il grafo dei link tra note (es. MeetWiki).

## Editor WYSIWYG / preview avanzata

| Plugin | ID | Cosa fa | Limiti |
|---|---|---|---|
| **Office Viewer (Markdown Editor)** | `cweijan.vscode-office` | WYSIWYG completo (Vditor): tabelle visuali, math, mermaid, mind-map, "instant rendering" tipo Typora. Probabile miglior WYSIWYG su VS Code. | Apre i `.md` con editor custom (disabilitabile per file). |
| **Markdown Editor** | `zaaack.markdown-editor` | WYSIWYG semplice stile Typora/Obsidian: heading, liste, tabelle, immagini drag&drop, KaTeX, mermaid, front-matter. | Meno features di Office Viewer. Niente grafo, niente backlink. |
| **Markdown Preview Enhanced** | `shd101wyy.markdown-preview-enhanced` | Preview ricchissima: mermaid, PlantUML, KaTeX, code chunks eseguibili, export PDF/HTML/PNG. | Solo preview, non editing inline. |
| **Markdown All in One** | `yzhang.markdown-all-in-one` | Scorciatoie, TOC automatico, list editing, table formatter. Quasi obbligatorio. | Non è WYSIWYG. |
| **Front Matter CMS** | `eliostruyf.vscode-front-matter` | Gestione frontmatter YAML visuale, tassonomie, media manager, dashboard note. Ottimo per vault strutturati. | Non WYSIWYG: resta source + preview. |

**Combo consigliata per MeetWiki**:
`cweijan.vscode-office` (WYSIWYG) + `yzhang.markdown-all-in-one` (scorciatoie) + `eliostruyf.vscode-front-matter` (frontmatter).

## Grafo dei link (stile Obsidian)

| Plugin | ID | Cosa fa |
|---|---|---|
| **Foam** | `foam.foam-vscode` | Il più vicino a Obsidian su VS Code: `[[wikilink]]` cliccabili, **grafo interattivo**, backlinks panel, daily notes, tag explorer, template. |
| **Markdown Links** | `tchayen.markdown-links` | Solo grafo: visualizza il network di link tra `.md` del workspace. Leggero, no backlink panel. |
| **Memo** | `svsool.markdown-memo` | Wikilink, backlinks, link refactoring. Niente grafo nativo. |

## Limiti rispetto a Obsidian (MeetWiki)

Nessun plugin VS Code replica:

- **Plugin community Obsidian** (`obsidian-kanban`, `dataview`).
- Il flusso Kanban + sync `MeetWiki/.meta/actions_status.json`.
- Il vault concept (su VS Code lavori sul workspace).

VS Code + questi plugin servono per **consultare e ritoccare le note senza uscire**
dall'editor. Per il workflow completo (Kanban bidirezionale, dataview query)
Obsidian resta necessario.

## Install rapido

```powershell
code --install-extension cweijan.vscode-office
code --install-extension yzhang.markdown-all-in-one
code --install-extension eliostruyf.vscode-front-matter
code --install-extension foam.foam-vscode
```
