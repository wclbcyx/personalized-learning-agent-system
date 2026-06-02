"""FastAPI application entrypoint.

运行方式示例：

    cd backend
    ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

当前提供：
    - GET  /health
    - POST /api/learning/ask
    - POST /api/exercise/generate
    - POST /api/exercise/grade
    - POST /api/plan/generate
    - POST /api/agent/coordinate
    - POST /api/agent/reflect
    - GET/POST /api/materials
    - GET/PUT/DELETE /api/profile
    - GET /api/evaluation/summary
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.exercise import router as exercise_router
from app.api.routes.learning import router as learning_router
from app.api.routes.materials import router as materials_router
from app.api.routes.plan import router as plan_router
from app.api.routes.profile import router as profile_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。

    单独封装成函数的好处：
        - 测试时可以直接调用 create_app()
        - 后续注册更多路由或中间件时结构更清楚
    """

    settings = get_settings()

    app = FastAPI(
        title="Personalized Learning Agent System",
        description="个性化学习辅导多智能体系统",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(learning_router)
    app.include_router(exercise_router)
    app.include_router(plan_router)
    app.include_router(agent_router)
    app.include_router(materials_router)
    app.include_router(profile_router)
    app.include_router(evaluation_router)

    @app.get("/health")
    def health_check() -> dict:
        """健康检查接口。

        用来确认服务是否正常启动，不会触发大模型调用。
        """

        return {
            "status": "ok",
            "service": "personalized-learning-agent-system",
            "version": "1.0.0",
        }

    return app


app = create_app()
