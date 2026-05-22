"""
API для управління макросами AIVA
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from macro_manager import macro_manager

router = APIRouter(prefix="/api/macros", tags=["macros"])


class MacroCreate(BaseModel):
    name: str
    triggers: List[str]
    commands: List[str]


class MacroUpdate(BaseModel):
    name: Optional[str] = None
    triggers: Optional[List[str]] = None
    commands: Optional[List[str]] = None


@router.get("/")
def list_macros():
    return [m.to_dict() for m in macro_manager.list_all()]


@router.post("/")
def create_macro(body: MacroCreate):
    if not body.name.strip():
        raise HTTPException(400, "Назва макросу не може бути порожньою")
    if not body.triggers:
        raise HTTPException(400, "Потрібен хоча б один тригер")
    if not body.commands:
        raise HTTPException(400, "Потрібна хоча б одна команда")

    macro = macro_manager.create(body.name, body.triggers, body.commands)
    return {"ok": True, "macro": macro.to_dict()}


@router.get("/{macro_id}")
def get_macro(macro_id: str):
    macro = macro_manager.get(macro_id)
    if not macro:
        raise HTTPException(404, "Макрос не знайдено")
    return macro.to_dict()


@router.patch("/{macro_id}")
def update_macro(macro_id: str, body: MacroUpdate):
    macro = macro_manager.update(
        macro_id,
        name=body.name,
        triggers=body.triggers,
        commands=body.commands,
    )
    if not macro:
        raise HTTPException(404, "Макрос не знайдено")
    return {"ok": True, "macro": macro.to_dict()}


@router.delete("/{macro_id}")
def delete_macro(macro_id: str):
    if not macro_manager.delete(macro_id):
        raise HTTPException(404, "Макрос не знайдено")
    return {"ok": True}


@router.post("/{macro_id}/run")
def run_macro(macro_id: str):
    macro = macro_manager.get(macro_id)
    if not macro:
        raise HTTPException(404, "Макрос не знайдено")
    return _execute_macro(macro)


def _execute_macro(macro) -> dict:
    """Виконує команди макросу і повертає результати."""
    from agent_main import handle_intent

    macro_manager.record_use(macro.id)
    results = []

    for cmd in macro.commands:
        res = handle_intent(cmd, source="macro")
        results.append({
            "command": cmd,
            "ok": res.get("ok", False) if res else False,
            "text": res.get("text", "немає відповіді") if res else "не виконано",
        })

    all_ok = all(r["ok"] for r in results)
    summary = " | ".join(r["text"] for r in results)

    return {
        "ok": all_ok,
        "macro": macro.name,
        "results": results,
        "summary": summary,
    }
