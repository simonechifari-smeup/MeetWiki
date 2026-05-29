---
name: docs-review
description: Revisiona e integra la documentazione del progetto MeetWiki. Controlla allineamento tra README.md, AGENTS.md, docs/*.md, MeetWiki/README.md e le skill. Individua sezioni obsolete, mancanti o incoerenti e le corregge inline. Da usare quando l'utente chiede "revisiona la documentazione", "aggiorna i docs", "allinea la documentazione", "controlla che i docs siano corretti", "integra la documentazione".
---

# Skill: docs-review

Revisiona e integra **inline** la documentazione del progetto, correggendo
incoerenze, sezioni obsolete e informazioni mancanti. Non genera report: **fa** le fix.

## Quando usare

- Utente chiede "revisiona la documentazione", "aggiorna i docs", "allinea la doc"
- Dopo un ciclo di sviluppo (nuovi script, flag CLI, struttura cartelle)
- Prima di un rilascio o apertura open-source
- Dopo `project-review` (che identifica problemi di codice: questa integra i docs)

## Quando NON usare

- Per code review → usa `project-review`
- Per aggiornare la wiki MeetWiki (note riunioni) → usa `meetwiki-update`
- Per correggere un singolo file già noto → editalo direttamente

## File da revisionare (in ordine di priorità)

| File | Cosa controllare |
|------|-----------------|
| `README.md` | Badge, stack, comandi rapidi, tabella skill, struttura cartelle |
| `AGENTS.md` | Comandi rapidi, flag CLI, struttura cartelle, procedura rilascio |
| `docs/setup.md` | Prerequisiti Python version, dipendenze, passi installazione |
| `docs/usage.md` | Comandi aggiornati (nuovi flag, --dry-run, --verbose) |
| `docs/faq.md` | Troubleshooting allineato ai comportamenti attuali |
| `docs/architecture.md` | Diagrammi, componenti, scelte progettuali (meetwiki_common) |
| `MeetWiki/README.md` | Struttura cartelle, tabella script, link interni |
| `.github/skills/*/SKILL.md` | Flag CLI aggiornati, passi procedura coerenti con gli script |
| `CONTRIBUTING.md` | Comandi lint/test, setup dev |
| `CHANGELOG.md` | Sezione Unreleased presente e aggiornata |

## Procedura

### 1. Raccolta stato attuale

```powershell
# Versione corrente
Select-String -Path pyproject.toml -Pattern "^version"

# Flag CLI di ogni script
Get-ChildItem scripts\meetwiki_*.py | ForEach-Object {
    $flags = Select-String -Path $_ -Pattern "add_argument" | Select-Object -First 5
    if ($flags) { Write-Output "$($_.Name):"; $flags | ForEach-Object { "  " + $_.Line.Trim() } }
}

# Script presenti
Get-ChildItem scripts\meetwiki_*.py | Select-Object -ExpandProperty Name

# Struttura MeetWiki/notes (partizionamento per mese)
Get-ChildItem MeetWiki\notes\ -Directory | Select-Object Name | Select-Object -First 5
```

### 2. Checklist di revisione

Per ogni file nella tabella sopra, verificare:

#### README.md
- [ ] Versione Python nel badge allineata a `pyproject.toml` (`requires-python`)
- [ ] Badge Lint punta al workflow corretto (`.github/workflows/lint.yml`)
- [ ] Tabella script completa: include `meetwiki_common.py` (utility) se elencato
- [ ] Sezione "Struttura" riflette la cartella `tests/` e `pyproject.toml`
- [ ] Comandi rapidi includono `--dry-run` e `--verbose` dove rilevante

#### AGENTS.md
- [ ] Sezione "Comandi rapidi" include tutti i flag attuali
- [ ] `--dry-run` documentato per `meetwiki_update.py` e `meetwiki_ingest.py`
- [ ] `--verbose` documentato per `meetwiki_ingest.py`
- [ ] Python version in "Stack tecnico" allineata a `pyproject.toml`
- [ ] Tabella skill completa (include `docs-review` dopo questa skill)
- [ ] "Cosa fare dopo modifiche" include riga per modifiche docs

#### docs/setup.md
- [ ] Versione Python aggiornata (3.12+ → allineata a `requires-python` in pyproject.toml)
- [ ] `pip install -e ".[dev]"` per installare anche le dipendenze dev (pytest, ruff)
- [ ] Menzione di `pyproject.toml` come fonte dipendenze
- [ ] Passo opzionale: configurazione `pre-commit` o `ruff`

#### docs/usage.md
- [ ] Flag `--dry-run` documentato per `meetwiki_update.py`
- [ ] Flag `--verbose` documentato per `meetwiki_ingest.py`
- [ ] Sezione "Test" con `python -m pytest` o `python -m pytest -q`
- [ ] Sezione "Linting" con `ruff check scripts/`

#### docs/architecture.md
- [ ] Menzione di `meetwiki_common.py` come modulo utility condiviso
- [ ] Menzione di `tests/` e `pyproject.toml`

#### docs/faq.md
- [ ] Troubleshooting per `--dry-run` (utile per debug)
- [ ] FAQ su come eseguire i test
- [ ] FAQ su come aggiungere/modificare flag CLI

#### MeetWiki/README.md
- [ ] Tabella script aggiornata (include `meetwiki_common.py`)
- [ ] Struttura cartelle include `notes/_history/`

#### CONTRIBUTING.md
- [ ] Comandi test: `python -m pytest` e `python -m pytest -q`
- [ ] Comandi lint: `ruff check scripts/` e `ruff check scripts/ --fix`
- [ ] Menzione di `pyproject.toml` per configurazione

#### CHANGELOG.md
- [ ] Sezione `## [Unreleased]` presente e vuota dopo l'ultima release

### 3. Esecuzione fix

Per ogni problema trovato:
1. Leggi il file corrente con `read_file`
2. Applica la correzione con `replace_string_in_file` o `multi_replace_string_in_file`
3. Non aggiungere sezioni intere non richieste — correggi solo ciò che è sbagliato o mancante

### 4. Verifica finale

```powershell
# Controlla che ruff sia ancora green dopo le modifiche (per sicurezza)
python -m ruff check scripts/

# Controlla che i test passino
.venv\Scripts\python.exe -m pytest -q
```

### 5. Commit

```powershell
git add README.md AGENTS.md docs/ MeetWiki/README.md CONTRIBUTING.md CHANGELOG.md .github/skills/
git commit -m "docs: allinea documentazione al codice attuale"
```

## Note operative

- NON modificare `MeetWiki/topics/`, `MeetWiki/people/`, `MeetWiki/INDEX.md`,
  `MeetWiki/TAGS.md`, `MeetWiki/PEOPLE.md`, `MeetWiki/ACTIONS.md`,
  `MeetWiki/MY-KANBAN.md` — sono generati dagli script.
- NON toccare `MeetWiki/.meta/` salvo `schema.md`.
- Le skill `SKILL.md` sono editabili direttamente.
- `AGENTS.md` è la fonte di verità per le convenzioni agenti: tenerla sempre aggiornata.
