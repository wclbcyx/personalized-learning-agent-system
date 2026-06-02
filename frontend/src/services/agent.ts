import type { ReflectionResult } from '../types/plan'

export async function reflectStudent(studentId: string): Promise<ReflectionResult> {
  const response = await fetch('/api/agent/reflect', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ student_id: studentId }),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `生成学习反思失败：${response.status}`)
  }

  return response.json()
}
