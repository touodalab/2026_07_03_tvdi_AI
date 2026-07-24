import { useState, useEffect, useCallback } from 'react'
import { predict } from '../api'
import type { IrisInput, IrisOutput } from '../types'

const DEFAULTS: IrisInput = {
  sepal_length: 5.1,
  sepal_width: 3.5,
  petal_length: 1.4,
  petal_width: 0.2,
}

const FIELDS: { key: keyof IrisInput; label: string; labelEn: string; unit: string; min: number; max: number; step: number }[] = [
  { key: 'sepal_length', label: '花萼長度', labelEn: 'Sepal Length', unit: 'cm', min: 0.1, max: 10, step: 0.1 },
  { key: 'sepal_width', label: '花萼寬度', labelEn: 'Sepal Width', unit: 'cm', min: 0.1, max: 10, step: 0.1 },
  { key: 'petal_length', label: '花瓣長度', labelEn: 'Petal Length', unit: 'cm', min: 0.1, max: 10, step: 0.1 },
  { key: 'petal_width', label: '花瓣寬度', labelEn: 'Petal Width', unit: 'cm', min: 0.1, max: 10, step: 0.1 },
]

const SPECIES_CONFIG: Record<string, { bg: string; border: string; text: string; emoji: string; name: string }> = {
  setosa: { bg: 'bg-emerald-50', border: 'border-emerald-300', text: 'text-emerald-800', emoji: '🌿', name: 'Setosa (山鳶尾)' },
  versicolor: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-800', emoji: '🍁', name: 'Versicolor (變色鳶尾)' },
  virginica: { bg: 'bg-rose-50', border: 'border-rose-300', text: 'text-rose-800', emoji: '🪻', name: 'Virginica (維吉尼亞鳶尾)' },
}

const BAR_COLORS: Record<string, string> = {
  setosa: 'bg-emerald-500',
  versicolor: 'bg-amber-500',
  virginica: 'bg-rose-500',
}

export default function PredictTab() {
  const [values, setValues] = useState<IrisInput>({ ...DEFAULTS })
  const [result, setResult] = useState<IrisOutput | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const doPredict = useCallback(async (inputs: IrisInput) => {
    setLoading(true)
    setError(null)
    try {
      const res = await predict(inputs)
      setResult(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '預測失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => doPredict(values), 300)
    return () => clearTimeout(timer)
  }, [values, doPredict])

  const handleChange = (key: keyof IrisInput, val: number) => {
    setValues(prev => ({ ...prev, [key]: val }))
  }

  const species = result?.prediction_label ?? 'setosa'
  const config = SPECIES_CONFIG[species] ?? SPECIES_CONFIG.setosa

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
      {/* Left: Input Controls */}
      <div className="space-y-5">
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">1. 輸入特徵值 (Features)</h3>
        {FIELDS.map(f => (
          <div key={f.key}>
            <div className="flex justify-between mb-1.5">
              <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {f.label} <span className="text-gray-400 font-normal">{f.labelEn}</span>
              </label>
              <span className="text-sm font-mono font-bold text-indigo-600 dark:text-indigo-400">
                {values[f.key].toFixed(1)} {f.unit}
              </span>
            </div>
            <input
              type="range"
              min={f.min}
              max={f.max}
              step={f.step}
              value={values[f.key]}
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
          onClick={() => doPredict(values)}
          disabled={loading}
          className="w-full py-3 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-200 dark:shadow-none"
        >
          {loading ? '預測中...' : '🔮 開始預測'}
        </button>
      </div>

      {/* Right: Results */}
      <div className="space-y-5">
        <h3 className="text-lg font-bold text-gray-800 dark:text-gray-100">2. 預測結果與機率分析</h3>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Prediction Card */}
        {result && (
          <div className={`${config.bg} ${config.border} border-2 rounded-2xl p-6 text-center shadow-md transition-all duration-300`}>
            <p className="text-xs font-bold uppercase tracking-widest opacity-60 mb-1">預測分析品種</p>
            <p className={`text-3xl sm:text-4xl font-extrabold ${config.text} my-2`}>
              {config.emoji} {config.name}
            </p>
            <p className={`text-lg font-medium ${config.text}`}>
              預測機率：<span className="font-extrabold text-xl">{((result.probabilities[species] ?? 0) * 100).toFixed(1)}%</span>
            </p>
          </div>
        )}

        {/* Probability Bars */}
        {result && (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-5 shadow-md border border-gray-100 dark:border-gray-700 space-y-4">
            <h4 className="text-sm font-bold text-gray-600 dark:text-gray-300 uppercase tracking-wide">各品種機率分佈</h4>
            {Object.entries(result.probabilities).map(([name, prob]) => {
              const pct = prob * 100
              return (
                <div key={name}>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 capitalize">{name}</span>
                    <span className="text-sm font-mono font-bold text-gray-600 dark:text-gray-400">{pct.toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ease-out ${BAR_COLORS[name] ?? 'bg-indigo-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {!result && !loading && !error && (
          <div className="text-center text-gray-400 dark:text-gray-500 py-12 text-sm">
            拖動左側滑桿即可即時預測
          </div>
        )}
      </div>
    </div>
  )
}
