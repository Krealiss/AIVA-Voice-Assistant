import os
import glob
import sqlite3
import re
import winreg
import sys

# --- КОНФІГУРАЦІЯ ---
DB_PATH = os.getenv("DB_PATH", "assistant.db")
BAD_WORDS = {
    "uninstall", "uninst", "setup", "update", "helper", "config", "install", 
    "redist", "framework", "vcredist", "dxsetup", "repair", "patch", "crash", 
    "handler", "report", "service", "daemon", "server", "tool", "agent"
}

def get_conn():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY,
            name TEXT,
            canonical_name TEXT,
            exe_path TEXT,
            source TEXT,
            score INTEGER
        );
        DELETE FROM apps; 
    """)
    con.commit()
    return con

def add_app(con, name, path, source, score):
    path = path.strip().strip('"')
    if "," in path and path.endswith("0"): path = path.split(",")[0].strip('"')

    n_low = name.lower()
    if any(w in n_low for w in BAD_WORDS): return
    if path.lower().endswith(('.txt', '.url', '.ico', '.dll')): return

    clean_name = re.sub(r"\s+", " ", name).strip()
    clean_name = re.sub(r"\((x64|x86|64-bit)\)", "", clean_name).strip()
    
    if len(clean_name) < 2: return

    try:
        con.execute(
            "INSERT INTO apps (name, canonical_name, exe_path, source, score) VALUES (?, ?, ?, ?, ?)",
            (clean_name, clean_name.lower(), path, source, score)
        )
    except sqlite3.Error:
        pass

# === 1. ГЛИБОКИЙ ПОШУК TELEGRAM ===
def scan_user_apps(con):
    print("[Essentials] Scanning user folders...")
    added = 0
    
    appdata_roaming = os.getenv('APPDATA')
    appdata_local = os.getenv('LOCALAPPDATA')
    
    # Список точних шляхів
    candidates = [
        (os.path.join(appdata_roaming, "Telegram Desktop", "Telegram.exe"), "Telegram"),
        (os.path.join(appdata_roaming, "Telegram", "Telegram.exe"), "Telegram"),
        (os.path.join(appdata_local, "Programs", "Microsoft VS Code", "Code.exe"), "Visual Studio Code"),
        (os.path.join(appdata_roaming, "Spotify", "Spotify.exe"), "Spotify"),
    ]

    # Додаємо Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    for cp in chrome_paths:
        candidates.append((cp, "Google Chrome"))

    for path, name in candidates:
        if os.path.exists(path):
            print(f"   -> Found: {name}")
            add_app(con, name, f'"{path}"', "manual", 200)
            added += 1

    # Рекурсивний пошук Telegram, якщо не знайшли
    cursor = con.execute("SELECT count(*) FROM apps WHERE canonical_name='telegram'")
    if cursor.fetchone()[0] == 0:
        print("   -> Searching Telegram recursively...")
        found_tg = []
        # Шукаємо в Local та Roaming
        for root_dir in [appdata_roaming, appdata_local]:
            if not root_dir: continue
            # Шукаємо файл Telegram.exe, але не глибше 4 рівнів, щоб не зависнути
            for root, dirs, files in os.walk(root_dir):
                # Оптимізація: не заходимо в системні папки
                if "Temp" in root or "Cache" in root: continue
                
                if "Telegram.exe" in files:
                    full_path = os.path.join(root, "Telegram.exe")
                    if "Uninst" not in full_path:
                        found_tg.append(full_path)
                        break # Знайшли один - досить

        if found_tg:
            print(f"   -> FOUND Telegram at: {found_tg[0]}")
            add_app(con, "Telegram", f'"{found_tg[0]}"', "manual", 200)
            added += 1

    return added

# === 2. STEAM ===
def get_steam_install_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        path = winreg.QueryValueEx(key, "SteamPath")[0]
        return path.replace("/", "\\")
    except:
        candidates = [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
        for c in candidates:
            if os.path.exists(c): return c
    return None

def scan_steam_games(con):
    steam_root = get_steam_install_path()
    if not steam_root:
        print("[Steam] Not found.")
        return 0

    print(f"[Steam] Root: {steam_root}")
    if os.path.exists(os.path.join(steam_root, "steam.exe")):
        add_app(con, "Steam", f'"{os.path.join(steam_root, "steam.exe")}"', "manual", 200)
    
    library_paths = [steam_root]
    vdf_path = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    
    if os.path.exists(vdf_path):
        try:
            with open(vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
                found = re.findall(r'"path"\s+"(.*?)"', content, re.IGNORECASE)
                for p in found:
                    clean_p = p.replace("\\\\", "\\")
                    if clean_p.lower() != steam_root.lower():
                        library_paths.append(clean_p)
        except: pass

    added = 0
    for lib in library_paths:
        apps_dir = os.path.join(lib, "steamapps")
        if not os.path.exists(apps_dir): continue
        
        for acf in glob.glob(os.path.join(apps_dir, "appmanifest_*.acf")):
            try:
                with open(acf, 'r', encoding='utf-8', errors='ignore') as f:
                    data = f.read()
                    name_match = re.search(r'"name"\s+"(.*?)"', data)
                    id_match = re.search(r'"appid"\s+"(\d+)"', data)
                    
                    if name_match and id_match:
                        name = name_match.group(1)
                        app_id = id_match.group(1)
                        if "Common Redist" in name or "Steamworks" in name: continue
                        
                        # ВАЖЛИВО: Просто посилання, без explorer.exe
                        cmd = f"steam://rungameid/{app_id}"
                        add_app(con, name, cmd, "steam_game", 100)
                        added += 1
            except: pass
    return added

# === 3. START MENU ===
def scan_start_menu(con):
    print("[StartMenu] Scanning...")
    try:
        import winshell
    except: return 0
    
    start_dirs = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
    ]
    
    added = 0
    for base in start_dirs:
        if not os.path.exists(base): continue
        for lnk in glob.glob(os.path.join(base, "**", "*.lnk"), recursive=True):
            try:
                shortcut = winshell.Shortcut(lnk)
                target = shortcut.path
                name = os.path.splitext(os.path.basename(lnk))[0]
                
                if target and os.path.exists(target) and target.endswith('.exe'):
                    if "install" not in name.lower() and "setup" not in name.lower():
                        add_app(con, name, f'"{target}"', "start_menu", 80)
                        added += 1
            except: continue
    return added

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass
    
    con = get_conn()
    n_user = scan_user_apps(con)
    n_steam = scan_steam_games(con)
    n_start = scan_start_menu(con)
    
    con.execute("DELETE FROM apps WHERE id NOT IN (SELECT MAX(id) FROM apps GROUP BY canonical_name)")
    con.commit()
    
    print(f"Done! Apps: User={n_user}, Steam={n_steam}, StartMenu={n_start}")
    con.close()

if __name__ == "__main__":
    main()