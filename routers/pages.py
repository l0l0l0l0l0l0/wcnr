# -*- coding: utf-8 -*-
"""
页面路由 — 主页、线索页
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@router.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(TEMPLATES_DIR / "gov_monitor_v2.html")


@router.get("/v2", response_class=HTMLResponse)
def index_v2():
    return FileResponse(TEMPLATES_DIR / "gov_monitor_v2.html")


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return FileResponse(TEMPLATES_DIR / "login.html")


@router.get("/users", response_class=HTMLResponse)
def users_page():
    return FileResponse(TEMPLATES_DIR / "users.html")


@router.get("/clues", response_class=HTMLResponse)
def clues_page():
    path = TEMPLATES_DIR / "clues.html"
    if path.exists():
        return FileResponse(path)
    return HTMLResponse("<h1>线索管理页面开发中</h1>", status_code=200)
