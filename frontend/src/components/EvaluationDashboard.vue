<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getEvaluationEvents, getEvaluationSummary, type EvaluationSummary } from '../services/api'

const summary = ref<EvaluationSummary | null>(null)
const events = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const error = ref('')

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    summary.value = await getEvaluationSummary()
    const eventResponse = await getEvaluationEvents()
    events.value = eventResponse.events
  } catch (err) {
    error.value = err instanceof Error ? err.message : '读取评估数据失败。'
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="exercise-workspace">
    <div class="exercise-toolbar">
      <div>
        <p class="eyebrow">Evaluation</p>
        <h2>学习数据看板</h2>
      </div>
      <div class="plan-actions">
        <a class="secondary-button link-button" href="/api/evaluation/export.json" target="_blank">导出 JSON</a>
        <a class="secondary-button link-button" href="/api/evaluation/export.csv" target="_blank">导出 CSV</a>
        <button class="secondary-button" type="button" :disabled="loading" @click="refresh">
          {{ loading ? '刷新中...' : '刷新' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section v-if="summary" class="metric-grid">
      <div class="metric-card">
        <strong>{{ summary.material_count }}</strong>
        <span>资料数</span>
      </div>
      <div class="metric-card">
        <strong>{{ summary.memory_count }}</strong>
        <span>记忆记录</span>
      </div>
      <div class="metric-card">
        <strong>{{ summary.grading_count }}</strong>
        <span>批改次数</span>
      </div>
      <div class="metric-card">
        <strong>{{ summary.average_score ?? '-' }}</strong>
        <span>平均分</span>
      </div>
      <div class="metric-card">
        <strong>{{ summary.weak_point_count }}</strong>
        <span>薄弱点</span>
      </div>
      <div class="metric-card">
        <strong>{{ summary.event_count }}</strong>
        <span>协调调用</span>
      </div>
    </section>

    <section v-if="summary" class="result-grid">
      <div class="info-block">
        <h3>Intent 分布</h3>
        <ul class="step-list">
          <li v-for="(count, intent) in summary.intent_distribution" :key="intent">
            {{ intent }}：{{ count }}
          </li>
        </ul>
      </div>
      <div class="info-block">
        <h3>论文指标覆盖</h3>
        <ul class="step-list">
          <li>RAG 命中资料数量：由回答 debug 与资料索引统计支撑</li>
          <li>练习正确率：由批改记忆中的 score/is_correct 支撑</li>
          <li>薄弱点变化：由 StudentProfile weak_points 支撑</li>
          <li>平均响应时间：由协调器日志 elapsed_ms 支撑</li>
        </ul>
      </div>
    </section>

    <div class="data-table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>学生</th>
            <th>Intent</th>
            <th>结果</th>
            <th>耗时</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in events.slice().reverse()" :key="String(event.created_at) + String(event.intent)">
            <td>{{ event.created_at }}</td>
            <td>{{ event.student_id || '-' }}</td>
            <td>{{ event.intent }}</td>
            <td>{{ event.success ? '成功' : '失败' }}</td>
            <td>{{ event.elapsed_ms }} ms</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
