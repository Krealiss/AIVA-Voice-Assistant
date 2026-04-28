import os
import logging
from typing import Optional, Dict
from threading import Lock
from faster_whisper import WhisperModel

# ===== ENV / CONFIG =====
ASR_MODEL_SIZE = os.getenv("ASR_MODEL_SIZE", "base")       # base швидше за medium, точність достатня
ASR_LANGUAGE   = os.getenv("ASR_LANGUAGE", "uk")           # uk | en | ru ...
ASR_DEVICE     = os.getenv("ASR_DEVICE", "cpu").lower()    # cuda | cpu
ASR_BEAM_SIZE  = int(os.getenv("ASR_BEAM_SIZE", "1"))      # 1 = найшвидше для коротких команд

logger = logging.getLogger("asr")
if not logger.handlers:
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

_model: Optional[WhisperModel] = None
_model_lock = Lock()


def _make_model(device: str) -> WhisperModel:
    """
    Створення моделі з оптимальним compute_type:
      - CUDA: float16 (швидко та точно)
      - CPU : int8   (найшвидше на CPU)
    """
    compute_type = "float16" if device == "cuda" else "int8"
    logger.info("[ASR] loading model=%s device=%s compute=%s", ASR_MODEL_SIZE, device, compute_type)
    # Додаємо num_workers для паралельної обробки
    return WhisperModel(
        ASR_MODEL_SIZE,
        device=device,
        compute_type=compute_type,
        num_workers=2,  # Паралельна обробка для швидшого декодування
        download_root=None,
        local_files_only=False
    )


def get_model() -> WhisperModel:
    """Ледаче завантаження моделі з fallback CUDA→CPU."""
    global _model
    if _model is not None:
        return _model
    try:
        _model = _make_model(ASR_DEVICE)
    except Exception as e:
        logger.warning("[ASR] CUDA init failed: %s. Falling back to CPU…", e)
        _model = _make_model("cpu")
    return _model


def transcribe_wav_custom(
    wav_path: str,
    *,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    vad_filter: bool = True,
    vad_parameters: Optional[Dict] = None,
    beam_size: Optional[int] = None,
    temperature: float = 0.0,
    condition_on_previous_text: bool = False,
) -> str:
    """
    Оптимізоване розпізнавання з блокуванням потоків та покращеними VAD параметрами.
    """
    model = get_model()
    lang = language or ASR_LANGUAGE
    # Оптимізовані параметри VAD для швидшого реагування
    vparams = vad_parameters or {
        "min_silence_duration_ms": 150,  # Зменшено з 200 для швидшої реакції
        "speech_pad_ms": 100,
        "threshold": 0.35  # Трохи вище для зменшення false positives
    }
    bsize = beam_size if beam_size is not None else ASR_BEAM_SIZE

    # Блокування для thread-safety
    with _model_lock:
        segments, info = model.transcribe(
            wav_path,
            language=lang,
            beam_size=bsize,
            vad_filter=vad_filter,
            vad_parameters=vparams,
            condition_on_previous_text=condition_on_previous_text,
            temperature=temperature,
            initial_prompt=initial_prompt,
        )
        # Збираємо текст під замком
        text = " ".join(s.text.strip() for s in segments if s.text).strip()

    logger.info(
        "[ASR] transcribed='%s' lang=%s dur=%.2fs vad=%s beam=%s",
        text, lang, getattr(info, "duration", 0.0) or 0.0, vad_filter, bsize
    )
    return text


def warmup() -> None:
    """Одноразовий прогрів, щоб перший виклик не гальмував."""
    try:
        _ = get_model()
        logger.info("[ASR] warmup complete (model ready)")
    except Exception as e:
        logger.error("[ASR] warmup failed: %s", e)
