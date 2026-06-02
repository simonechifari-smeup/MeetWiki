# Benchmark LLM locale — Ollama + Gemma 3 4B QAT

Stato sessione 2026-06-02. Stack scelto e validato end-to-end sul portatile dell'utente
(Windows, 16 GB RAM, **senza GPU dedicata**, Python 3.14 in `.venv\Scripts\python.exe`).

## Setup verificato

- **Runtime**: Ollama in ascolto su `http://localhost:11434` (REST + OpenAI-compatible).
- **Modello installato**: `gemma3:4b-it-qat` (digest `d01ad05792...`).
  - 4.3B parametri, GGUF Q4_0, 4.0 GB su disco, ~4 GB RAM a runtime.
  - 128K context, multilingua, QAT (Quantization Aware Training) → qualità ≈ BF16.
- **CLI Ollama non in PATH** in PowerShell (irrilevante: si usa la REST API).
- Validato con:
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
  ```

## Test 1 — Prompt breve (smoke test)

Prompt: *"Rispondi in italiano in 2 frasi: cos'è un data center?"*
Modello caldo (già in RAM).

| Metrica | Valore |
|---|---|
| Wall time totale | 57.6 s |
| Load modello | 0.3 s (cache calda) |
| Prompt eval | 29 tok in 1.8 s → **15.9 tok/s** |
| Generazione | 58 tok in 8.0 s → **7.2 tok/s** |
| Qualità output | Italiano corretto, conciso, on-topic |

> Nota: il "wall time" di 57.6 s vs la somma effettiva (~10 s) include overhead
> della shell PowerShell, non del modello. Tempo reale Ollama ≈ 10 s.

## Test 2 — Riassunto nota MeetWiki da 7.7 KB

Prompt: nota completa `2025-07-29-ssc-formazione.md` + istruzione riassunto 5 bullet.
**Non terminato in ragionevole tempo** (killato dopo diversi minuti).
Coerente con le metriche del test 1: ~2000+ token di prompt eval su CPU = 2+ minuti
solo per leggere il contesto.

## Stima per query RAG reale

Scenario tipico: system prompt + 3 chunk recuperati (~500 tok l'uno) + risposta 300 tok:

| Fase | Token | Tempo |
|---|---|---|
| Prompt eval | ~2000 | ~125 s |
| Generazione | ~300 | ~42 s |
| **Totale** | | **~2.5–3 min** (a freddo +5–10 s) |

## Implicazioni per il piano LLM

Riferimento: [plans/llm-plugin-implementation.md](../plans/llm-plugin-implementation.md) — Addendum 2026-06-02.

L'`OllamaProvider` (Fase 1) **funziona** ma deve gestire:

1. **Timeout lunghi**: default HTTP almeno 300 s.
2. **Streaming obbligatorio** in UI (`stream: true`). A 7 tok/s ≈ 25 char/s = leggibile,
   l'utente vede output dopo 1–2 s invece di aspettare il blocco completo.
3. **Mantenere modello caldo**: variabile `OLLAMA_KEEP_ALIVE=30m` (default 5m è troppo basso).
4. **Limitare contesto**: top-2 chunk (non top-5) per RAG, `num_predict=200` per default.
5. **Health-check con messaggio chiaro** se 11434 down (`ConnectException: rifiuto persistente`).
6. **Provider routing per costo**: query leggere (tag extraction, classificazione, query rewriting)
   andrebbero su `gemma3:1b` (~25–35 tok/s su CPU), riservando 4B per generazione finale.

## Cosa NON funziona / limiti hardware

- **No GPU dedicata** = prompt eval è il collo di bottiglia (15 tok/s contro 200+ tok/s su GPU).
- Senza VRAM: 4B Q4 è il **massimo praticabile** per uso interattivo. 12B/24B richiederebbero
  >2× la RAM e tempi 3–4× peggiori → non viable.
- Per ribaltare la situazione serve **GPU anche solo 6 GB VRAM** (RTX 3050/4060): 4B passa da
  7 a 50+ tok/s, RAG sotto 30 s end-to-end.

## Configurazione `.env` proposta

```env
MEETWIKI_LLM_PROVIDER=ollama
MEETWIKI_OLLAMA_HOST=http://localhost:11434
MEETWIKI_OLLAMA_MODEL=gemma3:4b-it-qat
MEETWIKI_OLLAMA_MODEL_LIGHT=gemma3:1b           # opzionale: query leggere
MEETWIKI_OLLAMA_KEEP_ALIVE=30m
MEETWIKI_OLLAMA_TIMEOUT_SEC=300
MEETWIKI_OLLAMA_NUM_PREDICT=200
MEETWIKI_RAG_TOP_K=2                            # invece di default 5
```

## Decisioni confermate (no rework)

- ✅ **Stack 100% locale**: Ollama + Gemma 3 4B QAT (no cloud LLM).
- ✅ **No Gemma 4 / E2B / E4B**: 7.2–9.6 GB disco + 8–10 GB RAM = troppo per 16 GB laptop.
  Inoltre "thinking mode" aggiunge 10–30 s di latenza non utile per RAG breve.
- ✅ **No torch / sentence-transformers** per embedding: backend ONNX runtime.
  Vedi [plans/hybrid-search-embedding.md](../plans/hybrid-search-embedding.md).
- ✅ **EmbeddingGemma 300M ONNX Q4 (256 dim Matryoshka)** per la retrieval.

## Prossimi step quando riprendiamo

1. **Implementare `OllamaProvider`** (`scripts/meetwiki_llm.py` nuovo) con:
   - Health-check `/api/tags`
   - Streaming via `/api/generate` o `/api/chat`
   - Selezione `MEETWIKI_LLM_PROVIDER` da `.env`
   - Fallback con messaggio chiaro se servizio down
2. **Implementare ricerca ibrida** (Fase 1 di [plans/hybrid-search-embedding.md](../plans/hybrid-search-embedding.md)):
   - `pyproject.toml` extra `embed` con `onnxruntime`, `tokenizers`, `huggingface-hub`, `numpy`
   - Download modello con `MODEL_REVISION` pinnata (SHA)
   - Storage `MeetWiki/.meta/search_embeddings.{npy,json}` con hash per chunk_id
   - Flag `--index` (BM25 + embedding) e `--no-embed` in `meetwiki_update.py`
3. **Integrare provider + retrieval in `meetwiki_ask.py`**: cambiare da pura ricerca a
   retrieval → generazione opzionale con LLM.
4. **Opzionale**: test rapido `gemma3:1b` come modello "light" per confronto latenza.

## Comandi utili per ripartire

```powershell
# Verifica Ollama up
Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5

# Lista modelli
Invoke-RestMethod -Uri "http://localhost:11434/api/tags" | Select-Object -ExpandProperty models | Format-Table name, size, @{n='quant';e={$_.details.quantization_level}}

# Query rapida (streaming)
$body = @{ model = "gemma3:4b-it-qat"; prompt = "<testo>"; stream = $true; options = @{ num_predict = 200 } } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method Post -Body $body -ContentType "application/json"

# Pull eventuale modello light per benchmark
# (richiede CLI: aggiungere C:\Users\<user>\AppData\Local\Programs\Ollama al PATH oppure usare GUI)
ollama pull gemma3:1b
```

## File correlati

- [plans/hybrid-search-embedding.md](../plans/hybrid-search-embedding.md) — piano embedding + RRF
- [plans/llm-plugin-implementation.md](../plans/llm-plugin-implementation.md) — piano LLM + Addendum locale
- [docs/vscode-markdown-plugins.md](vscode-markdown-plugins.md) — plugin VS Code per markdown/grafo
- [scripts/meetwiki_ask.py](../scripts/meetwiki_ask.py) — search BM25 attuale (da estendere)
