/**
 * OCR API 客户端
 * 支持 PaddleOCR / EasyOCR 多方案识别
 */

const BASE = '/api/ocr'

export async function recognizeFromFile(fileId, includeBoxes = false) {
  const body = new FormData()
  body.append('file_id', fileId)
  body.append('include_boxes', includeBoxes)

  const res = await fetch(`${BASE}/recognize`, { method: 'POST', body })
  return res.json()
}

export async function recognizeImage(file, includeBoxes = false) {
  const body = new FormData()
  body.append('file', file)
  body.append('include_boxes', includeBoxes)

  const res = await fetch(`${BASE}/recognize`, { method: 'POST', body })
  return res.json()
}

export async function listProviders() {
  const res = await fetch(`${BASE}/providers`)
  return res.json()
}
