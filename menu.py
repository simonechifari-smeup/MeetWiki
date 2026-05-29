"""
MeetWiki — Menu interattivo
"""
import os
import sys
import subprocess
import msvcrt


def getch():
    """Legge un singolo tasto senza bisogno di premere INVIO."""
    ch = msvcrt.getwch()
    return ch.upper()

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
WHITE  = "\033[97m"

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
SCRIPTS = os.path.join(ROOT, "scripts")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    print(f"""
{CYAN}========================================================{RESET}
   {WHITE}{BOLD}M e e t W i k i{RESET}
               {DIM}...from Gemini Notes{RESET}
{CYAN}========================================================{RESET}
""")


def menu_items():
    return [
        ("1", "Scarica note da Gmail",           "download",  GREEN),
        ("2", "Aggiorna wiki (pipeline)",        "update",    GREEN),
        ("3", "Aggiorna wiki (force)",           "update_f",  GREEN),
        ("",  "",                                 "",          ""),
        ("4", "Ricerca semantica (ask)",         "ask",       CYAN),
        ("5", "Action items",                    "actions",   CYAN),
        ("6", "Kanban (sync + export)",          "kanban",    CYAN),
        ("",  "",                                 "",          ""),
        ("7", "Digest settimanale",              "digest_w",  YELLOW),
        ("8", "Digest mensile",                  "digest_m",  YELLOW),
        ("",  "",                                 "",          ""),
        ("O", "Apri Obsidian (vault wiki)",      "obsidian",  YELLOW),
        ("",  "",                                 "",          ""),
        ("S", "Setup...",                        "setup_sub", RED),
        ("",  "",                                 "",          ""),
        ("Q", "Esci",                            "quit",      RED),
    ]


def print_menu():
    items = menu_items()
    print(f"  {WHITE}Scegli un'opzione:{RESET}\n")
    for key, label, _, color in items:
        if not key:
            print()
            continue
        print(f"    {color}[{key}]{RESET}  {label}")
    print()


def setup_submenu():
    clear()
    banner()
    print(f"  {WHITE}Setup:{RESET}\n")
    print(f"    {RED}[1]{RESET}  Setup completo (venv + dipendenze)")
    print(f"    {RED}[2]{RESET}  Setup Obsidian (vault + plugin)")
    print(f"    {RED}[3]{RESET}  Schedulazione automatica")
    print()
    print(f"    {RED}[B]{RESET}  Indietro")
    print()

    print(f"  {BOLD}›{RESET} ", end="", flush=True)
    choice = getch()
    print(choice)

    if choice == "1":
        run_bat("setup.bat")
    elif choice == "2":
        run_bat("setup_obsidian.bat")
    elif choice == "3":
        run_bat("schedule_task.bat")
    elif choice == "B":
        return
    else:
        print(f"\n  {RED}Opzione non valida.{RESET}")


def run_script(script_name, *args):
    cmd = [PYTHON, os.path.join(SCRIPTS, script_name)] + list(args)
    print(f"\n  {DIM}> {' '.join(cmd)}{RESET}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def run_bat(bat_name):
    bat = os.path.join(SCRIPTS, bat_name)
    print(f"\n  {DIM}> {bat}{RESET}\n")
    result = subprocess.run(["cmd", "/c", bat], cwd=ROOT)
    return result.returncode


def handle_download():
    run_bat("..\\run.bat")


def handle_update():
    run_script("meetwiki_update.py")


def handle_update_force():
    run_script("meetwiki_update.py", "--force")


def handle_ask():
    query = input(f"  {WHITE}? Query:{RESET} ").strip()
    if query:
        run_script("meetwiki_ask.py", query)


def handle_actions():
    run_script("meetwiki_actions.py", "--list")


def handle_digest_weekly():
    run_script("meetwiki_digest.py")


def handle_digest_monthly():
    run_script("meetwiki_digest.py", "--period", "month")


def handle_kanban():
    run_script("meetwiki_kanban.py")


def handle_setup():
    run_bat("setup.bat")


def handle_setup_obs():
    run_bat("setup_obsidian.bat")


def handle_obsidian():
    vault = os.path.join(ROOT, "MeetWiki")
    uri = f"obsidian://open?path={vault.replace(os.sep, '/')}"
    os.startfile(uri)


ACTIONS = {
    "download":  handle_download,
    "update":    handle_update,
    "update_f":  handle_update_force,
    "ask":       handle_ask,
    "actions":   handle_actions,
    "digest_w":  handle_digest_weekly,
    "digest_m":  handle_digest_monthly,
    "kanban":    handle_kanban,
    "obsidian":  handle_obsidian,
    "setup_sub": setup_submenu,
}


def main():
    if os.name == "nt":
        os.system("")

    while True:
        clear()
        banner()
        print_menu()

        print(f"  {BOLD}›{RESET} ", end="", flush=True)
        choice = getch()
        print(choice)

        if choice == "Q":
            print(f"\n  {DIM}Arrivederci!{RESET}\n")
            break

        action_key = None
        for key, _, act, _ in menu_items():
            if key == choice:
                action_key = act
                break

        if action_key and action_key in ACTIONS:
            ACTIONS[action_key]()
            if action_key != "setup_sub":
                print(f"\n  {GREEN}Done.{RESET}")
                print(f"  {DIM}Premi un tasto per continuare...{RESET}", end="", flush=True)
                msvcrt.getwch()
        elif choice:
            print(f"\n  {RED}Opzione non valida.{RESET}")
            print(f"  {DIM}Premi un tasto per continuare...{RESET}", end="", flush=True)
            msvcrt.getwch()


if __name__ == "__main__":
    main()
