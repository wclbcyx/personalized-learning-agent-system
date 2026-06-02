export interface MaterialInfo {
  file_name: string
  relative_path: string
  suffix: string
  size_bytes: number
  course_name?: string | null
  indexed: boolean
}

export interface MaterialListResponse {
  materials: MaterialInfo[]
  index_status: Record<string, unknown>
}

export async function listMaterials(): Promise<MaterialListResponse> {
  const response = await fetch('/api/materials')

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `读取资料失败：${response.status}`)
  }

  return response.json()
}

export async function uploadMaterial(file: File, courseName?: string): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  if (courseName?.trim()) {
    formData.append('course_name', courseName.trim())
  }

  const response = await fetch('/api/materials/upload', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `上传资料失败：${response.status}`)
  }

  return response.json()
}
