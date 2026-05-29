---
name: project-review
description: Esegue una code review sistematica del progetto MeetWiki per qualità del codice, robustezza, sicurezza, documentazione e preparazione production/open-source. Da usare quando l'utente chiede "revisiona il progetto", "code review", "quality check", "rendilo production-ready", "audit del codice", "trova problemi nel codice".
---

# Skill: project-review

Esegue direttamente una revisione sistematica del progetto, analizzando il codice,
identificando problemi concreti e proponendo fix. NON genera un prompt per un'altra AI:
**fa** la review.

## Quando usare
- Utente chiede "fai una code review", "revisiona il progetto", "quality audit"
- Utente vuole preparare il progetto per open-source o condivisione
- Utente chiede "cosa migliorare", "rendilo production-ready", "trova bug"
- Prima di un rilascio o milestone importante

## Quando NON usare
- Per correggere un singolo bug già noto → risolvilo direttamente
- Per domande sulle riunioni → usa `meetwiki-search` o `meetwiki-ask`

## Contesto del progetto

**Stack**: Python 3.14, Windows-only, single-user. Playwright 1.44 + python-dotenv.
Nessun YAML parser esterno (regex intenzionale). 2 dipendenze pip.

**Architettura**: pipeline sequenziale con 7 script idempotenti + 1 orchestratore.
Stato in JSON (`manifest.json`, `actions_status.json`, `processed_emails.json`).

## Procedura

### 1. Raccolta dati correnti

Prima di revisare, eseguire:

```powershell
# Conta righe per script
Get-ChildItem scripts\meetwiki_*.py, scripts\gemini_notes_downloader.py, menu.py | ForEach-Object { "$($_.Name): $((Get-Content $_ | Measure-Object -Line).Lines) righe" }

# Verifica presenza test
Get-ChildItem -Recurse -Filter "test_*.py" | Select-Object FullName

# Verifica config linting
Test-Path pyproject.toml, setup.cfg, .flake8, ruff.toml

# Verifica file mancanti referenziati
Test-Path "MeetWiki/.meta/schema.md"
```

### 2. Analisi su 6 assi (priorità decrescente)

Leggere i file sorgente principali ed esaminare ognuno su questi assi:

#### Asse 1 — Correttezza e robustezza (PRIORITÀ MASSIMA)

Cercare:
- Bug latenti, race condition, edge case non gestiti
- Gestione errori: crash silenti, fallback pericolosi (es. `date → now()` senza warning)
- File I/O: encoding issues, mancanza di atomic writes
- Corruzione stato: `manifest.json`, `actions_status.json`, `processed_emails.json`
- Idempotenza: side-effect nascosti nella re-esecuzione

#### Asse 2 — Architettura e manutenibilità

Verificare:
- Code duplication: `parse_frontmatter()` in 5 script, `extract_section()` in 4, `slugify()` in 3
- Cross-import hack: `sys.path.insert(0, ...)` in `meetwiki_kanban.py`
- CLI parsing manuale: `"--flag" in sys.argv` — fragile per estensione futura?
- Separazione responsabilità e facilità di aggiungere nuovi script

#### Asse 3 — Sicurezza (OWASP-aligned, contesto desktop)

Controllare:
- Hardcoded paths con username Windows nei default
- `taskkill /F /IM chrome.exe` uccide TUTTI i Chrome, non solo quello gestito
- Remote debugging port 9222 esposta durante il download
- `.env` in `.gitignore`? Secrets gestiti correttamente?
- Subprocess calls: injection possibili?
- File permission / path traversal

#### Asse 4 — Testing e quality assurance

Valutare stato attuale e proporre strategia pragmatica:
- Quali funzioni testare per prime (massimo ROI)?
- Unit test vs integration test vs golden-file test?
- Come testare il downloader senza Gmail reale?
- Config minima: ruff, mypy, pytest, pre-commit?

#### Asse 5 — Documentazione

Verificare:
- Coerenza tra `AGENTS.md`, `README.md`, `MeetWiki/README.md`, `docs/*.md`, skill `SKILL.md`
- `MeetWiki/.meta/schema.md` è referenziato ovunque ma **potrebbe non esistere**
- Docstring nei moduli sufficienti?
- Istruzioni di setup (`docs/setup.md`, `setup.bat`) corrette?

#### Asse 6 — Preparazione open-source

