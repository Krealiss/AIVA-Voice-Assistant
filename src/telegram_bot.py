import os
import re
import time
import logging
import urllib.parse
import tempfile
import shutil
import subprocess
import requests
import telebot
import sys
import html  # <--- ДОДАНО: для безпеки HTML повідомлень

# Імпортуємо конфігурацію
import config

# === Logging ===
LOG_LEVEL = getattr(logging, (getattr(config, "LOG_LEVEL", "INFO")).upper(), logging.INFO)
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bot")

# === Config ===
BOT_TOKEN = config.BOT_TOKEN
AGENT_URL = config.AGENT_URL.rstrip("/")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

# Ініціалізація бота
bot = telebot.TeleBot(BOT_TOKEN)

# === МЕНЮ (КЛАВІАТУРИ) ===

def menu_main():
    """Головне меню"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_devices = telebot.types.KeyboardButton("📱 Керування пристроями")
    btn_macros = telebot.types.KeyboardButton("⚡ Макроси")
    btn_rescan = telebot.types.KeyboardButton("/rescan")
    btn_help = telebot.types.KeyboardButton("/help")
    markup.add(btn_devices, btn_macros)
    markup.add(btn_rescan, btn_help)
    return markup

def menu_devices():
    """Меню вибору типу пристрою"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_light = telebot.types.KeyboardButton("💡 Світло")
    btn_socket = telebot.types.KeyboardButton("⚡ Розетка")
    btn_back = telebot.types.KeyboardButton("⬅️ Головне меню")
    markup.add(btn_light, btn_socket)
    markup.add(btn_back)
    return markup

def menu_light():
    """Меню керування світлом"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_on = telebot.types.KeyboardButton("💡 Увімкни світло")
    btn_off = telebot.types.KeyboardButton("🌑 Вимкни світло")
    btn_back = telebot.types.KeyboardButton("⬅️ Назад до пристроїв")
    markup.add(btn_on, btn_off)
    markup.add(btn_back)
    return markup

def menu_socket():
    """Меню керування розеткою"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_on = telebot.types.KeyboardButton("⚡ Увімкни розетку")
    btn_off = telebot.types.KeyboardButton("🔌 Вимкни розетку")
    btn_back = telebot.types.KeyboardButton("⬅️ Назад до пристроїв")
    markup.add(btn_on, btn_off)
    markup.add(btn_back)
    return markup

# === Стан для діалогу створення макросу ===
# { chat_id: {"step": "name"|"triggers"|"commands", "name": str, "triggers": str} }
_macro_state: dict = {}


def macros_list_message():
    """Отримує список макросів і повертає текст + inline-клавіатуру."""
    try:
        res = requests.get(f"{AGENT_URL}/api/macros", timeout=10)
        macros = res.json() if res.ok else []
    except Exception:
        return "⚠️ Не вдалося отримати список макросів.", None

    if not macros:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("➕ Новий макрос", callback_data="macro_new"))
        return "📋 Макросів ще немає.", markup

    text = "⚡ <b>Ваші макроси:</b>\n\n"
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for m in macros:
        cmd_count = len(m.get("commands", []))
        uses = m.get("use_count", 0)
        text += f"• <b>{html.escape(m['name'])}</b> — {cmd_count} команд"
        if uses:
            text += f", запущено {uses}×"
        text += "\n"
        btn_run = telebot.types.InlineKeyboardButton(
            f"▶ {m['name']}", callback_data=f"macro_run_{m['id']}"
        )
        btn_del = telebot.types.InlineKeyboardButton(
            "🗑", callback_data=f"macro_del_{m['id']}"
        )
        markup.add(btn_run, btn_del)

    markup.add(telebot.types.InlineKeyboardButton("➕ Новий макрос", callback_data="macro_new"))
    return text, markup


# === Utilities ===

def make_request_id(message) -> str:
    ts = int(time.time() * 1000)
    mid = getattr(message, "message_id", 0)
    return f"req-{ts}-{mid}"

