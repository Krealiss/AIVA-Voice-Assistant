import subprocess
import sys
import time
import os

def run_process(script_name):
    """Запускає Python скрипт в окремому процесі"""
    return subprocess.Popen(
        [sys.executable, script_name],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        shell=True # Для Windows, щоб відкрити в тому ж середовищі
    )

def main():
    print("🚀 Запуск системи AIVA...")
    
    # 1. Запускаємо Агента (FastAPI + Listener + Hardware)
    # uvicorn запускається через subprocess, або можна просто запустити файл, 
    # якщо в agent_main.py додати блок if __name__ == "__main__": uvicorn.run(...)
    # Але ми запустимо як модуль, щоб бачити логи.
    
    # Варіант А: Запуск через uvicorn команду (рекомендовано для FastAPI)
    agent_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "agent_main:app", "--host", "127.0.0.1", "--port", "8787", "--reload"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print("✅ Агент (Core) запущено.")
    time.sleep(5) # Даємо час серверу піднятися
    
    # 2. Запускаємо Телеграм Бота
    bot_process = run_process("telegram_bot.py")
    print("✅ Телеграм Бот запущено.")

    print("\n--- Система працює. Натисни Ctrl+C для зупинки ---\n")

    try:
        while True:
            time.sleep(1)
            # Перевірка, чи не впали процеси
            if agent_process.poll() is not None:
                print("⚠️ Агент впав! Перезапуск...")
                agent_process = subprocess.Popen([sys.executable, "-m", "uvicorn", "agent_main:app", "--host", "0.0.0.0", "--port", "8787"])
            
            if bot_process.poll() is not None:
                print("⚠️ Бот впав! Перезапуск...")
                bot_process = run_process("telegram_bot.py")

    except KeyboardInterrupt:
        print("\n🛑 Зупинка системи...")
        agent_process.terminate()
        bot_process.terminate()
        print("👋 До зустрічі!")

if __name__ == "__main__":
    main()