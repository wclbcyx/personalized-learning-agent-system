import type { AskLearningRequest, LearningAnswerResponse } from '../types/learning'

export async function askLearningQuestion(
  payload: AskLearningRequest,
): Promise<LearningAnswerResponse> {
  const response = await fetch('/api/learning/ask', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `请求失败：${response.status}`)
  }

  return response.json()
}
