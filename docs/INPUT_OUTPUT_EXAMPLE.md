# 最终实现输入输出实例

## 用户输入

```json
{
  "student_id": "stu_001",
  "course": "大模型智能体开发",
  "goal": "4周内掌握 HelloAgents，并完成一个多智能体课程项目",
  "current_level": "了解 Python 和基础 LLM 调用，但不熟悉 RAG、记忆和多智能体协作",
  "available_time_per_day": "1.5小时",
  "preferred_style": "先讲原理，再给代码框架，最后做小练习",
  "current_question": "我想先学习 Agent 的工具调用和 RAG，应该怎么开始？"
}
```

## 系统最终输出

```json
{
  "session_id": "session_20260531_001",
  "answer": {
    "summary": "建议先学习工具调用，再学习 RAG，因为 RAG 本质上也可以被封装成知识检索工具。",
    "learning_path": [
      "第1阶段：理解 Agent、Prompt 和上下文工程",
      "第2阶段：掌握工具调用与 MCP 工具接入",
      "第3阶段：构建课程资料 RAG 知识库",
      "第4阶段：加入长期记忆和学习画像",
      "第5阶段：完成多智能体协作项目"
    ],
    "today_plan": [
      "阅读工具调用章节核心概念",
      "运行一个 SearchTool 或 MCPTool 示例",
      "整理 3 个 RAG 应用场景",
      "完成 5 道概念检测题"
    ],
    "explanation": "工具调用解决 Agent 如何连接外部能力，RAG 解决 Agent 如何使用课程资料和知识库。先学工具调用有助于理解后续的检索工具封装。",
    "exercise": {
      "type": "short_answer",
      "question": "请解释 Agent 工具调用和普通函数调用的区别，并说明 RAG 为什么可以看作一种工具增强方式。",
      "rubric": [
        "是否说明由模型决定何时调用工具",
        "是否说明工具调用需要参数解析和结果回填",
        "是否说明 RAG 包含检索和生成两个阶段"
      ]
    },
    "sources": [
      {
        "title": "HelloAgents 教材：工具调用章节",
        "chunk_id": "chapter_tools_003",
        "reason": "用于解释工具调用机制"
      },
      {
        "title": "HelloAgents 教材：RAG 章节",
        "chunk_id": "chapter_rag_002",
        "reason": "用于解释检索增强生成流程"
      }
    ]
  },
  "memory_update": {
    "student_level": "Python 基础较好，Agent 工具调用和 RAG 初学",
    "weak_points": [
      "工具调用参数设计",
      "RAG 检索结果如何进入上下文"
    ],
    "next_recommendation": "下一次优先练习：把课程资料检索封装为 KnowledgeRetrievalTool"
  },
  "evaluation": {
    "estimated_mastery": {
      "tool_calling": 0.35,
      "rag": 0.25,
      "context_engineering": 0.3
    },
    "confidence": 0.82
  }
}
```
