<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import EvaluationDashboard from './components/EvaluationDashboard.vue'
import ExerciseWorkspace from './components/ExerciseWorkspace.vue'
import LearningPlanPanel from './components/LearningPlanPanel.vue'
import MaterialsPanel from './components/MaterialsPanel.vue'
import ProfilePanel from './components/ProfilePanel.vue'
import { reflectStudent } from './services/agent'
import { askLearningQuestion } from './services/learning'
import type { ReflectionResult } from './types/plan'
import type { LearningAnswerResponse } from './types/learning'

type ModuleKey =
  | 'profile'
  | 'plan'
  | 'ask'
  | 'exercise'
  | 'reflection'
  | 'materials'
  | 'evaluation'

const activeModule = ref<ModuleKey>('profile')

const modules: Array<{ key: ModuleKey; title: string; description: string }> = [
  { key: 'profile', title: '学生画像', description: '长期记忆、薄弱点和历史记录' },
  { key: 'plan', title: '生成计划', description: 'PlannerAgent 阶段化规划' },
  { key: 'ask', title: '学习提问', description: 'RAG 检索 + TutorAgent 讲解' },
  { key: 'exercise', title: '生成练习', description: 'ExerciseAgent 出题 + GradingAgent 批改' },
  { key: 'reflection', title: '学习反思', description: 'ReflectionAgent 更新薄弱点' },
  { key: 'materials', title: '资料管理', description: '上传资料、查看知识库与索引' },
  { key: 'evaluation', title: '数据看板', description: '评估指标、调用日志和实验导出' },
]

const askForm = reactive({
  student_id: 'stu_001',
  course_name: '初中数学',
  preferred_style: '先讲原因，再举例，最后给我下一步练习建议',
  question: '为什么解不等式时，两边除以负数要改变不等号方向？',
})

const askLoading = ref(false)
const askError = ref('')
const askResult = ref<LearningAnswerResponse | null>(null)

const canAsk = computed(() => askForm.student_id.trim() && askForm.question.trim() && !askLoading.value)

async function submitQuestion() {
  if (!canAsk.value) return

  askLoading.value = true
  askError.value = ''
  askResult.value = null

  try {
    askResult.value = await askLearningQuestion({
      student_id: askForm.student_id.trim(),
      question: askForm.question.trim(),
      course_name: askForm.course_name.trim() || undefined,
      preferred_style: askForm.preferred_style.trim() || undefined,
    })
  } catch (error) {
    askError.value = error instanceof Error ? error.message : '请求失败，请检查后端服务是否启动。'
  } finally {
    askLoading.value = false
  }
}

const reflectionForm = reactive({
  student_id: 'stu_001',
})
const reflectionLoading = ref(false)
const reflectionError = ref('')
const reflectionResult = ref<ReflectionResult | null>(null)

async function submitReflection() {
  if (!reflectionForm.student_id.trim()) {
    reflectionError.value = '请先填写学生 ID。'
    return
  }

  reflectionLoading.value = true
  reflectionError.value = ''
  reflectionResult.value = null

  try {
    reflectionResult.value = await reflectStudent(reflectionForm.student_id.trim())
  } catch (error) {
    reflectionError.value = error instanceof Error ? error.message : '生成学习反思失败。'
  } finally {
    reflectionLoading.value = false
  }
}
</script>