Controllare:
- LICENSE presente?
- `pyproject.toml` vs `requirements.txt` — serve modernizzare?
- Entry point: `__main__.py` o `menu.py` basta?
- `.gitignore` completo? (`chrome_profile/`, `.venv/`, `.cache/`, `note_riunioni/archive/`)
- CONTRIBUTING.md, CHANGELOG?
- Nomi variabili/commenti in italiano: problema per OSS?

### 3. File da esaminare (in ordine di importanza)

| File | Ruolo |
|------|-------|
| `scripts/meetwiki_ingest.py` | Core: parsing, dedup, archival |
| `scripts/gemini_notes_downloader.py` | Browser automation Playwright |
| `scripts/meetwiki_update.py` | Orchestratore pipeline |
| `scripts/meetwiki_actions.py` | Action item tracking |
| `scripts/meetwiki_kanban.py` | Kanban sync bidirezionale |
| `scripts/meetwiki_ask.py` | BM25 search engine |
| `scripts/meetwiki_digest.py` | Digest settimanali/mensili |
| `scripts/meetwiki_index.py` | Indici INDEX/TAGS/PEOPLE |
| `scripts/meetwiki_summarize.py` | Pagine aggregate |
| `menu.py` | TUI interattiva (Windows) |

Per una review completa, leggere TUTTI. Per una review rapida (se l'utente
specifica scope), limitarsi ai file rilevanti.

## Vincoli di design (NON suggerire modifiche a questi)

| Vincolo | Motivo |
|---------|--------|
| NO `pyyaml` | Parser regex intenzionale per zero-deps |
| NO framework web | Tool CLI/desktop |
| NO database | JSON file come store è voluto |
| NO multiprocessing | Pipeline sequenziale by design |
| NO cross-platform | Target Windows, non investire effort qui |

**OK proporre** (se il beneficio è chiaro e concreto):
- Modulo shared `meetwiki_common.py` per eliminare duplication
- `argparse` se migliora UX senza over-engineering
- Typing più strict / mypy config
- Test e CI minimali
- Atomic writes per i JSON di stato

## Formato output della review

Produrre il report come file Markdown in **`docs/REVIEW_REPORT.md`**.
Se il file esiste già, sovrascriverlo con i risultati aggiornati.

### Struttura del file

```markdown
# Code Review Report — MeetWiki Pipeline

> Generato il: YYYY-MM-DD

## Checklist Summary

- [ ] 🔴 [Breve descrizione issue critico 1](#finding-id)
- [ ] 🔴 [Breve descrizione issue critico 2](#finding-id)
- [ ] 🟡 [Breve descrizione issue medio 1](#finding-id)
- [ ] 🟡 [Breve descrizione issue medio 2](#finding-id)
- [ ] 🟢 [Breve descrizione issue basso 1](#finding-id)
- ...

---

## Asse 1 — Correttezza e robustezza

### Findings
...

### Raccomandazioni
...

## Asse 2 — Architettura e manutenibilità
...

(ripetere per tutti i 6 assi)

---

## Tabella riassuntiva top-10

| # | Azione | Asse | Severità | Effort |
|---|--------|------|----------|--------|
| 1 | ... | ... | 🔴 | S |
...
```

### Regole per la checklist

- La checklist è in testa al documento, subito dopo il titolo
- Ogni item è un `- [ ]` con emoji di severità e link ancora alla sezione
- Ordine: prima tutti i 🔴, poi 🟡, poi 🟢
- Ogni item deve essere actionable (verbo all'infinito: "Aggiungere...", "Rimuovere...", "Sostituire...")
- La checklist serve come tracker: l'utente spunta man mano che risolve
- Includere TUTTI i findings, non solo i top-10

### Per ogni asse:
1. **Findings**: lista di issue concreti con severità
   - 🔴 Critico: bug, corruzione dati, security hole
   - 🟡 Medio: code smell, manutenibilità, robustezza
   - 🟢 Basso: style, best practice, nice-to-have
2. **Raccomandazioni**: azioni specifiche ordinate per impatto/sforzo
3. **Code snippets**: mostrare prima/dopo per le fix proposte

### Alla fine:
**Tabella riassuntiva** con top-10 azioni ordinate per priorità:

| # | Azione | Asse | Severità | Effort |
|---|--------|------|----------|--------|
| 1 | ... | ... | 🔴/🟡/🟢 | S/M/L |

Dove effort: **S** = <30 min, **M** = 1-3h, **L** = mezza giornata+

## Varianti

- **Review rapida** ("quick review", "check veloce"): solo Asse 1 + 3 sui top-3 file
- **Review completa** (default): tutti i 6 assi, tutti i file
- **Review mirata** ("review sicurezza", "review test"): solo l'asse specificato, approfondito
