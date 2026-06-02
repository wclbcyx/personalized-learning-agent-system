export type TaskType = 'reading' | 'explanation' | 'exercise' | 'review' | 'quiz' | 'project'
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'skipped'
export type PlanStatus = 'draft' | 'active' | 'completed' | 'adjusted'

export interface GeneratePlanRequest {
  student_id: string
  course_name: string
  learning_goal: string
  focus_topics: string[]
  available_days: number
  daily_minutes: number
  extra_requirement?: string
}

export interface LearningTask {
  task_id: string
  task_type: TaskType
  title: string
  description: string
  estimated_minutes: number
  knowledge_points: string[]
  completion_criteria?: string | null
  source_ids: string[]
  status: TaskStatus
  metadata: Record<string, unknown>
}

export interface PlanCheckpoint {
  checkpoint_id: string
  title: string
  description: string
  pass_criteria: string
  result_summary?: string | null
  passed?: boolean | null
}

export interface LearningStage {
  stage_id: string
  title: string
  objective: string
  start_day: number
  end_day: number
  knowledge_points: string[]
  tasks: LearningTask[]
  checkpoint?: PlanCheckpoint | null
}

export interface LearningPlan {
  plan_id: string
  student_id: string
  course_name: string
  learning_goal: string
  available_days: number
  daily_minutes: number
  stages: LearningStage[]
  overall_suggestions: string[]
  status: PlanStatus
  created_at: string
  updated_at: string
  debug: Record<string, unknown>
}

export interface ReflectionResult {
  summary?: string
  mastered_points?: string[]
  weak_points?: string[]
  next_recommendations?: string[]
  level_update?: string
  debug?: Record<string, unknown>
}
