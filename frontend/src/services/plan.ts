import type { GeneratePlanRequest, LearningPlan } from '../types/plan'

export async function generateLearningPlan(payload: GeneratePlanRequest): Promise<LearningPlan> {
  const response = await fetch('/api/plan/generate', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `生成学习计划失败：${response.status}`)
  }

  return response.json()
}

export async function getLearningPlan(planId: string): Promise<LearningPlan> {
  const response = await fetch(`/api/plan/${encodeURIComponent(planId)}`)

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `读取学习计划失败：${response.status}`)
  }

  return response.json()
}
