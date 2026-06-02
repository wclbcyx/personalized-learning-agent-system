<script setup lang="ts">
import { reactive, ref } from 'vue'
import { reflectStudent } from '../services/agent'
import { generateLearningPlan } from '../services/plan'
import type { LearningPlan, ReflectionResult } from '../types/plan'

const form = reactive({
  student_id: 'stu_001',
  course_name: '初中数学',
  learning_goal: '两周内掌握不等式和一次函数',
  focus_topics: '不等式, 一次函数',
  available_days: 14,
  daily_minutes: 40,
  extra_requirement: '每天安排一个小练习，阶段结束安排检查点',
})

const plan = ref<LearningPlan | null>(null)
const reflection = ref<ReflectionResult | null>(null)
const planLoading = ref(false)
const reflectLoading = ref(false)
const planError = ref('')
const reflectError = ref('')

function parseFocusTopics() {
  return form.focus_topics
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

async function handleGeneratePlan() {
  if (!form.student_id.trim() || !form.course_name.trim() || !form.learning_goal.trim()) {
    planError.value = '请先填写学生 ID、课程名称和学习目标。'
    return
  }

  planLoading.value = true
  planError.value = ''
  plan.value = null

  try {
    plan.value = await generateLearningPlan({
      student_id: form.student_id.trim(),
      course_name: form.course_name.trim(),
      learning_goal: form.learning_goal.trim(),
      focus_topics: parseFocusTopics(),
      available_days: Number(form.available_days),
      daily_minutes: Number(form.daily_minutes),
      extra_requirement: form.extra_requirement.trim() || undefined,
    })
  } catch (error) {
    planError.value = error instanceof Error ? error.message : '生成学习计划失败。'
  } finally {
    planLoading.value = false
  }
}

async function handleReflect() {
  if (!form.student_id.trim()) {
    reflectError.value = '请先填写学生 ID。'
    return
  }

  reflectLoading.value = true
  reflectError.value = ''
  reflection.value = null

  try {
    reflection.value = await reflectStudent(form.student_id.trim())
  } catch (error) {
    reflectError.value = error instanceof Error ? error.message : '生成学习反思失败。'
  } finally {
    reflectLoading.value = false
  }
}
</script>

<template>
  <section class="plan-panel">
    <div class="exercise-toolbar">
      <div>
        <p class="eyebrow">Planning & Reflection</p>
        <h2>学习计划与反思</h2>
      </div>
      <div class="plan-actions">
        <button class="secondary-button" type="button" :disabled="planLoading" @click="handleGeneratePlan">
          <span v-if="planLoading" class="spinner"></span>
          {{ planLoading ? '正在规划...' : '生成计划' }}
        </button>
        <button class="secondary-button" type="button" :disabled="reflectLoading" @click="handleReflect">
          <span v-if="reflectLoading" class="spinner"></span>
          {{ reflectLoading ? '正在反思...' : '学习反思' }}
        </button>
      </div>
    </div>

    <div class="plan-settings">
      <label>
        <span>学生 ID</span>
        <input v-model="form.student_id" />
      </label>
      <label>
        <span>课程名称</span>
        <input v-model="form.course_name" />
      </label>
      <label>
        <span>学习目标</span>
        <input v-model="form.learning_goal" />
      </label>
      <label>
        <span>重点知识点</span>
        <input v-model="form.focus_topics" />
      </label>
      <label>
        <span>学习天数</span>
        <input v-model.number="form.available_days" type="number" min="1" max="365" />
      </label>
      <label>
        <span>每日分钟</span>
        <input v-model.number="form.daily_minutes" type="number" min="1" max="600" />
      </label>
    </div>

    <label>
      <span>计划要求</span>
      <input v-model="form.extra_requirement" />
    </label>

    <p v-if="planError" class="inline-error">{{ planError }}</p>
    <p v-if="reflectError" class="inline-error">{{ reflectError }}</p>

    <div v-if="plan" class="plan-result">
      <div class="exercise-summary">
        <strong>{{ plan.learning_goal }}</strong>
        <span>{{ plan.plan_id }} · {{ plan.available_days }} 天 · {{ plan.daily_minutes }} 分钟/天</span>
      </div>

      <div v-if="plan.overall_suggestions.length" class="plan-suggestions">
        <strong>总体建议</strong>
        <ul>
          <li v-for="item in plan.overall_suggestions" :key="item">{{ item }}</li>
        </ul>
      </div>

      <article v-for="stage in plan.stages" :key="stage.stage_id" class="plan-stage">
        <div class="exercise-card-head">
          <div>
            <strong>{{ stage.title }}</strong>
            <p>第 {{ stage.start_day }} - {{ stage.end_day }} 天</p>
          </div>
          <div class="tag-list">
            <span v-for="point in stage.knowledge_points" :key="point">{{ point }}</span>
          </div>
        </div>
        <p class="exercise-question">{{ stage.objective }}</p>

        <ol class="task-list">
          <li v-for="task in stage.tasks" :key="task.task_id">
            <div>
              <strong>{{ task.title }}</strong>
              <span>{{ task.task_type }} · {{ task.estimated_minutes }} 分钟</span>
            </div>
            <p>{{ task.description }}</p>
            <small v-if="task.completion_criteria">完成标准：{{ task.completion_criteria }}</small>
          </li>
        </ol>

        <div v-if="stage.checkpoint" class="checkpoint">
          <strong>{{ stage.checkpoint.title }}</strong>
          <p>{{ stage.checkpoint.description }}</p>
          <small>达标标准：{{ stage.checkpoint.pass_criteria }}</small>
        </div>
      </article>

      <details class="debug-block">
        <summary>计划调试信息</summary>
        <pre>{{ JSON.stringify(plan.debug, null, 2) }}</pre>
      </details>
    </div>

    <div v-if="reflection" class="reflection-result">
      <h3>学习反思</h3>
      <p>{{ reflection.summary }}</p>
      <div class="result-grid">
        <div>
          <strong>已掌握</strong>
          <ul>
            <li v-for="item in reflection.mastered_points || []" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div>
          <strong>薄弱点</strong>
          <ul>
            <li v-for="item in reflection.weak_points || []" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
      <div v-if="reflection.next_recommendations?.length">
        <strong>下一步建议</strong>
        <ul>
          <li v-for="item in reflection.next_recommendations" :key="item">{{ item }}</li>
        </ul>
      </div>
      <p v-if="reflection.level_update"><strong>水平更新：</strong>{{ reflection.level_update }}</p>
    </div>
  </section>
</template>
