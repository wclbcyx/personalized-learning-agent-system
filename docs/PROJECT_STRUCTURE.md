# 项目结构说明

```text
personalized-learning-agent-system/
├── backend/
│   ├── app/
│   │   ├── agents/          # 7 类核心 Agent
│   │   ├── api/routes/      # 学习、对话、练习、资料、画像等接口
│   │   ├── core/            # 配置、提示词、上下文构建、编排器
│   │   ├── models/          # 学生、课程、练习、记忆等数据模型
│   │   ├── services/        # 学习计划、RAG、记忆、批改、报告服务
│   │   ├── tools/           # 搜索、代码运行、文件解析、知识检索、评分工具
│   │   ├── memory/          # 长期记忆设计文档
│   │   ├── rag/             # 切分、向量化、检索策略文档
│   │   ├── evaluation/      # 指标、测试用例与评估设计
│   │   └── workflows/       # 学习会话和练习反馈流程
│   └── data/
│       ├── course_materials/ # 课程资料
│       ├── vector_store/     # 向量库
│       ├── student_profiles/ # 学生画像
│       ├── submissions/      # 学生提交
│       └── logs/             # 运行日志
├── frontend/
│   └── src/
│       ├── components/       # 学习计划、聊天、练习、记忆、进度面板
│       ├── views/            # 首页、学习页、练习页、画像页、报告页
│       ├── services/         # 前端 API 调用
│       ├── stores/           # 学生状态与会话状态
│       └── types/            # TypeScript 类型
├── docs/
│   ├── architecture/         # 架构设计文档
│   ├── examples/             # 输入输出样例与执行轨迹
│   └── thesis/               # 开题、创新点、实施计划
├── configs/                  # 配置文件占位
└── scripts/                  # 启动与资料导入脚本占位
```

## 后续实现顺序建议

1. 先实现课程资料导入与 RAG 检索。
2. 再实现学生画像和长期记忆。
3. 接着实现学习规划、讲解、练习、批改四个核心 Agent。
4. 最后实现反思 Agent、评估指标和前端可视化。
