# Changelog

Tutte le modifiche notevoli al progetto sono documentate qui.
Il formato segue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
e il progetto aderisce a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-29

Squadra di fix sui finding della review interna: 14/15 chiusi (vedi
`docs/REVIEW_REPORT.md`). Solo `F10` resta aperto come scelta consapevole
e documentata (richiede ristrutturazione del layout in package).

### Added

- `scripts/meetwiki_common.py`: `atomic_write_text` (write `.tmp` + `os.replace`)
  e `validate_note_frontmatter` (campi obbligatori, formato data, tipi lista).
- `scripts/meetwiki_update.py`: lock globale della pipeline su
  `MeetWiki/.meta/.update.lock` (rilevamento stale lock > 1h, exit code 2
  se un'altra esecuzione e' gia' in corso) — F27.
- `scripts/meetwiki_ingest.py`: rilevamento conflitti su note canoniche
  modificate a mano via `generated_note_hash` nel manifest; in caso di
  conflitto scrive `.conflict.md` e salta l'update — F28.
- `scripts/meetwiki_actions.py`: parsing CLI via `argparse` (`--help`,
  `--list`) — F36.
- `SECURITY.md`: policy di disclosure (GitHub Security Advisory + email
  fallback, in/out of scope) — F37.
- `.github/workflows/ci.yml`: CI Windows con `ruff check` + `pytest` — F35.
- `tests/test_integration.py`: 7 test (validazione frontmatter, atomic
  write, end-to-end ingest). Totale ora 24/24 — F34.
- `.env.example`: documenta `CDP_PORT` e `MEETWIKI_KILL_CHROME` — F33.
- `MeetWiki/README.md`: sezione "Plugin Obsidian bundled" con versioni
  e origine dei plugin community versionati — F39.

### Changed

- Tutte le scritture markdown/json generate passano per
  `atomic_write_text` / `atomic_write_json` (ingest, summarize, index,
  digest, actions, ask, kanban) — F30.
- Tutti gli script che caricano frontmatter delle note validano via
  `validate_note_frontmatter` e saltano note malformate con WARN — F29.
- `scripts/gemini_notes_downloader.py`: la chiusura di Chrome e' ora
  opt-in via `MEETWIKI_KILL_CHROME=1` (prima killava sempre). In modalita'
  interattiva chiede conferma con default NO. Il restart Chrome nel
  `finally` avviene solo se abbiamo effettivamente killato — F03.
- `menu.py`: launch di Chrome forza `--remote-debugging-address=127.0.0.1`,
  `--user-data-dir=scripts/chrome_profile` e `--profile-directory=Default`
  allineando il menu alla stessa security posture del downloader — F32.
- README, `docs/usage.md`, `docs/setup.md`, `docs/faq.md`,
  `scripts/setup.bat`, `scripts/schedule_task.bat`: rimossi tutti i
  riferimenti a `run.bat` (rimosso intenzionalmente in `873f5b9`),
  sostituiti con `menu.cmd` o path Python diretto — F31.
- README: chiarito che `MeetWiki/` e' vault locale versionabile ma non
  parte del repo pubblico distribuito — F38.

### Security

- Riduzione esposizione CDP: anche il launch di Chrome dal menu
  interattivo e' ora vincolato a `127.0.0.1` (F32).
- Comportamento distruttivo della chiusura Chrome reso opt-in (F03).
- Aggiunta policy disclosure ufficiale `SECURITY.md` (F37).

### Known issues

- `F10` (open): pattern `sys.path.insert(0, ...)` + `# noqa: E402` in
  cima a ogni script `scripts/meetwiki_*.py`. Il fix richiede di
  pacchettizzare il codice (package `meetwiki/` con entry-point in
  `pyproject.toml`) e di aggiornare tutta la documentazione, le 10 skill
  e gli script bat. Rimandato a una release futura con un refactor
  dedicato (vedi `docs/REVIEW_REPORT.md#f10`).

Prima versione coerente con review interna completata (vedi `docs/REVIEW_REPORT.md`).

### Added

- Modulo `scripts/meetwiki_common.py` con utility condivise: `parse_frontmatter`,
  `extract_section`, `slugify`, `atomic_write_json`, `safe_load_json`.
- `pyproject.toml` con dipendenze, configurazione `ruff` e `pytest`.
- Suite di test pytest (`tests/test_pure_functions.py`) sulle funzioni pure.
- Flag `--dry-run` su `meetwiki_ingest.py` e `meetwiki_update.py`.
- Flag `--verbose` su `meetwiki_ingest.py` (log DEBUG, es. partecipanti scartati).
- Flag `--remote-debugging-address=127.0.0.1` esplicito nel downloader Gemini
  (riduce esposizione della porta CDP).
- `CONTRIBUTING.md` con setup, test, linting e checklist PR.
- Link dallo `MeetWiki/README.md` e `docs/architecture.md` a `MeetWiki/.meta/schema.md`.

### Changed

- Parsing CLI uniformato via `argparse` su `meetwiki_update`, `meetwiki_kanban`,
  `meetwiki_digest`, `meetwiki_ask`, `meetwiki_ingest`.
- `meetwiki_digest.py`: validazione `--date` con `date.fromisoformat`.
- `requirements.txt`: Playwright e python-dotenv passano da pin esatto a range
  compatibile (`>=1.44,<2.0`, `>=1.0,<2.0`).
- Downloader Gemini: il ripristino del profilo utente di Chrome avviene ora in
  un blocco `finally`, quindi anche su exception o early return.
- Downloader Gemini: sostituiti `except Exception: pass` silenziosi con
  `log.debug(...)` mirati.
- `meetwiki_kanban.py`: rimosso `sys.path.insert` ridondante.

### Documentation

- `MeetWiki/.meta/schema.md`: documentati limiti del parser regex YAML.

### Fixed

- Vari findings F01-F25 di `docs/REVIEW_REPORT.md`.

[Unreleased]: ./CHANGELOG.md
[0.1.0]: ./CHANGELOG.md
