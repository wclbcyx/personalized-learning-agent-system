import type {
  ExerciseGenerationResponse,
  GenerateExerciseRequest,
  GradeExerciseRequest,
  GradingResult,
} from '../types/exercise'

export async function generateExercises(
  payload: GenerateExerciseRequest,
): Promise<ExerciseGenerationResponse> {
  const response = await fetch('/api/exercise/generate', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `生成练习失败：${response.status}`)
  }

  return response.json()
}

export async function gradeExercise(payload: GradeExerciseRequest): Promise<GradingResult> {
  const response = await fetch('/api/exercise/grade', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `批改失败：${response.status}`)
  }

  return response.json()
}
