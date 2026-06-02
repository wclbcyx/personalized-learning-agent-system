<script setup lang="ts">
import { computed, ref } from 'vue'
import { clearStudentMemory, getStudentProfile, type StudentProfile } from '../services/profile'

const studentId = ref('stu_001')
const profile = ref<StudentProfile | null>(null)
const loading = ref(false)
const error = ref('')
const message = ref('')

const gradingMemories = computed(() =>
  (profile.value?.memories || []).filter((item) => item.metadata?.type === 'grading'),
)

async function loadProfile() {
  if (!studentId.value.trim()) {
    error.value = '请先填写学生 ID。'
    return
  }
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    profile.value = await getStudentProfile(studentId.value.trim())
  } catch (err) {
    error.value = err instanceof Error ? err.message : '读取画像失败。'
  } finally {
    loading.value = false
  }
}

async function clearMemory() {
  if (!studentId.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    await clearStudentMemory(studentId.value.trim())
    message.value = '学生记忆已清空。'
    await loadProfile()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '清空失败。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="module-page two-column-page">
    <form class="question-panel module-card" @submit.prevent="loadProfile">
      <div class="panel-header">
        <p class="eyebrow">Long-Term Memory</p>
        <h2>学生画像</h2>
        <p>查看目标、水平、偏好、薄弱点、历史提问和练习批改。</p>
      </div>
      <label>
        <span>学生 ID</span>
        <input v-model="studentId" autocomplete="off" />
      </label>
      <button class="primary-button" type="submit" :disabled="loading">
        {{ loading ? '读取中...' : '读取画像' }}
      </button>
      <button class="secondary-button" type="button" :disabled="loading" @click="clearMemory">
        清空记忆
      </button>
      <p v-if="error" class="inline-error">{{ error }}</p>
      <p v-if="message" class="hint">{{ message }}</p>
    </form>

    <section class="answer-panel module-card scroll-card">
      <div v-if="!profile" class="empty-state compact-empty">
        <h2>等待读取画像</h2>
        <p>画像会展示长期记忆如何影响后续问答、出题和计划。</p>
      </div>

      <div v-if="profile" class="result-stack">
        <section class="answer-card">
          <p class="eyebrow">{{ profile.student_id }}</p>
          <h2>{{ profile.course_name || '未设置课程' }}</h2>
          <p><strong>学习目标：</strong>{{ profile.learning_goal || '未设置' }}</p>
          <p><strong>当前水平：</strong>{{ profile.current_level || '未设置' }}</p>
          <p><strong>讲解偏好：</strong>{{ profile.preferred_style || '未设置' }}</p>
        </section>

        <section class="result-grid">
          <div class="info-block">
            <h3>薄弱知识点</h3>
            <div class="tag-list left-tags">
              <span v-for="point in profile.weak_points" :key="point">{{ point }}</span>
            </div>
            <p v-if="!profile.weak_points.length" class="muted">暂无薄弱点。</p>
          </div>
          <div class="info-block">
            <h3>近期建议</h3>
            <ol class="step-list">
              <li v-for="item in profile.recent_recommendations" :key="item">{{ item }}</li>
            </ol>
          </div>
        </section>

        <section class="info-block">
          <h3>历史学习记录</h3>
          <ol class="timeline-list">
            <li v-for="item in profile.memories.slice().reverse()" :key="item.created_at + item.question">
              <strong>{{ item.question }}</strong>
              <small>{{ item.created_at }}</small>
              <p>{{ item.answer_summary }}</p>
            </li>
          </ol>
        </section>

        <section class="info-block">
          <h3>练习批改记录</h3>
          <ol class="timeline-list">
            <li v-for="item in gradingMemories" :key="item.created_at + item.question">
              <strong>{{ item.metadata.exercise_id }} · {{ item.metadata.score }} 分</strong>
              <p>{{ item.answer_summary }}</p>
            </li>
          </ol>
        </section>
      </div>
    </section>
  </section>
</template>
