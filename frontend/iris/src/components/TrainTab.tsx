import { useState } from 'react'
import { trainModel } from '../api'
import type { TrainConfig, TrainResult } from '../types'

const DEFAULT_CONFIG: TrainConfig = {
  n_estimators: 100,
  max_depth: 0,
  test_size: 0.2,
  random_state: 42,
}

const TRAIN_FIELDS: { key: keyof TrainConfig; label: string; labelEn: string; min: number; max: number; step: number }[] = [
  { key: 'n_estimators', label: '決策樹數量', labelEn: 'n_estimators', min: 10, max: 500, step: 10 },
  { key: 'max_depth', label: '最大深度 (0 = 無限制)', labelEn: 'max_depth', min: 0, max: 20, step: 1 },
  { key: 'test_size', label: '測試集比例', labelEn: 'test_size', min: 0.1, max: 0.5, step: 0.05 },
  { key: 'random_state', label: '隨機種子', labelEn: 'random_state', min: 0, max: 999, step: 1 },
]

const IMPORTANCE_COLORS = ['bg-indigo-500', 'bg-purple-500', 'bg-emerald-500', 'bg-orange-500']

export default function TrainTab() {
  const [config, setConfig] = useState<TrainConfig>({ ...DEFAULT_CONFIG })
  const [result, setResult] = useState<TrainResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusMsg, setStatusMsg] = useState('已載入預訓練模型 (就緒)')

  const handleChange = (key: keyof TrainConfig, val: number) => {
    setConfig(prev => ({ ...prev, [key]: val }))
  }

  const handleTrain = async () => {
    setLoading(true)
    setError(null)
    setStatusMsg('訓練中...')
    try {
      const res = await trainModel(config)
      setResult(res)
      setStatusMsg('✅ 線上重新訓練並載入成功！')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '訓練失敗')
      setStatusMsg('❌ 訓練失敗')
    } finally {
      setLoading(false)
    }
  }

  const sortedImportance = result
    ? Object.entries(result.feature_importances).sort((a, b) => b[1] - a[1])
    : []
  const maxImp = sortedImportance.length > 0 ? sortedImportance[0][1] : 1

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
      {/* Left: Hyperparameter Controls */}
      <div className="space-y-5">
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">1. 調整隨機森林超參數</h3>
        {TRAIN_FIELDS.map(f => (
          <div key={f.key}>
            <div className="flex justify-between mb-1.5">
              <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {f.label} <span className="text-gray-400 font-normal">{f.labelEn}</span>
              </label>
              <span className="text-sm font-mono font-bold text-indigo-600 dark:text-indigo-400">
                {config[f.key]}
              </span>
            </div>
            <input
              type="range"
              min={f.min}
              max={f.max}
              step={f.step}
              value={config[f.key]}
              onChange={e => handleChange(f.key, parseFloat(e.target.value))}
              className="w-full h-2 rounded-full appearance-none cursor-pointer bg-gray-200 dark:bg-gray-700 accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>{f.min}</span>
              <span>{f.max}</span>
            </div>
          </div>
        ))}
        <button
          onClick={handleTrain}
          disabled={loading}
          className="w-full py-3 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-200 dark:shadow-none"
        >
          {loading ? '訓練中...' : '🚀 開始訓練模型'}
        </button>
        <div className="text-center text-sm text-gray-500 dark:text-gray-400">
          📢 狀態：<code className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded font-mono text-xs">{statusMsg}</code>
        </div>
      </div>

      {/* Right: Results */}
      <div className="space-y-5">
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">2. 訓練結果與特徵重要性</h3>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        )}

        {result && (
          <>
            {/* Metrics Cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center border border-gray-100 dark:border-gray-700 shadow-sm">
                <p className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-gray-400">測試集準確度</p>
                <p className="text-xl sm:text-2xl font-extrabold text-blue-600 dark:text-blue-400 mt-1">
                  {(result.accuracy * 100).toFixed(2)}%
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center border border-gray-100 dark:border-gray-700 shadow-sm">
                <p className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-gray-400">訓練耗時</p>
                <p className="text-xl sm:text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                  {result.train_time.toFixed(4)}s
                </p>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-xl p-4 text-center border border-gray-100 dark:border-gray-700 shadow-sm">
                <p className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-gray-400">決策樹數量</p>
                <p className="text-xl sm:text-2xl font-extrabold text-purple-600 dark:text-purple-400 mt-1">
                  {config.n_estimators}
                </p>
              </div>
            </div>

            {/* Config Summary */}
            <div className="flex flex-wrap justify-between bg-gray-50 dark:bg-gray-800 rounded-xl px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300 border border-gray-100 dark:border-gray-700 gap-2">
              <span>🌲 <strong>最大樹深度:</strong> {config.max_depth === 0 ? '無限制' : config.max_depth}</span>
              <span>📊 <strong>測試集比例:</strong> {(config.test_size * 100).toFixed(0)}%</span>
            </div>

            {/* Feature Importance */}
            {sortedImportance.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-md border border-gray-100 dark:border-gray-700 space-y-3">
                <h4 className="text-sm font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                  💡 特徵重要性分析 (Feature Importance)
                </h4>
                {sortedImportance.map(([name, val], idx) => {
                  const pct = (val / maxImp) * 100
                  return (
                    <div key={name}>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 capitalize">{name}</span>
                        <span className="text-sm font-mono font-bold text-gray-600 dark:text-gray-400">{(val * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ease-out ${IMPORTANCE_COLORS[idx % IMPORTANCE_COLORS.length]}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </>
        )}

        {!result && !loading && !error && (
          <div className="text-center text-gray-400 dark:text-gray-500 py-12 text-sm">
            調整超參數後點擊「開始訓練模型」即可查看結果
          </div>
        )}
      </div>
    </div>
  )
}
