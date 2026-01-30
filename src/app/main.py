"""应用入口"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.routes import chat, health
from src.app.core.config import settings


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Agentic RAG with LangGraph + DeepSeek + Self-Reflection",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    application.include_router(health.router)
    application.include_router(chat.router)

    return application


app = create_app()


def main() -> None:
    """启动应用"""
    uvicorn.run(
        "src.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
