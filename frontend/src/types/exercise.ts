export type ExerciseType = 'short_answer' | 'choice' | 'calculation'
export type DifficultyLevel = 'easy' | 'medium' | 'hard'

export interface GenerateExerciseRequest {
  student_id: string
  course_name?: string
  topic?: string
  question?: string
  count: number
  difficulty: DifficultyLevel
  exercise_type: ExerciseType
  extra_requirement?: string
}

export interface ExerciseItem {
  exercise_id: string
  exercise_type: ExerciseType
  difficulty: DifficultyLevel
  knowledge_points: string[]
  question: string
  options: string[]
  hint?: string | null
  source_ids: string[]
  created_at: string
  metadata: Record<string, unknown>
}

export interface ExerciseGenerationResponse {
  exercise_set_id: string
  student_id: string
  exercises: ExerciseItem[]
  summary?: string | null
  debug: Record<string, unknown>
}

export interface GradeExerciseRequest {
  student_id: string
  exercise_set_id: string
  exercise_id: string
  student_answer: string
}

export interface GradingResult {
  exercise_id: string
  is_correct: boolean
  score: number
  feedback: string
  reference_answer: string
  mistake_points: string[]
  improvement_suggestions: string[]
  graded_at: string
  debug: Record<string, unknown>
}
