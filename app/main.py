# -*- coding: utf-8 -*-
"""
FastAPI 应用工厂
"""

import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/ttf", ".ttf")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动调度器，关闭时停止。"""
    scheduler = None
    try:
        from scheduler.tasks import init_scheduler
        scheduler = init_scheduler()
        scheduler.start()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"调度器启动失败: {e}")

    yield

    if scheduler:
        scheduler.stop()


class AuthRedirectMiddleware:
    """未登录用户访问页面时重定向到 /login"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path in ("/login", "/favicon.ico") or path.startswith("/static/") or path.startswith("/api/"):
                await self.app(scope, receive, send)
                return

            headers = dict(scope.get("headers", []))
            cookie_header = headers.get(b"cookie", b"").decode("utf-8")
            token = None
            for part in cookie_header.split(";"):
                part = part.strip()
                if part.startswith("access_token="):
                    token = part.split("=", 1)[1]
                    break

            if token:
                from services.auth import decode_access_token
                token_data = decode_access_token(token)
                if token_data and token_data.username:
                    await self.app(scope, receive, send)
                    return

            # Redirect to login
            from starlette.responses import RedirectResponse
            response = RedirectResponse(url="/login", status_code=302)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    app = FastAPI(title="天网可视化系统", lifespan=lifespan)
    app.add_middleware(AuthRedirectMiddleware)

    # 静态文件
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 注册路由
    from routers import pages, alerts, controls, reports, clues, dify, system, auth, users, data_import, population, cases, ai_portrait
    app.include_router(pages.router)
    app.include_router(alerts.router)
    app.include_router(controls.router)
    app.include_router(reports.router)
    app.include_router(clues.router)
    app.include_router(dify.router)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(data_import.router)
    app.include_router(population.router)
    app.include_router(cases.router)
    app.include_router(ai_portrait.router)

    # 异常处理
    from app.exception_handlers import register_handlers
    register_handlers(app)

    return app
