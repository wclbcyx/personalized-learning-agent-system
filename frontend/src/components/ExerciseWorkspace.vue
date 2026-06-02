<script setup lang="ts">
import { reactive, ref } from 'vue'
import { generateExercises, gradeExercise } from '../services/exercise'
import type {
  DifficultyLevel,
  ExerciseGenerationResponse,
  ExerciseType,
  GradingResult,
} from '../types/exercise'

const form = reactive({
  student_id: 'stu_001',
  course_name: '初中数学',
  topic: '不等式',
  question: '为什么解不等式时，两边除以负数要改变不等号方向？',
  count: 3,
  difficulty: 'medium' as DifficultyLevel,
  exercise_type: 'calculation' as ExerciseType,
  extra_requirement: '题目要贴近当前讲解内容，适合课堂练习',
})

const loadingGenerate = ref(false)
const generatingError = ref('')
const exerciseSet = ref<ExerciseGenerationResponse | null>(null)
const answers = reactive<Record<string, string>>({})
const gradingLoading = reactive<Record<string, boolean>>({})
const gradingErrors = reactive<Record<string, string>>({})
const gradingResults = reactive<Record<string, GradingResult>>({})

async function handleGenerate() {
  if (!form.student_id.trim()) {
    generatingError.value = '请先填写学生 ID。'
    return
  }

  loadingGenerate.value = true
  generatingError.value = ''
  exerciseSet.value = null
  Object.keys(answers).forEach((key) => delete answers[key])
  Object.keys(gradingResults).forEach((key) => delete gradingResults[key])
  Object.keys(gradingErrors).forEach((key) => delete gradingErrors[key])

  try {
    exerciseSet.value = await generateExercises({
      student_id: form.student_id.trim(),
      course_name: form.course_name.trim() || undefined,
      topic: form.topic.trim() || undefined,
      question: form.question.trim() || undefined,
      count: Number(form.count),
      difficulty: form.difficulty,
      exercise_type: form.exercise_type,
      extra_requirement: form.extra_requirement.trim() || undefined,
    })
  } catch (error) {
    generatingError.value = error instanceof Error ? error.message : '生成练习失败。'
  } finally {
    loadingGenerate.value = false
  }
}

async function handleGrade(exerciseId: string) {
  if (!exerciseSet.value) return

  const answer = answers[exerciseId]?.trim()
  if (!answer) {
    gradingErrors[exerciseId] = '请先填写答案。'
    return
  }

  gradingLoading[exerciseId] = true
  gradingErrors[exerciseId] = ''

  try {
    gradingResults[exerciseId] = await gradeExercise({
      student_id: form.student_id.trim(),
      exercise_set_id: exerciseSet.value.exercise_set_id,
      exercise_id: exerciseId,
      student_answer: answer,
    })
  } catch (error) {
    gradingErrors[exerciseId] = error instanceof Error ? error.message : '批改失败。'
  } finally {
    gradingLoading[exerciseId] = false
  }
}
</script>

<template>
  <section class="exercise-workspace">
    <div class="exercise-toolbar">
      <div>
        <p class="eyebrow">Practice & Grading</p>
        <h2>练习生成与批改</h2>
      </div>
      <button class="secondary-button" type="button" :disabled="loadingGenerate" @click="handleGenerate">
        <span v-if="loadingGenerate" class="spinner"></span>
        {{ loadingGenerate ? '正在生成...' : '生成练习' }}
      </button>
    </div>

    <div class="exercise-settings">
      <label>
        <span>学生 ID</span>
        <input v-model="form.student_id" />
      </label>
      <label>
        <span>课程名称</span>
        <input v-model="form.course_name" />
      </label>
      <label>
        <span>练习主题</span>
        <input v-model="form.topic" />
      </label>
      <label>
        <span>数量</span>
        <input v-model.number="form.count" type="number" min="1" max="10" />
      </label>
      <label>
        <span>难度</span>
        <select v-model="form.difficulty">
          <option value="easy">easy</option>
          <option value="medium">medium</option>
          <option value="hard">hard</option>
        </select>
      </label>
      <label>
        <span>题型</span>
        <select v-model="form.exercise_type">
          <option value="short_answer">short_answer</option>
          <option value="choice">choice</option>
          <option value="calculation">calculation</option>
        </select>
      </label>
    </div>

    <label>
      <span>关联问题</span>
      <textarea v-model="form.question" rows="3"></textarea>
    </label>

    <label class="exercise-extra">
      <span>额外要求</span>
      <input v-model="form.extra_requirement" />
    </label>

    <p v-if="generatingError" class="inline-error">{{ generatingError }}</p>

    <div v-if="exerciseSet" class="exercise-set">
      <div class="exercise-summary">
        <strong>{{ exerciseSet.summary || '已生成练习' }}</strong>
        <span>{{ exerciseSet.exercise_set_id }}</span>
      </div>

      <article v-for="exercise in exerciseSet.exercises" :key="exercise.exercise_id" class="exercise-card">
        <div class="exercise-card-head">
          <div>
            <strong>{{ exercise.exercise_id }}</strong>
            <p>{{ exercise.difficulty }} · {{ exercise.exercise_type }}</p>
          </div>
          <div class="tag-list">
            <span v-for="point in exercise.knowledge_points" :key="point">{{ point }}</span>
          </div>
        </div>

        <p class="exercise-question">{{ exercise.question }}</p>

        <ul v-if="exercise.options.length" class="option-list">
          <li v-for="option in exercise.options" :key="option">{{ option }}</li>
        </ul>

        <p v-if="exercise.hint" class="hint">提示：{{ exercise.hint }}</p>

        <label>
          <span>你的答案</span>
          <textarea v-model="answers[exercise.exercise_id]" rows="4"></textarea>
        </label>

        <button
          class="secondary-button"
          type="button"
          :disabled="gradingLoading[exercise.exercise_id]"
          @click="handleGrade(exercise.exercise_id)"
        >
          <span v-if="gradingLoading[exercise.exercise_id]" class="spinner"></span>
          {{ gradingLoading[exercise.exercise_id] ? '正在批改...' : '提交批改' }}
        </button>

        <p v-if="gradingErrors[exercise.exercise_id]" class="inline-error">
          {{ gradingErrors[exercise.exercise_id] }}
        </p>

        <div v-if="gradingResults[exercise.exercise_id]" class="grading-result">
          <div class="score-line">
            <strong>{{ gradingResults[exercise.exercise_id].score }} 分</strong>
            <span :class="{ pass: gradingResults[exercise.exercise_id].is_correct }">
              {{ gradingResults[exercise.exercise_id].is_correct ? '判断：正确' : '判断：需订正' }}
            </span>
          </div>
          <p>{{ gradingResults[exercise.exercise_id].feedback }}</p>
          <p><strong>参考答案：</strong>{{ gradingResults[exercise.exercise_id].reference_answer }}</p>
          <div v-if="gradingResults[exercise.exercise_id].mistake_points.length">
            <strong>错误点</strong>
            <ul>
              <li v-for="item in gradingResults[exercise.exercise_id].mistake_points" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div v-if="gradingResults[exercise.exercise_id].improvement_suggestions.length">
            <strong>改进建议</strong>
            <ul>
              <li v-for="item in gradingResults[exercise.exercise_id].improvement_suggestions" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
