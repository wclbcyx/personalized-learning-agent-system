# 个性化学习陪伴与课程项目辅导多智能体系统

本项目是一个面向毕业设计展示的 V1.0 个性化学习 Agent 系统。系统融合 RAG、长期记忆、多智能体协作和前端学习工作台，支持学生画像、学习计划、学习提问、出题批改、学习反思、资料管理和评估看板。

## V1.0 核心功能

- 资料上传与知识库管理：支持 `.md`、`.txt`、`.pdf` 上传，保存到本地课程资料目录并进入 RAG 检索。
- RAG 检索增强：根据学生问题从课程资料中召回片段，并在回答中展示引用来源。
- 搜索工具兜底：课程资料未命中时，TutorAgent 会调用搜索工具辅助回答。
- 长期学生画像：保存学习目标、当前水平、讲解偏好、薄弱点、历史提问和批改记录。
- 练习生成与自动批改：ExerciseAgent 生成题目，GradingAgent 基于参考答案和 rubric 批改。
- 个性化学习计划：PlannerAgent 生成阶段、任务和检查点。
- 学习反思：ReflectionAgent 根据近期表现更新薄弱点和下一步建议。
- 评估与数据看板：汇总资料数、记忆数、批改次数、平均分、薄弱点、协调器调用日志，并支持 JSON/CSV 导出。

## 技术架构

- 前端：Vue 3 + TypeScript + Vite
- 后端：FastAPI + 本地轻量 LLM/Agent 封装 + 搜索工具
- RAG：本地课程资料读取 + chunk 切分 + 关键词检索
- 记忆：本地 JSON 学生画像
- 数据：课程资料、学生画像、练习批次、学习计划、调用日志

## 主要接口

- `POST /api/learning/ask`：学习提问
- `POST /api/exercise/generate`：生成练习
- `POST /api/exercise/grade`：批改练习
- `POST /api/plan/generate`：生成学习计划
- `POST /api/agent/reflect`：学习反思
- `GET /api/materials`、`POST /api/materials/upload`：资料管理
- `GET /api/profile/{student_id}`、`DELETE /api/profile/{student_id}/memory`：学生画像
- `GET /api/evaluation/summary`、`GET /api/evaluation/export.json`、`GET /api/evaluation/export.csv`：评估数据

## 启动方式

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，并通过 Vite 代理访问 `http://localhost:8000/api`。

## 演示脚本

1. 在“学生画像”查看 `stu_001` 的学习目标、薄弱点和历史记录。
2. 在“生成计划”生成阶段化学习计划。
3. 在“学习提问”输入不等式问题，查看 RAG 引用来源。
4. 在“生成练习”生成 3 道题并提交答案批改。
5. 在“学习反思”生成近期诊断并更新画像。
6. 在“资料管理”确认已有初中数学资料，或上传新的 `.md/.txt/.pdf` 资料。
7. 在“数据看板”查看指标并导出实验数据。

## 当前说明

V1.0 已形成可展示的完整系统结构。RAG 当前是本地关键词检索，适合毕设演示和论文对比；后续可升级为 Qdrant/FAISS 向量检索和更严格的实验评估。
