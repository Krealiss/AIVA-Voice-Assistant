import os
import re
import logging
import subprocess
import time
import urllib.parse
import webbrowser
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import inspect

# --- FIX: Pymorphy2 compatibility for Python 3.10+ ---
if not hasattr(inspect, 'getargspec'):
    def getargspec_stub(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = getargspec_stub

import pymorphy2

# --- 1. ВАЖЛИВО: Імпортуємо конфіг першим ---
import config

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rapidfuzz import process, fuzz

# --- 2. Імпорт модулів ---
from asr_whisper import transcribe_wav_custom, warmup as asr_warmup
from listener import AivaListener
from ai_brain import brain

# === Logging ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("agent")

# Optional imports з fallback
try:
    from tts_module import speak
except ImportError:
    logger.warning("TTS module not available")
    def speak(text): pass

try:
    from smart_home import home
except ImportError:
    logger.warning("Smart home module not available")
    home = None

from system_control import sys_ctrl
from weather import weather
from db_manager import DatabaseManager
from dashboard_api import router as dashboard_router
from websocket_manager import manager as ws_manager, websocket_endpoint

# Learning systems (optional imports)
try:
    from learning_api import router as learning_router
    from analytics_engine import analytics, CommandMetric
    from habit_learner import habit_learner
    from feedback_system import feedback_system
    LEARNING_ENABLED = True
except ImportError as e:
    logger.warning(f"Learning systems not available: {e}")
    LEARNING_ENABLED = False

# Vision system (optional import)
try:
    from vision_api import router as vision_router
    VISION_ENABLED = True
except ImportError as e:
    logger.warning(f"Vision system not available: {e}")
    VISION_ENABLED = False

# Context & User Profile system
try:
    from context_api import router as context_router, user_router
    CONTEXT_ENABLED = True
except ImportError as e:
    logger.warning(f"Context system not available: {e}")
    CONTEXT_ENABLED = False

# NLU Engine (Hybrid intent recognition)
try:
    from nlu_engine import nlu_engine, IntentResult
    NLU_ENABLED = True
    logger.info("NLU Engine enabled (Hybrid mode)")
except ImportError as e:
    logger.warning(f"NLU Engine not available: {e}")
    NLU_ENABLED = False

DB_PATH = config.DB_PATH
VERSION = "2.1.0 (Hybrid NLU Edition)"

# Ініціалізація оптимізованого менеджера БД
db_manager = DatabaseManager(DB_PATH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # [STARTUP LOGIC]
    asr_warmup()
    global_listener.start()
    logger.info("AIVA System Ready.")
    yield
    # [SHUTDOWN LOGIC]
    global_listener.stop()

app = FastAPI(title="AIVA Server", lifespan=lifespan)
morph = pymorphy2.MorphAnalyzer(lang='uk')

# Middleware для закриття з'єднань БД після кожного запиту
@app.middleware("http")
async def close_db_connections(request, call_next):
    response = await call_next(request)
    # Закриваємо з'єднання в db_manager
    try:
        db_manager.close()
    except Exception as e:
        logger.debug(f"Error closing db_manager connection: {e}")
    return response

# Підключаємо статичні файли
app.mount("/static", StaticFiles(directory="static"), name="static")

# Підключаємо dashboard API
app.include_router(dashboard_router)

# Підключаємо learning API
if LEARNING_ENABLED:
    app.include_router(learning_router)

# Підключаємо vision API
if VISION_ENABLED:
    app.include_router(vision_router)

# Підключаємо context & user profile API
if CONTEXT_ENABLED:
    app.include_router(context_router)
    app.include_router(user_router)

# === СИНОНІМИ (Додано нове) ===
APP_ALIASES_MAP = {
    "google chrome": ["хром", "гугл", "браузер", "internet"],
    "steam": ["стім", "стим", "valve"],
    "telegram": ["тг", "тєлєгу", "телега", "messanger"],
    "visual studio code": ["код", "віжуал", "вс код", "студіо"], 
    "counter-strike 2": ["кс", "контра", "кс 2", "кс го", "csgo", "cs 2"], 
    "dota 2": ["дота", "доту"], 
    "spotify": ["спотіфай", "музика", "спотік"],
    "discord": ["діскорд", "діс", "дс"],
}

# ---------- DB / APPS ----------
def db_counts() -> Dict:
    return db_manager.get_counts()

def load_apps() -> List[Tuple[str, str]]:
    return db_manager.load_apps()

def get_exe_by_canonical(canon: str) -> Optional[Tuple[str, str]]:
    return db_manager.get_exe_by_canonical(canon)

def fuzzy_find(query: str, items: List[Tuple[str, str]]) -> Optional[Tuple[str, str, float]]:
    if not items: return None
    names = [n for n, _ in items]
    
    # ЗМІНА: Використовуємо extractOne з QRatio (швидке порівняння) замість WRatio.
    # WRatio занадто "м'який" і плутає "dota 2" і "cs 2" через спільну цифру 2.
    match = process.extractOne(query, names, scorer=fuzz.QRatio, score_cutoff=60)
    
    # Додаткова перевірка: якщо це коротке слово (менше 5 літер), вимагаємо вищу точність
    if match:
        name, score, idx = match
        if len(query) < 5 and score < 85:
            return None
            
        exe = items[idx][1]
        return name, exe, float(score)
        
    return None

def launch_path(exe_path: str) -> Tuple[bool, str]:
    """
    Розумний запуск: файли, посилання, Steam.
    Виправлено помилку 'explorer.exe not found'.
    """
    exe_path = exe_path.strip()
    
    try:
        # 1. Steam протокол (через os.startfile)
        if "steam://" in exe_path:
            clean_url = exe_path.replace("explorer.exe", "").strip()
            clean_url = clean_url.replace('"', '') 
            logger.info(f"🚀 Launching Steam URL: {clean_url}")
            os.startfile(clean_url) 
            return True, "Запускаю гру..."

        # 2. Звичайний файл
        clean_path = exe_path.replace('"', '')
        if os.path.exists(clean_path):
            logger.info(f"📂 Opening file: {clean_path}")
            os.startfile(clean_path)
            return True, f"Запускаю: {os.path.basename(clean_path)}"
        
        # 3. Фолбек (системні команди)
        subprocess.Popen(exe_path, shell=True)
        return True, "Спроба запуску..."

    except Exception as e:
        logger.error(f"Launch error: {e}")
        return False, f"Помилка запуску: {str(e)}"

# ---------- NLP Helpers ----------
def clean_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("’", "'")
    s = re.sub(r"[.,!?;:–—…]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def cleanup_search_query(q: str) -> str:
    s = q.strip()
    s = re.sub(r"[.,!?;:–—…\s]+$", "", s)
    s = re.sub(r"([A-Za-z]+)[\u0400-\u04FF]+", r"\1", s)
    return s

def is_word_close(word: str, candidates: List[str], cutoff: int = 75) -> Optional[str]:
    if not word: return None
    match = process.extractOne(word, candidates, scorer=fuzz.QRatio, score_cutoff=cutoff)
    return match[0] if match else None

def normalize_aliases(text: str) -> str:
    """Замінює сленг на офіційні назви"""
    text = clean_text(text)
    for real_name, aliases in APP_ALIASES_MAP.items():
        for alias in aliases:
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, text):
                text = re.sub(pattern, real_name, text)
    return text

def detect_app_by_synonyms(t: str) -> Optional[str]:
    # Ця функція тепер допоміжна, основна робота в normalize_aliases
    for canon, variants in APP_ALIASES_MAP.items():
        for v in variants:
            if re.search(rf"\b{re.escape(v)}\b", t):
                return canon
    return None

def build_initial_prompt_from_db(db_path: str = DB_PATH) -> str:
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        rows = cur.execute(
            "SELECT DISTINCT canonical_name FROM apps WHERE score > 50 LIMIT 80"
        ).fetchall()
        con.close()
        apps = ", ".join(r[0] for r in rows) if rows else "chrome, steam, telegram"
    except Exception:
        apps = "chrome, steam, telegram"
    return f"команди: запусти, знайди; програми: {apps}."

def extract_number(text: str, default: int = 50) -> int:
    nums = re.findall(r'\d+', text)
    if nums: return int(nums[0])
    return default

# ---------- Intents ----------
INTENT_MAP = {
    "run": ["запусти", "відкрий", "стартуй", "run", "open", "play", "грати"],
    "find": ["знайди", "пошукай", "find", "search"],
    "control_on": ["увімкни", "включи", "засвіти", "on"],
    "control_off": ["вимкни", "виключи", "погаси", "off"],
    "vol_set": ["гучність", "звук", "volume"],
    "vol_up": ["гучніше", "голосніше", "up"],
    "vol_down": ["тихіше", "зменш", "down"],
    "mute": ["без звуку", "мут", "mute"],
    "pc_off": ["вимкни комп'ютер", "вируби пк", "shutdown"],
    "pc_cancel": ["скасувати", "відміни", "стоп", "cancel"],
    "weather_now": ["погода", "температура"],
    "weather_forecast": ["прогноз"],
    "screenshot": ["скріншот", "знімок", "screenshot", "зроби фото", "сфоткай"],
    "describe_screen": ["опиши екран", "що бачиш", "describe screen", "аналізуй екран", "що на екрані"],
    "find_element": ["знайди на екрані", "де знаходиться", "find element", "шукай елемент"],
    "detect_errors": ["є помилки", "перевір помилки", "check errors", "помилки на екрані"],
    "read_text": ["прочитай текст", "що написано", "read text", "ocr", "розпізнай текст"]
}

PC_SYNONYMS = ["комп'ютер", "комп", "пк", "pc", "ноутбук"]

def save_response_to_context(session_id: str, response_text: str):
    """Зберігає відповідь системи в контекст"""
    if CONTEXT_ENABLED:
        try:
            from context_manager import context_manager
            context_manager.add_message(session_id, "assistant", response_text)
        except Exception as e:
            logger.debug(f"Failed to save response to context: {e}")

def handle_intent(text: str, source: str = "voice", user_id: str = "default") -> Optional[Dict]:
    start_time = time.time()

    if not text or not text.strip():
        return None

    # Отримуємо або створюємо сесію для користувача
    if CONTEXT_ENABLED:
        from context_manager import context_manager
        session = context_manager.get_active_session(user_id)
        session_id = session.session_id
    else:
        session_id = f"session_{user_id}"

    # === HYBRID NLU АНАЛІЗ ===
    if NLU_ENABLED:
        # Використовуємо новий NLU engine з session_id для контексту
        nlu_result = nlu_engine.analyze(text, session_id=session_id, context={
            "source": source,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })

        verb_type = nlu_result.intent
        entities = nlu_result.entities
        confidence = nlu_result.confidence
        arg = entities.get("query", "")

        logger.info(
            f"🔍 NLU: intent={verb_type}, confidence={confidence:.2f}, "
            f"method={nlu_result.method}, entities={entities}"
        )

        # Зберігаємо команду в контекст
        if CONTEXT_ENABLED:
            context_manager.add_message(
                session_id, "user", text,
                intent=verb_type, entities=entities, confidence=confidence
            )

        # Якщо низька впевненість -> fallback на AI
        if confidence < 0.5 or verb_type == "unknown":
            logger.info(f"🤔 Low confidence ({confidence:.2f}). Asking AI Brain...")
            ai_response = brain.ask(text)

            # Зберігаємо відповідь AI
            if CONTEXT_ENABLED:
                context_manager.add_message(session_id, "assistant", ai_response)

            return {"ok": True, "text": ai_response, "details": {"source": "ai_brain"}}

    else:
        # Fallback на стару логіку якщо NLU недоступний
        tl = normalize_aliases(text)
        if not tl: return None
        words = tl.split()

        best_score = 0
        verb_type = None
        verb_idx = 0

        for i, w in enumerate(words[:3]):
            for intent_name, keywords in INTENT_MAP.items():
                match = process.extractOne(w, keywords, scorer=fuzz.QRatio)
                if match:
                    _, score, _ = match
                    if score > 75 and score > best_score:
                        best_score = score
                        verb_type = intent_name
                        verb_idx = i

        logger.info(f"🔍 Intent Analysis (fallback): Type='{verb_type}' (Score: {best_score})")

        items = load_apps()

        if verb_type is None:
            fz = fuzzy_find(tl, items)
            if fz and fz[2] > 88:
                ok, msg = launch_path(fz[1])
                return {"ok": ok, "text": msg, "details": {"name": fz[0]}}
            logger.info(f"🤔 Unknown command '{text}'. Asking AI Brain...")
            ai_response = brain.ask(text)
            return {"ok": True, "text": ai_response, "details": {"source": "ai_brain"}}

        arg = " ".join(words[verb_idx + 1:]).strip()
        entities = {}  # Порожні entities для fallback режиму

    items = load_apps()

    # СИСТЕМНІ
    if verb_type == "vol_set":
        lvl = entities.get("volume", -1)
        response_text = sys_ctrl.set_volume(lvl) if lvl >= 0 else "На скільки?"
        save_response_to_context(session_id, response_text)
        return {"ok": True, "text": response_text}

    if verb_type == "vol_up":
        response_text = sys_ctrl.change_volume(10)
        save_response_to_context(session_id, response_text)
        return {"ok": True, "text": response_text}

    if verb_type == "vol_down":
        response_text = sys_ctrl.change_volume(-10)
        save_response_to_context(session_id, response_text)
        return {"ok": True, "text": response_text}

    if verb_type == "mute":
        response_text = sys_ctrl.mute_toggle()
        save_response_to_context(session_id, response_text)
        return {"ok": True, "text": response_text}

    if verb_type == "pc_off":
        response_text = sys_ctrl.pc_shutdown()
        save_response_to_context(session_id, response_text)
        return {"ok": True, "text": response_text}

    if verb_type == "pc_cancel":
        response_text = sys_ctrl.pc_cancel_shutdown()
        save_response_to_context(session_id, response_text)
        return {"ok": True, "text": response_text}

    # РОЗУМНИЙ ДІМ
    if verb_type in ["control_on", "control_off"]:
        action = entities.get("action", "on" if verb_type == "control_on" else "off")
        device = entities.get("device", "")

        # Захист від випадкового вимкнення ПК
        if action == "off" and any(fuzz.QRatio(device, pc) > 80 for pc in PC_SYNONYMS):
            response_text = sys_ctrl.pc_shutdown()
            save_response_to_context(session_id, response_text)
            return {"ok": True, "text": response_text}

        msg = home.control(device, action)
        save_response_to_context(session_id, msg)
        return {"ok": True, "text": msg, "details": {"source": "smart_home"}}

    # ЗАПУСК ПРОГРАМ
    if verb_type == "run":
        app_name = entities.get("app")

        if app_name:
            # Спочатку перевіряємо точний збіг
            if app_name in APP_ALIASES_MAP:
                exact = get_exe_by_canonical(app_name)
                if exact:
                    ok, msg = launch_path(exact[1])
                    return {"ok": ok, "text": msg}

            # Fuzzy matching з БД
            if items:
                fz = fuzzy_find(app_name, items)
                if fz:
                    name, exe, score = fz
                    logger.info(f"🎯 Fuzzy match: {app_name} -> {name} ({score}%)")
                    ok, msg = launch_path(exe)
                    return {"ok": ok, "text": f"{msg} ({name})"}

        # Fallback на AI
        ai_ans = brain.ask(text)
        return {"ok": True, "text": ai_ans}

    # ПОШУК
    if verb_type == "find":
        query = entities.get("query", text)
        q = cleanup_search_query(query)
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}")
        return {"ok": True, "text": f"Шукаю: {q}"}

    # ПОГОДА
    if verb_type in ["weather_now", "weather_forecast"]:
        city = entities.get("city")
        is_future = entities.get("when") == "forecast" or verb_type == "weather_forecast"
        report = weather.get_forecast(city) if is_future else weather.get_weather(city)
        return {"ok": True, "text": report, "details": {"source": "weather"}}

    # VISION COMMANDS
    if verb_type == "screenshot":
        if VISION_ENABLED:
            from vision_module import vision
            screenshot_path = vision.capture_screenshot()
            if screenshot_path:
                return {"ok": True, "text": f"Скріншот збережено: {screenshot_path}"}
            else:
                return {"ok": False, "text": "Не вдалося зробити скріншот"}
        else:
            return {"ok": False, "text": "Vision система не активна"}

    if verb_type == "describe_screen":
        if VISION_ENABLED:
            from vision_module import vision
            result = vision.describe_screen(prompt=arg if arg else None)
            if result.get("ok"):
                description = result.get("description", "Не вдалося проаналізувати")
                return {"ok": True, "text": f"На екрані: {description}"}
            else:
                return {"ok": False, "text": "Не вдалося проаналізувати екран"}
        else:
            return {"ok": False, "text": "Vision система не активна"}

    if verb_type == "find_element":
        if VISION_ENABLED and arg:
            from vision_module import vision
            result = vision.find_ui_element(arg)
            if result.get("ok"):
                found = result.get("found", "Не знайдено")
                return {"ok": True, "text": f"Результат пошуку: {found}"}
            else:
                return {"ok": False, "text": "Не вдалося знайти елемент"}
        else:
            return {"ok": False, "text": "Вкажи що шукати"}

    if verb_type == "detect_errors":
        if VISION_ENABLED:
            from vision_module import vision
            result = vision.detect_errors()
            if result.get("ok"):
                if result.get("has_errors"):
                    return {"ok": True, "text": f"Виявлено помилки: {result.get('analysis')}"}
                else:
                    return {"ok": True, "text": "Помилок не виявлено"}
            else:
                return {"ok": False, "text": "Не вдалося перевірити екран"}
        else:
            return {"ok": False, "text": "Vision система не активна"}

    if verb_type == "read_text":
        if VISION_ENABLED:
            from vision_module import vision
            screenshot_path = vision.capture_screenshot()
            if screenshot_path:
                ocr_text = vision.extract_text_ocr(screenshot_path)
                if ocr_text:
                    return {"ok": True, "text": f"Розпізнаний текст: {ocr_text}"}
                else:
                    return {"ok": False, "text": "Текст не знайдено на екрані"}
            else:
                return {"ok": False, "text": "Не вдалося зробити скріншот"}
        else:
            return {"ok": False, "text": "Vision система не активна"}

    # Track metrics if learning enabled
    duration_ms = (time.time() - start_time) * 1000
    if LEARNING_ENABLED:
        try:
            analytics.track_command(CommandMetric(
                command=text,
                intent_type=verb_type or "unknown",
                success=True,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                source=source
            ))
        except Exception as e:
            logger.error(f"Failed to track metric: {e}")

    # Зберігаємо невідому команду в контекст
    if CONTEXT_ENABLED and NLU_ENABLED:
        context_manager.add_message(
            session_id, "assistant", "Не зрозумів команду"
        )

    return None

def on_voice_command(text: str):
    logger.info(f"🎤 Command: {text}")
    res = handle_intent(text, source="voice")
    if res:
        response_text = res.get('text')
        logger.info(f"🤖 AIVA: {response_text}")
        
        source = res.get("details", {}).get("source")
        if source == "ai_brain" or source == "smart_home" or res.get("ok"):
             speak(response_text)

# --- INIT ---
global_listener = AivaListener(on_command_callback=on_voice_command)



# ---------- API ----------
class RunBody(BaseModel):
    query: str

class TranscribeBody(BaseModel):
    wav_path: str

@app.get("/")
def root():
    """Головна сторінка - перенаправлення на dashboard"""
    return FileResponse("static/dashboard.html")

@app.get("/dashboard")
def dashboard():
    """Dashboard сторінка"""
    return FileResponse("static/dashboard.html")

@app.get("/api/health")
def health():
    return {"ok": True, "version": VERSION}

@app.get("/api/stats")
def stats():
    return {"ok": True, "version": VERSION, "apps": db_counts()}

@app.post("/api/run_app")
def run_app(body: RunBody):
    # Використовуємо handle_intent
    res = handle_intent(body.query, source="api")
    if res:
         return {"ok": res["ok"], "text": res["text"], "details": res.get("details", {})}
    return {"ok": False, "text": "Не зрозумів команду"}

@app.post("/api/transcribe_file")
def api_transcribe_file(body: TranscribeBody):
    if not os.path.exists(body.wav_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        initial = build_initial_prompt_from_db(DB_PATH)
        text = transcribe_wav_custom(body.wav_path, vad_filter=False, initial_prompt=initial)
        return {"ok": True, "text": text}
    except Exception as e:
        logger.error(f"Transcribe error: {e}")
        return {"ok": False, "error": str(e)}

# ---------- WebSocket Push-to-Talk ----------
@app.get("/asr")
def asr_page():
    return HTMLResponse(_ASR_HTML)

@app.websocket("/ws/asr")
async def ws_asr(ws: WebSocket):
    await ws.accept()
    logger.info("WS connection open")
    buf = bytearray()
    lang = os.getenv("ASR_LANGUAGE", "uk")

    try:
        while True:
            msg = await ws.receive()
            if "type" in msg and msg["type"] == "websocket.disconnect":
                break

            if msg.get("text"):
                text = msg["text"].strip()
                if text.startswith("start"):
                    buf.clear()
                elif text == "end":
                    import tempfile, wave
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                        tmp_wav = f.name
                        f.close() 
                    
                    with wave.open(tmp_wav, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) 
                        wf.setframerate(16000)
                        wf.writeframes(bytes(buf))

                    initial = build_initial_prompt_from_db(DB_PATH)
                    txt = transcribe_wav_custom(tmp_wav, language=lang, vad_filter=False, initial_prompt=initial)
                    try: os.remove(tmp_wav)
                    except: pass

                    if not (txt and txt.strip()):
                        await ws.send_json({"type": "noop"})
                        continue

                    res = handle_intent(txt, source="websocket")
                    if res:
                        await ws.send_json({"type": "result", "text": txt, "action": res})
                    else:
                        await ws.send_json({"type": "result", "text": txt})
            elif msg.get("bytes"):
                buf.extend(msg["bytes"])
    except WebSocketDisconnect:
        pass

# ---------- WebSocket Dashboard ----------
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """WebSocket для real-time оновлень dashboard"""
    await websocket_endpoint(websocket)

# HTML для веб-інтерфейсу (Push-to-Talk)
_ASR_HTML = r"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8" />
<title>AIVA Push-to-Talk</title>
<style>
 body{font-family:system-ui,Segoe UI,Arial;margin:32px;background:#f0f0f0}
 button{font-size:24px;padding:20px 40px;border-radius:50px;border:none;background:#007bff;color:white;cursor:pointer;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
 button:active{background:#0056b3;transform:scale(0.98)}
 #log{margin-top:20px;white-space:pre-wrap;background:white;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.05);min-height:100px}
</style>
</head>
<body>
  <h1>🎤 AIVA Web Interface</h1>
  <p>Натисни та тримай кнопку, щоб говорити.</p>
  <div style="text-align:center;margin:40px">
    <button id="rec">🎙️ Говорити</button>
  </div>
  <div id="log"></div>

<script>
const btn = document.getElementById('rec');
const log = (t) => { 
    const el = document.getElementById('log');
    el.textContent = t + "\n" + el.textContent; 
};

let ws=null, media=null, node=null, src=null, ctx=null;
let isRecording=false, waitingResult=false;

async function setup() {
  ws = new WebSocket(`ws://${location.host}/ws/asr`);
  ws.onmessage = (ev)=>{
    try{
      const j = JSON.parse(ev.data);
      if (j.type==='result') {
        const actionText = (j.action && j.action.text) ? ("\n🤖: " + j.action.text) : "";
        log('🗣️: ' + j.text + actionText);
        waitingResult=false; isRecording=false;
      }
    } catch(e){}
  };
  await new Promise(r=> ws.onopen = r);

  ctx = new (window.AudioContext||window.webkitAudioContext)();
  media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } });
  src = ctx.createMediaStreamSource(media);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  
  proc.onaudioprocess = (e)=>{
     if (ws && ws.readyState===1 && isRecording) {
        const ch = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(ch.length);
        for (let i=0;i<ch.length;i++){
          let s = Math.max(-1, Math.min(1, ch[i]));
          pcm16[i] = s<0 ? s*0x8000 : s*0x7FFF;
        }
        ws.send(pcm16.buffer);
     }
  };
  src.connect(proc); proc.connect(ctx.destination);
  node = proc;
}

btn.addEventListener('mousedown', async ()=>{
  if (!ws) await setup();
  if (waitingResult) return;
  isRecording = true; 
  ws.send('start');
  btn.style.background = "#dc3545"; // Red
  btn.innerText = "🛑 Запис...";
});
btn.addEventListener('mouseup', ()=>{
  if (!ws || waitingResult) return;
  if (isRecording){ 
      isRecording=false; 
      ws.send('end'); 
      waitingResult=true; 
      btn.style.background = "#ffc107"; // Yellow
      btn.innerText = "⏳ Обробка...";
  }
  setTimeout(() => {
      btn.style.background = "#007bff"; 
      btn.innerText = "🎙️ Говорити";
  }, 1000);
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8787)