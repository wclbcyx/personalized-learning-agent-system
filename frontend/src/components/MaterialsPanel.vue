<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listMaterials, uploadMaterial, type MaterialInfo } from '../services/materials'

const materials = ref<MaterialInfo[]>([])
const indexStatus = ref<Record<string, unknown>>({})
const courseName = ref('初中数学')
const selectedFile = ref<File | null>(null)
const loading = ref(false)
const error = ref('')
const message = ref('')

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] || null
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const response = await listMaterials()
    materials.value = response.materials
    indexStatus.value = response.index_status
  } catch (err) {
    error.value = err instanceof Error ? err.message : '读取资料失败。'
  } finally {
    loading.value = false
  }
}

async function submitUpload() {
  if (!selectedFile.value) {
    error.value = '请先选择一个资料文件。'
    return
  }

  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const response = await uploadMaterial(selectedFile.value, courseName.value)
    message.value = String(response.message || '上传成功。')
    await refresh()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '上传失败。'
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
        <p class="eyebrow">Knowledge Base</p>
        <h2>资料管理</h2>
      </div>
      <button class="secondary-button" type="button" :disabled="loading" @click="refresh">
        {{ loading ? '刷新中...' : '刷新资料' }}
      </button>
    </div>

    <div class="utility-grid">
      <label>
        <span>课程名称</span>
        <input v-model="courseName" autocomplete="off" />
      </label>
      <label>
        <span>上传资料</span>
        <input type="file" accept=".md,.markdown,.txt,.pdf" @change="onFileChange" />
      </label>
      <button class="primary-button" type="button" :disabled="loading" @click="submitUpload">
        上传到知识库
      </button>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>
    <p v-if="message" class="hint">{{ message }}</p>

    <section class="metric-grid">
      <div class="metric-card">
        <strong>{{ materials.length }}</strong>
        <span>资料文件</span>
      </div>
      <div class="metric-card">
        <strong>{{ indexStatus.chunk_count ?? 0 }}</strong>
        <span>可检索片段</span>
      </div>
      <div class="metric-card">
        <strong>{{ indexStatus.retrieval_mode || 'local_keyword_rag' }}</strong>
        <span>检索模式</span>
      </div>
    </section>

    <div class="data-table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>文件</th>
            <th>课程</th>
            <th>类型</th>
            <th>大小</th>
            <th>索引</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in materials" :key="item.relative_path">
            <td>
              <strong>{{ item.file_name }}</strong>
              <small>{{ item.relative_path }}</small>
            </td>
            <td>{{ item.course_name || '默认' }}</td>
            <td>{{ item.suffix }}</td>
            <td>{{ Math.round(item.size_bytes / 1024) }} KB</td>
            <td>{{ item.indexed ? '已进入 RAG' : '已保存' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
