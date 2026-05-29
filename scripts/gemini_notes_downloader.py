"""
Gemini Meeting Notes Downloader — versione Playwright (no Google Cloud)
=======================================================================
Usa il tuo Chrome gia loggato a Google per:
  1. Cercare in Gmail le email di Gemini con note riunione
  2. Estrarre i link ai documenti Google Docs
  3. Scaricare ogni documento in formato Markdown tramite URL di esportazione
  4. Salvare i file .md nella cartella OUTPUT_DIR

Lo script chiude Chrome se aperto, fa il lavoro, poi lo riapre.
"""

import os
import re
import json
import hashlib
import shutil
import logging
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
load_dotenv()

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOCALAPPDATA = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(_REPO_ROOT / "note_riunioni")))

# CHROME_USER_DATA non viene usato dal flusso attuale (lo script usa il profilo
# persistente dedicato in scripts/chrome_profile/), ma e' mantenuto per
# retro-compatibilita' se qualcuno lo importa dall'esterno.
CHROME_USER_DATA = Path(os.getenv(
    "CHROME_USER_DATA",
    str(_LOCALAPPDATA / "Google" / "Chrome" / "User Data"),
))
CHROME_PROFILE = os.getenv("CHROME_PROFILE", "Default")
CHROME_EXE = os.getenv(
    "CHROME_EXE",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)

PROCESSED_FILE = Path(__file__).resolve().parent.parent / ".cache" / "processed_emails.json"
SCANNED_FILE = Path(__file__).resolve().parent.parent / ".cache" / "scanned_emails.json"
PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)

# Query di ricerca Gmail (configurabile via .env)
GMAIL_SEARCH = os.getenv("GMAIL_SEARCH", "label:note-di-gemini")

DOCS_URL_PATTERN = re.compile(
    r'https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)'
)

