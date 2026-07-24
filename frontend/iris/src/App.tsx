import { useState } from 'react'
import PredictTab from './components/PredictTab'
import TrainTab from './components/TrainTab'
import type { TabType } from './types'

const TABS: { key: TabType; label: string; emoji: string }[] = [
  { key: 'predict', label: '即時模型預測', emoji: '🔮' },
  { key: 'train', label: '線上模型訓練', emoji: '⚙️' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('predict')

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 sm:py-5">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
            🌸 Iris 鳶尾花機器學習平台
          </h1>
          <p className="text-sm sm:text-base text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
            結合 <span className="font-semibold text-indigo-600 dark:text-indigo-400">FastAPI</span> 後端與
            <span className="font-semibold text-emerald-600 dark:text-emerald-400"> React</span> 前端的互動式 ML 部署平台。
            輸入花瓣特徵即時預測品種，或線上調整超參數重新訓練模型。
          </p>
        </div>
      </header>

      {/* Tab Bar */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 mt-6">
        <div className="flex bg-gray-100 dark:bg-gray-800 rounded-xl p-1 gap-1">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2.5 sm:py-3 rounded-lg text-sm sm:text-base font-bold transition-all duration-200 cursor-pointer ${
                activeTab === tab.key
                  ? 'bg-white dark:bg-gray-700 text-indigo-700 dark:text-indigo-300 shadow-md'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {tab.emoji} {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {activeTab === 'predict' ? <PredictTab /> : <TrainTab />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 mt-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 text-center text-xs text-gray-400 dark:text-gray-500">
          Iris ML Platform &middot; FastAPI + React + TypeScript + TailwindCSS
        </div>
      </footer>
    </div>
  )
}