<template>
  <main class="app-shell app-shell-fixed">
    <aside class="module-sidebar">
      <div class="brand-block">
        <p class="eyebrow">Personalized Learning Agent</p>
        <h1>个性化学习辅导系统</h1>
        <div class="status-pill">
          <span class="status-dot"></span>
          V1.0 最终版
        </div>
      </div>

      <nav class="module-nav" aria-label="功能模块">
        <button
          v-for="item in modules"
          :key="item.key"
          type="button"
          :class="{ active: activeModule === item.key }"
          @click="activeModule = item.key"
        >
          <strong>{{ item.title }}</strong>
          <span>{{ item.description }}</span>
        </button>
      </nav>
    </aside>

    <section class="module-content">
      <ProfilePanel v-show="activeModule === 'profile'" />

      <section v-show="activeModule === 'plan'" class="module-page">
        <LearningPlanPanel />
      </section>

      <section v-show="activeModule === 'ask'" class="module-page two-column-page">
        <form class="question-panel module-card" @submit.prevent="submitQuestion">
          <div class="panel-header">
            <p class="eyebrow">Tutor</p>
            <h2>学习提问</h2>
            <p>填写学生、课程、讲解偏好和问题，系统会结合 RAG 和记忆回答。</p>
          </div>

          <label>
            <span>学生 ID</span>
            <input v-model="askForm.student_id" autocomplete="off" />
          </label>
          <label>
            <span>课程名称</span>
            <input v-model="askForm.course_name" autocomplete="off" />
          </label>
          <label>
            <span>讲解偏好（可选）</span>
            <input v-model="askForm.preferred_style" autocomplete="off" />
          </label>
          <label>
            <span>问题</span>
            <textarea v-model="askForm.question" rows="5"></textarea>
          </label>

          <button class="primary-button" type="submit" :disabled="!canAsk">
            <span v-if="askLoading" class="spinner"></span>
            {{ askLoading ? '正在调用大模型...' : '开始提问' }}
          </button>
        </form>

        <section class="answer-panel module-card scroll-card">
          <div v-if="!askResult && !askError" class="empty-state compact-empty">
            <h2>等待一次真实学习会话</h2>
            <p>提交后会展示 AI 回答、引用来源和下一步建议。</p>
          </div>

          <div v-if="askError" class="error-box compact-empty">
            <h2>请求失败</h2>
            <p>{{ askError }}</p>
          </div>

          <div v-if="askResult" class="result-stack">
            <section class="answer-card">
              <p class="eyebrow">AI Tutor Answer</p>
              <h2>{{ askResult.summary || '学习回答' }}</h2>
              <div class="answer-text">{{ askResult.answer }}</div>
              <div class="inline-actions">
                <button class="secondary-button" type="button" @click="activeModule = 'exercise'">
                  去生成练习
                </button>
                <button class="secondary-button" type="button" @click="activeModule = 'reflection'">
                  去学习反思
                </button>
              </div>
            </section>

            <section class="result-grid">
              <div class="info-block">
                <h3>引用来源</h3>
                <ul v-if="askResult.sources.length" class="source-list">
                  <li v-for="source in askResult.sources" :key="source.chunk_id">
                    <div class="source-head">
                      <strong>{{ source.chunk_id }}</strong>
                      <span>{{ source.score }}</span>
                    </div>
                    <p>{{ source.title }}</p>
                    <small>{{ source.metadata?.relative_path || source.source_path }}</small>
                  </li>
                </ul>
                <p v-else class="muted">暂无引用来源。</p>
              </div>

              <div class="info-block">
                <h3>下一步建议</h3>
                <ol v-if="askResult.next_steps.length" class="step-list">
                  <li v-for="step in askResult.next_steps" :key="step">{{ step }}</li>
                </ol>
                <p v-else class="muted">暂无建议。</p>
              </div>
            </section>

            <details class="debug-block">
              <summary>调试信息</summary>
              <pre>{{ JSON.stringify(askResult.debug, null, 2) }}</pre>
            </details>
          </div>
        </section>
      </section>

      <section v-show="activeModule === 'exercise'" class="module-page">
        <ExerciseWorkspace />
      </section>

      <section v-show="activeModule === 'reflection'" class="module-page two-column-page">
        <form class="module-card question-panel reflection-form" @submit.prevent="submitReflection">
          <div class="panel-header">
            <p class="eyebrow">Reflection</p>
            <h2>学习反思</h2>
            <p>输入学生 ID，系统会读取历史问答、练习批改和记忆记录。</p>
          </div>
          <label>
            <span>学生 ID</span>
            <input v-model="reflectionForm.student_id" autocomplete="off" />
          </label>
          <button class="primary-button" type="submit" :disabled="reflectionLoading">
            <span v-if="reflectionLoading" class="spinner"></span>
            {{ reflectionLoading ? '正在反思...' : '生成反思' }}
          </button>
          <p v-if="reflectionError" class="inline-error">{{ reflectionError }}</p>
        </form>

        <section class="module-card scroll-card">
          <div v-if="!reflectionResult && !reflectionError" class="empty-state compact-empty">
            <h2>等待学习反思</h2>
            <p>反思结果会更新学生画像里的薄弱点和下一步建议。</p>
          </div>

          <div v-if="reflectionResult" class="reflection-result">
            <h3>学习反思</h3>
            <p>{{ reflectionResult.summary }}</p>
            <div class="result-grid">
              <div>
                <strong>已掌握</strong>
                <ul>
                  <li v-for="item in reflectionResult.mastered_points || []" :key="item">{{ item }}</li>
                </ul>
              </div>
              <div>
                <strong>薄弱点</strong>
                <ul>
                  <li v-for="item in reflectionResult.weak_points || []" :key="item">{{ item }}</li>
                </ul>
              </div>
            </div>
            <div v-if="reflectionResult.next_recommendations?.length">
              <strong>下一步建议</strong>
              <ul>
                <li v-for="item in reflectionResult.next_recommendations" :key="item">{{ item }}</li>
              </ul>
            </div>
            <p v-if="reflectionResult.level_update">
              <strong>水平更新：</strong>{{ reflectionResult.level_update }}
            </p>
            <details v-if="reflectionResult.debug" class="debug-block">
              <summary>反思调试信息</summary>
              <pre>{{ JSON.stringify(reflectionResult.debug, null, 2) }}</pre>
            </details>
          </div>
        </section>
      </section>

      <section v-show="activeModule === 'materials'" class="module-page">
        <MaterialsPanel />
      </section>

      <section v-show="activeModule === 'evaluation'" class="module-page">
        <EvaluationDashboard />
      </section>
    </section>
  </main>
</template>
