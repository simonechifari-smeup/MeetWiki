# 📚 MeetWiki (From Gemini Notes)

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.44-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Obsidian](https://img.shields.io/badge/Obsidian-Vault-7C3AED?logo=obsidian&logoColor=white)](https://obsidian.md/)
[![Kanban](https://img.shields.io/badge/Kanban-Board-FF6B6B?logo=trello&logoColor=white)](https://github.com/mgmeyers/obsidian-kanban)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](#)

> Trasforma le note di riunione da Gemini in una **wiki strutturata e intelligente**, pronta per ricerca semantica e integrazione con AI.

Importa automaticamente le riunioni da Gmail, le organizza in una knowledge base interconnessa e offre ricerca semantica, action tracking e Kanban personali—il tutto integrato in Obsidian.

---

## 🚀 Quick Start

```powershell
# 1. Setup iniziale (eseguire una sola volta)
scripts\setup.bat

# 2. Configura il file .env (copia da .env.example)
cp .env.example .env
# Modifica .env con i tuoi valori:
#   OUTPUT_DIR       → percorso cartella note_riunioni
#   MEETWIKI_OWNER   → il tuo nome (per la board Kanban personale)

# 3. Scarica le note da Gmail
run.bat

# 4. Aggiorna la wiki
.venv\Scripts\python.exe scripts\meetwiki_update.py
```

| Variabile | Descrizione | Obbligatoria |
|-----------|-------------|:------------:|
| `OUTPUT_DIR` | Percorso dove salvare le note scaricate | ✅ |
| `MEETWIKI_OWNER` | Nome owner per la board Kanban personale | No |
| `GITHUB_MODELS_TOKEN` | Token GitHub per Obsidian Copilot | No |

---

## 🖥️ Menu interattivo

Lancia `menu.cmd` dalla root per accedere a tutte le funzioni con un solo tasto:

<p align="center">
  <img src="docs/menu-preview.svg?v=2" alt="Menu MeetWiki" width="580"/>
</p>

---

## ✨ Funzionalità principali

- **📥 Sincronizzazione Gmail** — Importa automaticamente le note di riunione da Gemini
- **🗂️ Wiki strutturata** — Organizzazione intelligente per data, partecipante, tag e tema
- **🔍 Ricerca semantica** — Trova decisioni e action items con query in linguaggio naturale
- **📋 Action Tracking** — Monitora task e responsabilità con Kanban personali
- **🧠 Pronta per LLM** — Frontmatter YAML e link relativi per integrazione AI
- **📊 Digest automatici** — Sintesi settimanali e mensili delle riunioni
- **🔗 Obsidian Vault** — Gestisci task in Kanban, integrato nel vault versionato

---

## 📖 Come cominciare

### Documentazione completa
- **[docs/](docs/README.md)** — Guida completa: setup, utilizzo, architettura e FAQ
- **[docs/setup.md](docs/setup.md)** — Installazione e configurazione
- **[docs/usage.md](docs/usage.md)** — Comandi e workflow quotidiano
- **[docs/architecture.md](docs/architecture.md)** — Diagrammi e scelte progettuali
- **[docs/faq.md](docs/faq.md)** — Troubleshooting e domande frequenti

### Riferimenti interni
- **[AGENTS.md](AGENTS.md)** — Istruzioni per AI agents e convenzioni progettuali
- **[MeetWiki/README.md](MeetWiki/README.md)** — Struttura della wiki e setup Obsidian
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — Integrazione con Copilot

### Con Obsidian
La cartella `MeetWiki/` è un vault Obsidian completo con il plugin `obsidian-kanban` bundled. Apri il vault, abilita i community plugins e gestisci i tuoi task in `MY-KANBAN.md`.

---

## 📋 Standard & Best Practices

Questo progetto segue le **best practices per Obsidian vault** e **gestione della knowledge base LLM-ready**:

### Obsidian Vault
- ✅ **`.obsidian/` versionata** — Configurazione consistente per tutti gli utenti
- ✅ **Plugin bundled** — `obsidian-kanban` (mgmeyers) e `dataview` inclusi e pre-configurati
- ✅ **Link relativi** — Compatibilità massima tra desktop e sistemi remoti
- ✅ **Frontmatter YAML** — Metadati strutturati per interoperabilità
- ✅ **Zero configurazione manuale** — Funziona out-of-the-box su qualsiasi macchina

### Knowledge Base
- ✅ **Partizionamento temporale** — Note organizzate per mese della riunione
- ✅ **Tagging semantico** — Tag curati e gestiti centralmente (non dinamici)
- ✅ **Pagine aggregate** — Sintesi tematiche generate automaticamente
- ✅ **History tracking** — Backup automatici in `_history/` per audit trail
- ✅ **BM25 search** — Indice semantico per query in linguaggio naturale

### Riferimenti
- 📖 [Obsidian Best Practices Guide](https://obsidian.md/)
- 📖 [Dataview Documentation](https://blacksmithgu.github.io/obsidian-dataview/)
- 📖 [Kanban Plugin](https://github.com/mgmeyers/obsidian-kanban)
- 📖 [YAML Frontmatter Standard](https://jekyllrb.com/docs/front-matter/)

## 🛠️ Stack tecnologico

- **Python 3.14** — Runtime principale
- **Playwright 1.44** — Automazione browser per Gmail
- **Obsidian + Kanban** — Gestione visiva dei task
- **Zero dipendenze YAML** — Parser regex custom per massima portabilità

---

## 📁 Struttura progetto

```
MeetWiki/
├── notes/              # Note di riunioni (partizionate per mese)
├── topics/             # Pagine aggregate per argomento
├── people/             # Profili per partecipante
├── digests/            # Sintesi settimanali/mensili
├── actions/            # Tracker action item e Kanban
├── .meta/              # Indici e metadati di configurazione
└── .obsidian/          # Vault Obsidian con plugin bundled

scripts/
├── meetwiki_update.py      # Pipeline completa (orchestratore)
├── meetwiki_ingest.py      # Importa note da Gmail
├── meetwiki_index.py       # Rigenera indici
├── meetwiki_search.py      # Ricerca per grep
├── meetwiki_ask.py         # Ricerca semantica (BM25)
└── ...
```


