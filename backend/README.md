# Backend

FastAPI + 本地轻量 LLM/Agent 封装，提供 V1.0 个性化学习多智能体系统能力。

## 模块

- `api/routes`：学习问答、练习、计划、统一协调、资料、画像、评估接口。
- `agents`：Coordinator、Tutor、Exercise、Grading、Planner、Reflection、Retriever。
- `services`：RAG、记忆、练习存储、批改、计划、资料管理、评估日志。
- `data`：课程资料、学生画像、练习批次、学习计划和调用日志。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
