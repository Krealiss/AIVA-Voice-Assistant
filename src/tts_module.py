import os
import asyncio
import logging
import edge_tts
import pygame
import tempfile

logger = logging.getLogger("tts")

# Голос: 'uk-UA-OstapNeural' (чоловічий) або 'uk-UA-PolinaNeural' (жіночий)
VOICE = "uk-UA-OstapNeural" 

def play_audio(file_path):
    """Відтворює аудіофайл через pygame без блокування основного потоку (або з блокуванням)."""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Чекаємо завершення, щоб файл не видалився завчасно
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.quit()
    except Exception as e:
        logger.error(f"Playback error: {e}")

async def _generate_audio_async(text, output_file):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def speak(text):
    """Головна функція: генерує mp3 і відтворює його."""
    if not text:
        return

    logger.info(f"🗣️ Speaking: {text[:50]}...")
    
    # Створюємо тимчасовий файл
    tmp_path = os.path.join(tempfile.gettempdir(), "aiva_speech.mp3")
    
    try:
        # Запускаємо асинхронну генерацію в синхронному коді
        asyncio.run(_generate_audio_async(text, tmp_path))
        
        # Відтворюємо
        play_audio(tmp_path)
        
    except Exception as e:
        logger.error(f"TTS Error: {e}")
    finally:
        # Прибираємо за собою
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

# Для тесту, якщо запустити файл напряму
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    speak("Привіт, я готовий до роботи.")