import type { IrisInput, IrisOutput, TrainConfig, TrainResult } from './types'

const API_BASE = import.meta.env.DEV
  ? ''
  : 'https://two026-07-03-tvdi-ai.onrender.com'

export async function predict(input: IrisInput): Promise<IrisOutput> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '預測失敗')
  }
  return res.json()
}

export async function trainModel(config: TrainConfig): Promise<TrainResult> {
  const res = await fetch(`${API_BASE}/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '訓練失敗')
  }
  return res.json()
}
