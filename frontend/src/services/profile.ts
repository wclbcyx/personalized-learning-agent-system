export interface LearningMemoryItem {
  question: string
  answer_summary: string
  source_ids: string[]
  knowledge_points: string[]
  next_steps: string[]
  created_at: string
  metadata: Record<string, unknown>
}

export interface StudentProfile {
  student_id: string
  course_name?: string | null
  learning_goal?: string | null
  current_level?: string | null
  preferred_style?: string | null
  weak_points: string[]
  recent_recommendations: string[]
  memories: LearningMemoryItem[]
  created_at: string
  updated_at: string
}

export async function getStudentProfile(studentId: string): Promise<StudentProfile> {
  const response = await fetch(`/api/profile/${encodeURIComponent(studentId)}`)

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `读取学生画像失败：${response.status}`)
  }

  return response.json()
}

export async function clearStudentMemory(studentId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`/api/profile/${encodeURIComponent(studentId)}/memory`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `清空记忆失败：${response.status}`)
  }

  return response.json()
}
