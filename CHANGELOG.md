# Changelog

Tutte le modifiche notevoli al progetto sono documentate qui.
Il formato segue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
e il progetto aderisce a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-29

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
