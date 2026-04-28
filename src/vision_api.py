"""
Vision API - endpoints для screen understanding
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os

try:
    from vision_module import vision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

router = APIRouter(prefix="/api/vision", tags=["vision"])

# === Models ===

class ScreenAnalysisRequest(BaseModel):
    prompt: Optional[str] = None

class ElementSearchRequest(BaseModel):
    element_description: str

class CompareRequest(BaseModel):
    screenshot1: str
    screenshot2: str

# === Endpoints ===

@router.get("/available")
async def check_availability():
    """Перевірити доступність vision features"""
    if not VISION_AVAILABLE:
        return {"available": False, "reason": "Vision module not imported"}

    return {
        "available": True,
        "screenshot": vision.SCREENSHOT_AVAILABLE if hasattr(vision, 'SCREENSHOT_AVAILABLE') else False,
        "ocr": vision.OCR_AVAILABLE if hasattr(vision, 'OCR_AVAILABLE') else False,
        "vision_api": vision.client is not None
    }

@router.post("/screenshot")
async def capture_screenshot():
    """Зробити скріншот екрану"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        screenshot_path = vision.capture_screenshot(save=True)

        if not screenshot_path:
            raise HTTPException(status_code=500, detail="Failed to capture screenshot")

        return {
            "ok": True,
            "screenshot": screenshot_path,
            "message": "Screenshot captured"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/describe")
async def describe_screen(request: ScreenAnalysisRequest):
    """Описати поточний екран"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        result = vision.describe_screen(prompt=request.prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/find-element")
async def find_element(request: ElementSearchRequest):
    """Знайти UI елемент на екрані"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        result = vision.find_ui_element(request.element_description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-errors")
async def detect_errors():
    """Виявити помилки на екрані"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        result = vision.detect_errors()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/read-text")
async def read_screen_text():
    """Прочитати текст з екрану (OCR)"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        text = vision.read_screen_text()
        return {
            "ok": True,
            "text": text,
            "length": len(text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active-window")
async def get_active_window():
    """Отримати інформацію про активне вікно"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        result = vision.get_active_window_info()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
async def compare_screenshots(request: CompareRequest):
    """Порівняти два скріншоти"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        # Перевіряємо існування файлів
        if not os.path.exists(request.screenshot1):
            raise HTTPException(status_code=404, detail=f"Screenshot 1 not found: {request.screenshot1}")
        if not os.path.exists(request.screenshot2):
            raise HTTPException(status_code=404, detail=f"Screenshot 2 not found: {request.screenshot2}")

        result = vision.compare_screenshots(request.screenshot1, request.screenshot2)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-image")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = None
):
    """Аналіз завантаженого зображення"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        # Зберігаємо тимчасово
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Аналізуємо
        default_prompt = "Опиши що на цьому зображенні"
        result = vision.analyze_with_vision_api(tmp_path, prompt or default_prompt)

        # Видаляємо тимчасовий файл
        os.unlink(tmp_path)

        return {
            "ok": True,
            "filename": file.filename,
            "analysis": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_screenshots(keep_last: int = 50):
    """Видалити старі скріншоти"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        vision.cleanup_old_screenshots(keep_last=keep_last)
        return {
            "ok": True,
            "message": f"Cleaned up old screenshots, kept last {keep_last}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/screenshots")
async def list_screenshots(limit: int = 20):
    """Список останніх скріншотів"""
    if not VISION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Vision module not available")

    try:
        from pathlib import Path
        screenshots = sorted(
            vision.screenshots_dir.glob("screenshot_*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]

        return {
            "ok": True,
            "screenshots": [
                {
                    "path": str(s),
                    "filename": s.name,
                    "size": s.stat().st_size,
                    "created": s.stat().st_mtime
                }
                for s in screenshots
            ],
            "total": len(screenshots)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
