export interface AskLearningRequest {
  student_id: string
  question: string
  course_name?: string
  learning_goal?: string
  current_level?: string
  preferred_style?: string
}

export interface SourceChunk {
  chunk_id: string
  title: string
  content: string
  score: number
  source_path: string
  start_index?: number | null
  end_index?: number | null
  metadata: Record<string, unknown>
}

export interface LearningAnswerResponse {
  answer: string
  sources: SourceChunk[]
  next_steps: string[]
  summary?: string | null
  debug: Record<string, unknown>
}