# Pattern aggiuntivi per link che Gemini potrebbe usare
ALL_GOOGLE_LINKS_PATTERN = re.compile(
    r'https://(?:docs\.google\.com/document/d/|drive\.google\.com/(?:file/d/|open\?id=))([a-zA-Z0-9_-]+)'
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "downloader.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilita
# ---------------------------------------------------------------------------
def load_processed() -> set:
    if PROCESSED_FILE.exists():
        try:
            return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()


def save_processed(processed: set) -> None:
    PROCESSED_FILE.write_text(
        json.dumps(sorted(processed), indent=2), encoding="utf-8"
    )


def load_scanned() -> set:
    if SCANNED_FILE.exists():
        try:
            return set(json.loads(SCANNED_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()


def save_scanned(scanned: set) -> None:
    SCANNED_FILE.write_text(
        json.dumps(sorted(scanned), indent=2), encoding="utf-8"
    )


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def _decode_url_chain(url: str) -> str:
    """
    Decodifica ripetutamente un URL per estrarre la destinazione finale
    da catene di redirect (google.com/url?q=..., urlsand, ecc.).
    """
    from urllib.parse import unquote, urlparse, parse_qs
    prev = None
    current = url
    for _ in range(5):  # max 5 livelli di redirect
        if current == prev:
            break
        prev = current
        # Decodifica URL encoding
        decoded = unquote(current)
        # Cerca parametri q= u= url= nella query string
        try:
            parsed = urlparse(decoded)
            qs = parse_qs(parsed.query)
            for param in ('q', 'u', 'url'):
                if param in qs:
                    current = qs[param][0]
                    break
            else:
                current = decoded
        except Exception:
            current = decoded
    return current


def extract_doc_ids_from_hrefs(hrefs: list) -> list:
    """
    Da una lista di href (già decodificati dal browser),
    estrae gli ID Google Docs seguendo i redirect.
    """
    ids = []
    for href in hrefs:
        # Segui la catena di redirect
        final_url = _decode_url_chain(href)
        m = DOCS_URL_PATTERN.search(final_url)
        if m:
            ids.append(m.group(1))
        else:
            m2 = ALL_GOOGLE_LINKS_PATTERN.search(final_url)
            if m2:
                ids.append(m2.group(1))
    return list(dict.fromkeys(ids))


def _parse_date(date_str: str) -> str:
    for fmt in ("%d %b %Y", "%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Download tramite URL di esportazione Google Docs (nessuna API necessaria)
# ---------------------------------------------------------------------------
def download_doc_as_markdown(page, doc_id: str, download_dir: Path):
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=md"
    log.info("  Download: %s", export_url)
    try:
        with page.expect_download(timeout=30_000) as dl_info:
            try:
                page.goto(export_url)
            except Exception:
                # page.goto solleva "Download is starting" quando il server
                # risponde con Content-Disposition: attachment. E' atteso.
                pass
        download = dl_info.value
        tmp_path = download_dir / download.suggested_filename
        download.save_as(str(tmp_path))
        log.info("  Download OK: %s", tmp_path.name)
        return tmp_path
    except PWTimeout:
        log.error("  Timeout download doc %s", doc_id)
        return None
    except Exception as exc:
        log.error("  Errore download doc %s: %s", doc_id, exc)
        return None


def get_doc_title(page, doc_id: str) -> str:
    try:
        page.goto(
            f"https://docs.google.com/document/d/{doc_id}/edit",
            wait_until="domcontentloaded",
            timeout=20_000,
        )
        # Aspetta che document.title sia popolato (Docs lo aggiorna dopo il load)
        for _ in range(30):
            title = page.title() or ""
            # Esempio: "Mio Doc - Google Docs"
            if title and "Google Docs" in title:
                clean = title.rsplit(" - Google Docs", 1)[0].strip()
                if clean:
                    return clean
            page.wait_for_timeout(300)
        # Fallback: input value del titolo
        try:
            val = page.locator("input.docs-title-input").input_value(timeout=3000)
            if val:
                return val.strip()
        except Exception:
            pass
        return doc_id
    except Exception:
        return doc_id


# ---------------------------------------------------------------------------
# Lettura email via Gmail web
# ---------------------------------------------------------------------------
def get_email_items(page, processed: set) -> list:
    log.info("Avvio ricerca email con query: %s", GMAIL_SEARCH)

    # Vai alla inbox e usa la barra di ricerca
    page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="domcontentloaded", timeout=30_000)
    try:
        page.wait_for_selector("input[aria-label='Cerca nella posta'], input[name='q']", timeout=15_000)
    except PWTimeout:
        log.error("Barra di ricerca Gmail non trovata.")
        return []

    search_box = page.locator("input[aria-label='Cerca nella posta'], input[name='q']").first
    search_box.click()
    search_box.fill(GMAIL_SEARCH)
    search_box.press("Enter")

    # Aspetta che la navigazione SPA completi (networkidle oppure URL aggiornato)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PWTimeout:
        pass

    log.info("URL dopo ricerca: %s", page.url)

    # Porta la tab in primo piano (Gmail può pausare il rendering in background)
    try:
        page.bring_to_front()
    except Exception:
        pass

    # Selettore robusto: Gmail può usare tr.zA oppure tr[role='row'] dentro div[role='main']
    SEL = "div[role='main'] tr.zA, div[role='main'] tr[jsaction]"

    try:
        page.wait_for_selector(SEL, timeout=30_000)
    except PWTimeout:
        log.warning("Nessuna riga email trovata. URL corrente: %s", page.url)

        # Debug: conta i tr e salva uno screenshot
        try:
            tr_total = page.locator("tr").count()
            tr_za = page.locator("tr.zA").count()
            tr_row = page.locator("tr[role='row']").count()
            main_html_len = page.locator("div[role='main']").inner_html(timeout=3000)
            log.warning(
                "Debug DOM -> tr totali: %d | tr.zA: %d | tr[role=row]: %d | main html chars: %d",
                tr_total, tr_za, tr_row, len(main_html_len)
            )
        except Exception as exc:
            log.warning("Debug DOM fallito: %s", exc)

        try:
            shot = Path(__file__).parent / "debug_gmail.png"
            page.screenshot(path=str(shot), full_page=True)
            log.warning("Screenshot salvato: %s", shot)
        except Exception as exc:
            log.warning("Screenshot fallito: %s", exc)

        # Fallback: naviga direttamente all'URL di ricerca codificato
        encoded = GMAIL_SEARCH.replace(":", "%3A").replace(" ", "+")
        page.goto(
            f"https://mail.google.com/mail/u/0/#search/{encoded}",
            wait_until="domcontentloaded", timeout=20_000
        )
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PWTimeout:
            pass
        try:
            page.wait_for_selector(SEL, timeout=20_000)
        except PWTimeout:
            log.info("Nessuna email trovata con la query (dopo fallback URL).")
            return []

    page.wait_for_timeout(1500)
    search_page_url = page.url
    log.info("URL ricerca salvato: %s", search_page_url)

    # Raccoglie ID thread, oggetto e data SOLO dalle righe attualmente visibili.
    # Gmail mantiene nel DOM anche le righe della inbox precedente (nascoste con
    # display:none), quindi filtriamo via offsetParent.
    email_data = page.evaluate("""() => {
        const rows = Array.from(document.querySelectorAll('div[role="main"] tr.zA'));
        return rows
            .filter(r => r.offsetParent !== null)
            .map(row => {
                const dateEl = row.querySelector('td.xW span, span.xW span, span.xW');
                return {
                    thread_id: row.getAttribute('data-legacy-thread-id')
                               || row.getAttribute('data-legacy-last-message-id')
                               || row.getAttribute('id')
                               || '',
                    subject: (row.querySelector('span.bog') || {}).innerText || '',
                    date: dateEl ? (dateEl.getAttribute('title') || dateEl.innerText || '') : ''
                };
            });
    }""")

    log.info("Email nella lista filtrata: %d", len(email_data))

    def visible_rows():
        return page.locator("div[role='main'] tr.zA:visible")

    results = []
    n = len(email_data)
    scanned = load_scanned()
    for i, meta in enumerate(email_data):
        subject = meta.get("subject", f"email-{i}")
        date_str = meta.get("date", "")
        thread_id = meta.get("thread_id", "")

        # Usa thread_id stabile (FM...) come chiave, fallback su hash(subject|date)
        if thread_id.startswith("FM"):
            scan_key = thread_id
        else:
            scan_key = hashlib.sha256(f"{subject}|{date_str}".encode()).hexdigest()[:16]

        if scan_key in scanned:
            log.debug("Email %d/%d gia scansionata, salto.", i + 1, n)
            continue

        log.info("Apro email %d/%d: %s", i + 1, n, subject[:80])

        try:
            rows = visible_rows()
            if rows.count() <= i:
                log.warning("  Riga %d non piu disponibile, salto.", i)
                continue
            rows.nth(i).click()

            page.wait_for_selector(".a3s, .ii.gt", timeout=15_000)
            page.wait_for_timeout(400)

            hrefs = page.locator(".a3s a[href], .ii.gt a[href]").evaluate_all(
                "els => els.map(e => e.href)"
            )

            log.info("  href trovati: %d", len(hrefs))
            docs_hrefs = [h for h in hrefs if "docs.google.com" in h]
            if docs_hrefs:
                log.info("  href Docs: %s", docs_hrefs[:3])

            doc_ids = extract_doc_ids_from_hrefs(hrefs)

            # Filtra doc_id gia scaricati
            new_doc_ids = [d for d in doc_ids if d not in processed]
            if doc_ids and not new_doc_ids:
                log.info("  -> Tutti i doc_id gia scaricati, salto.")
            elif new_doc_ids:
                results.append({
                    "date": _parse_date(date_str) if date_str else datetime.now().strftime("%Y-%m-%d"),
                    "doc_ids": new_doc_ids,
                })
                log.info("  -> %d nuovi doc: %s", len(new_doc_ids), new_doc_ids)
            else:
                log.info("  -> Nessun link Docs.")

            # Segna email come scansionata
            scanned.add(scan_key)
            save_scanned(scanned)

        except Exception as exc:
            log.error("Errore email %d (%s): %s", i + 1, subject[:40], exc, exc_info=True)

        # Torna alla lista con go_back (Gmail SPA hash routing)
        try:
            page.go_back(wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_selector("div[role='main'] tr.zA:visible", timeout=15_000)
            page.wait_for_timeout(500)
        except Exception:
            try:
                page.goto(search_page_url, wait_until="domcontentloaded", timeout=20_000)
                page.wait_for_load_state("networkidle", timeout=10_000)
                page.wait_for_selector("div[role='main'] tr.zA:visible", timeout=15_000)
            except Exception as exc:
                log.error("Impossibile tornare alla lista: %s", exc)
                break

    return results


# ---------------------------------------------------------------------------
# Gestione Chrome
# ---------------------------------------------------------------------------
def _chrome_is_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH", "/FO", "CSV"],
        capture_output=True, text=True
    )
    return "chrome.exe" in result.stdout


def _kill_chrome() -> None:
    if not _chrome_is_running():
        return
    log.info("Chiusura Chrome in corso...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    for _ in range(30):
        time.sleep(0.5)
        if not _chrome_is_running():
            log.info("Chrome chiuso.")
            return
    log.warning("Alcuni processi Chrome potrebbero essere ancora attivi.")


# Cartella profilo persistente: viene creata una sola volta.
# Il login viene fatto manualmente al primo avvio e i cookie
# vengono mantenuti tra un'esecuzione e l'altra.
PERSISTENT_PROFILE_DIR = Path(__file__).parent / "chrome_profile"


def _prepare_profile() -> Path:
    """
    Usa una cartella profilo dedicata e persistente (chrome_profile/).
    Al primo avvio la crea vuota: Google salva il login lì e lo ritrova
    ad ogni esecuzione successiva senza chiedere password.
    NON copia il profilo Chrome esistente per evitare che Google
    rilevi i cookie come provenienti da un dispositivo diverso.
    """
    PERSISTENT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    # Rimuove i lock file lasciati da esecuzioni precedenti
    for lock_name in ("SingletonLock", "SingletonCookie", "lockfile"):
        for lock in PERSISTENT_PROFILE_DIR.rglob(lock_name):
            try:
                lock.unlink()
            except Exception:
                pass
    return PERSISTENT_PROFILE_DIR


def _wait_for_cdp(port: int, timeout: float = 15.0) -> bool:
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


CDP_PORT = int(os.getenv("CDP_PORT", "9222"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run() -> None:
    log.info("=== Avvio Gemini Notes Downloader (Playwright) ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    processed = load_processed()
    total_saved = 0

    chrome_was_running = _chrome_is_running()
    _kill_chrome()
    time.sleep(1)

    profile_dir = _prepare_profile()

    chrome_args = [
        CHROME_EXE,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={profile_dir}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-restore-session-state",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
    ]
    log.info("Avvio Chrome con debug port %d...", CDP_PORT)
    chrome_proc = subprocess.Popen(chrome_args)

    if not _wait_for_cdp(CDP_PORT):
        log.error("Chrome non ha risposto sulla porta %d entro 15 secondi.", CDP_PORT)
        chrome_proc.terminate()
        return
    log.info("Chrome pronto.")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
        except Exception as exc:
            log.error("Connessione CDP fallita: %s", exc)
            chrome_proc.terminate()
            return

        context = browser.contexts[0] if browser.contexts else browser.new_context(
            accept_downloads=True, downloads_path=str(OUTPUT_DIR)
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # Naviga su Gmail e aspetta che sia completamente caricato.
            # Se l'utente deve fare il login, aspettiamo fino a 5 minuti.
            log.info("Apertura Gmail — se richiesto, esegui il login nel browser...")
            page.goto(
                "https://mail.google.com/mail/u/0/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )

            # Aspetta fino a 5 minuti: o vediamo la inbox Gmail oppure la pagina di login si risolve
            try:
                page.wait_for_selector(
                    "div[role='main'], div.AO, .T-I.T-I-KE",  # inbox o compose button
                    timeout=300_000,  # 5 minuti
                )
                log.info("Gmail caricato correttamente.")
            except PWTimeout:
                log.error("Gmail non si e' caricato entro 5 minuti. Interruzione.")
                return

            log.info("Ricerca email in corso...")
            emails = get_email_items(page, processed)
            log.info("Lettura email completata.")

            if not emails:
                log.info("Nessuna nuova email da processare.")
                save_processed(processed)
            else:
                # Raccogli nomi file gia presenti (inbox + archive) per dedup aggiuntiva
                existing_files = {f.stem for f in OUTPUT_DIR.glob("*.md")}
                archive_dir = OUTPUT_DIR / "archive"
                if archive_dir.exists():
                    existing_files |= {f.stem for f in archive_dir.rglob("*.md")}

                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)

                    for item in emails:
                        date_prefix = item["date"]
                        doc_ids = item["doc_ids"]

                        for doc_id in doc_ids:
                            title = get_doc_title(page, doc_id)
                            log.info("  Titolo: %s", title)

                            base_name = sanitize_filename(f"{date_prefix} - {title}")
                            # Skip se file gia presente
                            if base_name in existing_files:
                                log.info("  -> Gia scaricato: %s, salto.", base_name)
                                processed.add(doc_id)
                                save_processed(processed)
                                continue

                            downloaded = download_doc_as_markdown(page, doc_id, tmp_path)
                            if not downloaded:
                                continue

                            dest = OUTPUT_DIR / (base_name + ".md")
                            counter = 1
                            while dest.exists():
                                dest = OUTPUT_DIR / f"{base_name} ({counter}).md"
                                counter += 1

                            shutil.move(str(downloaded), str(dest))
                            log.info("  Salvato: %s", dest)
                            total_saved += 1
                            processed.add(doc_id)
                            save_processed(processed)

        finally:
            page.close()
            # Chiudi Chrome in modo pulito via CDP
            try:
                cdp = browser.new_browser_cdp_session()
                cdp.send("Browser.close")
            except Exception:
                pass
            browser.close()

    try:
        chrome_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        chrome_proc.terminate()
        chrome_proc.wait(timeout=5)

    log.info("=== Completato. File salvati: %d ===", total_saved)

    if chrome_was_running:
        log.info("Riapertura Chrome...")
        subprocess.Popen([CHROME_EXE, f"--profile-directory={CHROME_PROFILE}"])


if __name__ == "__main__":
    run()