import os
import json
import pyaudio
import logging
import threading
import wave
import tempfile
import time
import collections
import winsound
from vosk import Model, KaldiRecognizer
from asr_whisper import transcribe_wav_custom

# === CONFIG ===
VOSK_MODEL_PATH = "model_vosk"
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000
RECORD_SECONDS = 3  # Зменшено з 4 для швидшої обробки

logger = logging.getLogger("listener")

class AivaListener:
    def __init__(self, on_command_callback):
        self.callback = on_command_callback
        self.running = False
        self.thread = None
        self.processing_thread = None 
        
        self.wake_words_variants = [
            "айва", "ай ва", "а й ва", 
            "іва", "ава", "ейва", 
            "хай вам", "але", "iowa", "джарвіс"
        ]

        if not os.path.exists(VOSK_MODEL_PATH):
            logger.error(f"❌ Vosk model not found at '{VOSK_MODEL_PATH}'.")
            self.model = None
        else:
            try:
                logger.info("Loading Vosk model...")
                self.model = Model(VOSK_MODEL_PATH)
                logger.info("Vosk loaded successfully.")
            except Exception as e:
                logger.error(f"Vosk init error: {e}")
                self.model = None

    def start(self):
        if not self.model or self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logger.info(f"👂 [Threaded] Listening for: {self.wake_words_variants}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _listen_loop(self):
        p = pyaudio.PyAudio()
        stream = None

        try:
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=SAMPLE_RATE,
                            input=True,
                            frames_per_buffer=CHUNK_SIZE)
        except Exception as e:
            logger.error(f"Mic open error: {e}")
            return

        rec = KaldiRecognizer(self.model, SAMPLE_RATE)

        # Оптимізований буфер перед-запису (0.6 сек)
        pre_buffer = collections.deque(maxlen=int(SAMPLE_RATE / CHUNK_SIZE * 0.6))

        state = "WAITING"
        command_frames = []
        chunks_to_record = int(SAMPLE_RATE / CHUNK_SIZE * RECORD_SECONDS)

        logger.info("🎤 Microphone stream active.")

        while self.running:
            try:
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            except Exception as e:
                # logger.error(f"Stream read error: {e}")
                continue

            if state == "WAITING":
                pre_buffer.append(data)
                
                # --- ВИПРАВЛЕННЯ 1: Перевіряємо, чи зайнятий обробник ---
                if self.processing_thread and self.processing_thread.is_alive():
                    # Ми "глухі", поки обробляємо попередню команду.
                    # Можна додати print("Busy..."), якщо хочеш бачити це.
                    continue 

                # --- ВИПРАВЛЕННЯ 2: Ловимо слово і в Result, і в PartialResult ---
                caught_wake_word = False
                text_check = ""

                if rec.AcceptWaveform(data):
                    # Це фінальний результат фрази
                    res = json.loads(rec.Result())
                    text_check = res.get("text", "").lower()
                else:
                    # Це проміжний результат
                    partial = json.loads(rec.PartialResult())
                    text_check = partial.get("partial", "").lower()
                
                if text_check:
                    for w in self.wake_words_variants:
                        if w in text_check:
                            logger.info(f"🔔 Wake Word detected: '{w}' in '{text_check}'")
                            caught_wake_word = True
                            break
                
                if caught_wake_word:
                    winsound.Beep(1000, 200)
                    state = "RECORDING"
                    # Додаємо те, що було в буфері (сам момент "Айва...")
                    command_frames = list(pre_buffer)
                    # Скидаємо розпізнавач, щоб не ловити старі слова
                    rec.Reset()
            
            elif state == "RECORDING":
                command_frames.append(data)
                
                if len(command_frames) >= chunks_to_record:
                    logger.info("📦 Recording complete. Processing...")
                    
                    frames_copy = list(command_frames)
                    
                    self.processing_thread = threading.Thread(
                        target=self._process_frames_bg, 
                        args=(p, frames_copy)
                    )
                    self.processing_thread.start()
                    
                    # Миттєво повертаємося до очікування
                    state = "WAITING"
                    command_frames = []
                    pre_buffer.clear()
                    rec.Reset()

        if stream:
            stream.stop_stream()
            stream.close()
        p.terminate()

    def _process_frames_bg(self, pa_instance, frames):
        """Працює у фоновому потоці. ВИПРАВЛЕНО ДЛЯ WINDOWS."""
        tmp_wav = None
        try:
            # --- WINDOWS FIX: Create -> Close -> Open ---
            f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav = f.name
            f.close()

            with wave.open(tmp_wav, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(pa_instance.get_sample_size(pyaudio.paInt16))
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(frames))
            
            logger.info("🧠 Sending to Whisper...")

            # Оптимізовані параметри VAD для швидшої обробки
            text = transcribe_wav_custom(
                tmp_wav,
                language="uk",
                beam_size=1,  # Найшвидший режим
                vad_parameters={
                    "threshold": 0.35,  # Оптимальний баланс
                    "min_silence_duration_ms": 150,  # Швидше реагування
                    "speech_pad_ms": 100
                },
                initial_prompt="Українська мова. Запусти. Знайди. Котра година."
            )
            
            # Фільтруємо галюцинації (якщо текст збігається з промптом або дуже короткий)
            if not text or len(text.strip()) < 2 or "Українська мова" in text:
                logger.info("🤷‍♂️ Ignored (hallucination/noise).")
                return

            if text:
                logger.info(f"🗣 Recognized: '{text}'")
                self.callback(text)

        except Exception as e:
            logger.error(f"Processing error: {e}")
        finally:
            if tmp_wav and os.path.exists(tmp_wav):
                try:
                    os.remove(tmp_wav)
                except Exception:
                    pass