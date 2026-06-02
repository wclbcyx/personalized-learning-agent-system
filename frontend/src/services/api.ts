export interface EvaluationSummary {
  student_count: number
  material_count: number
  indexed_material_count: number
  exercise_set_count: number
  plan_count: number
  memory_count: number
  grading_count: number
  average_score?: number | null
  weak_point_count: number
  event_count: number
  average_response_ms?: number | null
  intent_distribution: Record<string, number>
}

export async function getEvaluationSummary(): Promise<EvaluationSummary> {
  const response = await fetch('/api/evaluation/summary')

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `读取评估指标失败：${response.status}`)
  }

  return response.json()
}

export async function getEvaluationEvents(): Promise<{ events: Record<string, unknown>[]; count: number }> {
  const response = await fetch('/api/evaluation/events')

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `读取调用日志失败：${response.status}`)
  }

  return response.json()
}
