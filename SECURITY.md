# Security Policy

## Versioni supportate

Solo la versione piu' recente sul branch `main` riceve fix di sicurezza.
Vedere [CHANGELOG.md](CHANGELOG.md) per le versioni rilasciate.

## Segnalare una vulnerabilita'

**Non aprire una issue pubblica** se la segnalazione contiene PoC o dati sensibili.

Canali preferiti, in ordine:

1. **GitHub Security Advisory** privata su questo repository:
   `Security` -> `Report a vulnerability`.
2. Email al maintainer indicato nel campo `authors` di [pyproject.toml](pyproject.toml).

Includere nella segnalazione:

- Descrizione del problema e impatto stimato.
- Passi per riprodurre o PoC minimale.
- Versione/commit interessati.
- Eventuale fix proposto.

Risposta attesa entro 7 giorni lavorativi. Per fix critici l'obiettivo
e' una release patch entro 14 giorni dalla conferma.

## Scope

In scope:

- Esecuzione di codice non voluto via input controllabili (note Gemini,
  manifest, board Kanban, `actions_status.json`).
- Esposizione di credenziali (`GITHUB_MODELS_TOKEN`, cookie del profilo
  Chrome persistente in `scripts/chrome_profile/`).
- Manipolazione del manifest o dello stato action items che porti a
  perdita silenziosa di dati.
- CDP debug port esposto oltre `127.0.0.1`.

Out of scope:

- Vulnerabilita' che richiedono accesso fisico alla macchina dell'utente
  o privilegi amministrativi gia' ottenuti.
- Bug in Chrome o nei plugin Obsidian bundled (segnalarli ai progetti
  upstream).
- DoS che richiedano input volutamente malevoli generati dall'utente stesso.
- Funzionalita' non ancora rilasciate (`[Unreleased]` nel CHANGELOG).