def ogg_to_wav(ogg_path: str, wav_path: str) -> None:
    cmd = [
        FFMPEG_PATH, "-y",
        "-i", ogg_path,
        "-ac", "1",
        "-ar", "16000",
        "-acodec", "pcm_s16le",
        "-af", "highpass=f=200, dynaudnorm=f=150:g=15", 
        wav_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def normalize_text(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[^\w\sа-яА-ЯіїєґІЇЄҐ]", "", s)
    s = s.replace("’", "'")
    s = re.sub(r"^(ну|е|а|так|слухай|будь ласка|ану)\s+", "", s) 
    s = re.sub(r"[.,!?;:–—…]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def cleanup_search_query(q: str) -> str:
    s = q.strip()
    s = re.sub(r"[.,!?;:–—…\s]+$", "", s)
    s = re.sub(r"([A-Za-z]+)[\u0400-\u04FF]+", r"\1", s)
    return s

# === Handlers ===

@bot.message_handler(commands=["start"])
def cmd_start(message):
    text = (
        "👋 <b>Привіт! Я AIVA.</b>\n\n"
        "Я керую твоїм комп'ютером та розумним будинком.\n"
        "Обери дію в меню:"
    )
    bot.reply_to(message, text, parse_mode="HTML", reply_markup=menu_main())

@bot.message_handler(commands=["help"])
def cmd_help(message):
    text = (
        "🎤 Голос або ⌨️ Текст.\n"
        "Команди: /rescan, /macros\n"
        "/cancel — скасувати поточну дію"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["cancel"])
def cmd_cancel(message):
    if message.chat.id in _macro_state:
        del _macro_state[message.chat.id]
        bot.reply_to(message, "❌ Скасовано.", reply_markup=menu_main())
    else:
        bot.reply_to(message, "Нічого скасовувати.", reply_markup=menu_main())

@bot.message_handler(commands=["rescan"])
def cmd_rescan(message):
    bot.reply_to(message, "⏳ <b>Індексація...</b>", parse_mode="HTML")
    try:
        # Запускаємо index_win.py
        cmd = [sys.executable, "index_win.py"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if len(output) > 500: output = "..." + output[-500:]
            # Екрануємо HTML, щоб уникнути помилки Bad Request
            safe_output = html.escape(output)
            bot.reply_to(message, f"✅ <b>Базу оновлено!</b>\n<pre>{safe_output}</pre>", parse_mode="HTML")
        else:
            # Екрануємо помилки
            safe_err = html.escape(result.stderr)
            bot.reply_to(message, f"⚠️ Помилка: <pre>{safe_err}</pre>", parse_mode="HTML")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {html.escape(str(e))}", parse_mode="HTML")

@bot.message_handler(commands=["macros"])
def cmd_macros(message):
    text, markup = macros_list_message()
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("macro_"))
def handle_macro_callback(call):
    data = call.data

    if data == "macro_new":
        _macro_state[call.message.chat.id] = {"step": "name"}
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "➕ <b>Новий макрос</b>\n\nВведіть <b>назву</b> макросу:",
            parse_mode="HTML",
        )
        return

    if data.startswith("macro_run_"):
        macro_id = data[len("macro_run_"):]
        bot.answer_callback_query(call.id, "⏳ Виконую...")
        try:
            res = requests.post(f"{AGENT_URL}/api/macros/{macro_id}/run", timeout=30)
            d = res.json()
            status = "✅" if d.get("ok") else "⚠️"
            text = f"{status} <b>{html.escape(d.get('macro', ''))}</b>\n{html.escape(d.get('summary', ''))}"
        except Exception as e:
            text = f"❌ Помилка: {html.escape(str(e))}"
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")
        return

    if data.startswith("macro_del_"):
        macro_id = data[len("macro_del_"):]
        try:
            res = requests.delete(f"{AGENT_URL}/api/macros/{macro_id}", timeout=10)
            if res.ok:
                bot.answer_callback_query(call.id, "Видалено")
                text, markup = macros_list_message()
                bot.edit_message_text(
                    text, call.message.chat.id, call.message.message_id,
                    parse_mode="HTML", reply_markup=markup
                )
            else:
                bot.answer_callback_query(call.id, "⚠️ Помилка видалення")
        except Exception:
            bot.answer_callback_query(call.id, "❌ Немає зв'язку")
        return

    if data.startswith("macro_confirm_del_"):
        macro_id = data[len("macro_confirm_del_"):]
        try:
            requests.delete(f"{AGENT_URL}/api/macros/{macro_id}", timeout=10)
            bot.answer_callback_query(call.id, "Видалено ✅")
            text, markup = macros_list_message()
            bot.edit_message_text(
                text, call.message.chat.id, call.message.message_id,
                parse_mode="HTML", reply_markup=markup
            )
        except Exception:
            bot.answer_callback_query(call.id, "❌ Помилка")
        return


@bot.message_handler(content_types=["voice", "audio"])
def handle_voice(message):
    rid = make_request_id(message)
    tmp_dir = tempfile.mkdtemp(prefix="aiva_bot_")
    ogg_path = os.path.join(tmp_dir, "voice.ogg")
    wav_path = os.path.join(tmp_dir, "voice.wav")
    
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        r = requests.get(file_url, timeout=30)
        with open(ogg_path, "wb") as f: f.write(r.content)
        ogg_to_wav(ogg_path, wav_path)

        logger.info(f"[{rid}] Sending voice to Agent API")
        transcribe_resp = requests.post(
            f"{AGENT_URL}/api/transcribe_file",
            json={"wav_path": wav_path},
            timeout=60
        )
        t_data = transcribe_resp.json()
        
        if t_data.get("ok"):
            text = t_data.get("text", "")
            bot.reply_to(message, f"🗣 <i>«{html.escape(text)}»</i>", parse_mode="HTML")
            
            # Виконуємо розпізнану команду
            if text:
                run_r = requests.post(f"{AGENT_URL}/api/run_app", json={"query": text}, timeout=20)
                run_data = run_r.json()
                if run_data.get("text"):
                    bot.reply_to(message, run_data.get("text"))
        else:
            bot.reply_to(message, "⚠️ Помилка розпізнавання.")

    except Exception as e:
        logger.error(f"[{rid}] Voice error: {e}")
        bot.reply_to(message, "⚠️ Помилка обробки голосу.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    text_raw = message.text.strip()
    chat_id = message.chat.id

    # --- 0. ДІАЛОГ СТВОРЕННЯ МАКРОСУ ---
    if chat_id in _macro_state:
        state = _macro_state[chat_id]
        step = state["step"]

        if step == "name":
            if not text_raw:
                bot.reply_to(message, "Назва не може бути порожньою.")
                return
            state["name"] = text_raw
            state["step"] = "triggers"
            bot.reply_to(
                message,
                "Введіть <b>тригери</b> (фрази що запускають макрос), через кому:\n"
                "<i>Наприклад: робочий режим, почни роботу</i>",
                parse_mode="HTML",
            )
            return

        if step == "triggers":
            triggers = [t.strip() for t in text_raw.split(",") if t.strip()]
            if not triggers:
                bot.reply_to(message, "Вкажіть хоча б один тригер.")
                return
            state["triggers"] = triggers
            state["step"] = "commands"
            bot.reply_to(
                message,
                "Введіть <b>команди</b> (кожна з нового рядка):\n"
                "<i>Наприклад:\nвідкрий chrome\nгучність 40</i>",
                parse_mode="HTML",
            )
            return

        if step == "commands":
            commands = [c.strip() for c in text_raw.split("\n") if c.strip()]
            if not commands:
                bot.reply_to(message, "Вкажіть хоча б одну команду.")
                return

            del _macro_state[chat_id]
            try:
                res = requests.post(
                    f"{AGENT_URL}/api/macros",
                    json={"name": state["name"], "triggers": state["triggers"], "commands": commands},
                    timeout=10,
                )
                if res.ok:
                    m = res.json().get("macro", {})
                    bot.reply_to(
                        message,
                        f"✅ Макрос <b>{html.escape(m.get('name', state['name']))}</b> створено!\n"
                        f"Тригери: {', '.join(state['triggers'])}\n"
                        f"Команд: {len(commands)}",
                        parse_mode="HTML",
                        reply_markup=menu_main(),
                    )
                else:
                    err = res.json().get("detail", "Невідома помилка")
                    bot.reply_to(message, f"⚠️ {html.escape(err)}", reply_markup=menu_main())
            except Exception as e:
                bot.reply_to(message, f"❌ Помилка: {html.escape(str(e))}", reply_markup=menu_main())
            return

    # --- 1. ЛОГІКА НАВІГАЦІЇ ПО МЕНЮ ---

    if text_raw == "⚡ Макроси":
        text, markup = macros_list_message()
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        return

    if text_raw == "📱 Керування пристроями":
        bot.send_message(message.chat.id, "🎛 Оберіть пристрій:", reply_markup=menu_devices())
        return

    if text_raw == "💡 Світло":
        bot.send_message(message.chat.id, "💡 Керування світлом:", reply_markup=menu_light())
        return

    if text_raw == "⚡ Розетка":
        bot.send_message(message.chat.id, "⚡ Керування розеткою:", reply_markup=menu_socket())
        return

    if text_raw == "⬅️ Назад до пристроїв" or text_raw == "⬅️ Назад":
        bot.send_message(message.chat.id, "🎛 Оберіть пристрій:", reply_markup=menu_devices())
        return
        
    if text_raw == "⬅️ Головне меню":
        bot.send_message(message.chat.id, "🏠 Головне меню:", reply_markup=menu_main())
        return

    # --- 2. ЛОГІКА ВИКОНАННЯ КОМАНД ---
    
    text_norm = normalize_text(text_raw)

    if text_norm.startswith("знайди ") and len(text_norm) > 7:
        query = text_norm.split(" ", 1)[1]
        q_clean = cleanup_search_query(query)
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q_clean)}"
        bot.reply_to(message, f"🔎 <a href='{url}'>Результати пошуку: {html.escape(q_clean)}</a>", parse_mode="HTML")
        return

    try:
        r = requests.post(f"{AGENT_URL}/api/run_app", json={"query": text_norm}, timeout=20)
        data = r.json()
        
        if data.get("text"):
            bot.reply_to(message, data.get("text"))
        else:
            bot.reply_to(message, "🤷‍♂️ Агент повернув порожню відповідь.")
            
    except requests.exceptions.ConnectionError:
        bot.reply_to(message, "⚠️ Немає зв'язку з сервером (agent_main.py).")
    except Exception as e:
        logger.error(f"Bot Text Error: {e}")
        bot.reply_to(message, "⚠️ Сталася помилка.")

if __name__ == "__main__":
    logger.info("🤖 Telegram Bot Started (Menu Mode)")
    bot.delete_webhook() 
    bot.infinity_polling(timeout=60, long_polling_timeout=20)