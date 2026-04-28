"""
Запуск AIVA з dashboard (гібридна версія)
"""
import subprocess
import sys
import time
import os

def main():
    print("🚀 Запуск системи AIVA з Dashboard...")

    # Перевіряємо чи є всі модулі
    try:
        import edge_tts
        import pygame
        full_version = True
        print("✅ Всі модулі доступні - запуск повної версії")
    except ImportError as e:
        full_version = False
        print(f"⚠️ Деякі модулі відсутні: {e}")
        print("📦 Запуск в режимі Dashboard (без голосу)")

    if full_version:
        # Запускаємо повну версію
        print("\n--- Запуск Agent (Core + Dashboard) ---")
        agent_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "agent_main:app",
             "--host", "127.0.0.1", "--port", "8787", "--reload"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print("✅ Агент запущено з dashboard на http://127.0.0.1:8787/dashboard")

        time.sleep(3)

        # Запускаємо Телеграм Бота
        try:
            bot_process = subprocess.Popen(
                [sys.executable, "telegram_bot.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                shell=True
            )
            print("✅ Телеграм Бот запущено")
        except Exception as e:
            print(f"⚠️ Не вдалося запустити Telegram бота: {e}")
            bot_process = None
    else:
        # Запускаємо lite версію
        print("\n--- Запуск Dashboard Lite ---")
        agent_process = subprocess.Popen(
            [sys.executable, "dashboard_lite.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print("✅ Dashboard запущено на http://127.0.0.1:8787/dashboard")
        bot_process = None

    print("\n" + "="*50)
    print("🎛️ Dashboard: http://127.0.0.1:8787/dashboard")
    print("🎤 Push-to-Talk: http://127.0.0.1:8787/asr")
    print("="*50)
    print("\n--- Система працює. Натисни Ctrl+C для зупинки ---\n")

    try:
        while True:
            time.sleep(1)

            # Перевірка процесів
            if agent_process.poll() is not None:
                print("⚠️ Агент впав! Перезапуск...")
                if full_version:
                    agent_process = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "agent_main:app",
                         "--host", "127.0.0.1", "--port", "8787"]
                    )
                else:
                    agent_process = subprocess.Popen(
                        [sys.executable, "dashboard_lite.py"]
                    )

            if bot_process and bot_process.poll() is not None:
                print("⚠️ Бот впав! Перезапуск...")
                bot_process = subprocess.Popen(
                    [sys.executable, "telegram_bot.py"],
                    shell=True
                )

    except KeyboardInterrupt:
        print("\n🛑 Зупинка системи...")
        agent_process.terminate()
        if bot_process:
            bot_process.terminate()
        print("👋 До зустрічі!")

if __name__ == "__main__":
    main()
