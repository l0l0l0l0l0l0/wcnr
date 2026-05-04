# -*- coding: utf-8 -*-
"""
页面路由 — 主页、布控管理、统计报表、线索页
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@router.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(TEMPLATES_DIR / "alert.html")


@router.get("/control", response_class=HTMLResponse)
def control_page():
    return FileResponse(TEMPLATES_DIR / "control.html")


@router.get("/report", response_class=HTMLResponse)
def report_page():
    return FileResponse(TEMPLATES_DIR / "report.html")


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return FileResponse(TEMPLATES_DIR / "login.html")


@router.get("/users", response_class=HTMLResponse)
def users_page():
    return FileResponse(TEMPLATES_DIR / "users.html")


@router.get("/settings", response_class=HTMLResponse)
def settings_page():
    return FileResponse(TEMPLATES_DIR / "settings.html")


@router.get("/clues", response_class=HTMLResponse)
def clues_page():
    path = TEMPLATES_DIR / "clues.html"
    if path.exists():
        return FileResponse(path)
    return HTMLResponse("<h1>线索管理页面开发中</h1>", status_code=200)


@router.get("/ai-portrait", response_class=HTMLResponse)
def ai_portrait_page():
    return FileResponse(TEMPLATES_DIR / "ai_portrait.html")


@router.get("/archive-report", response_class=HTMLResponse)
def archive_report_page():
    return FileResponse(TEMPLATES_DIR / "archive_report.html")
