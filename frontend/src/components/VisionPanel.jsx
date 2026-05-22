import { useState, useEffect } from 'react'
import { useStore } from '../store'
import { Camera, Eye, Loader2, Image as ImageIcon, AlertCircle, FileText, Settings, History } from 'lucide-react'

export default function VisionPanel() {
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [screenshots, setScreenshots] = useState([])
  const [activeTab, setActiveTab] = useState('analyze') // analyze, gallery, history, settings
  const [errorHistory, setErrorHistory] = useState([])
  const { captureScreenshot, describeScreen } = useStore()

  // Завантаження історії скріншотів
  useEffect(() => {
    loadScreenshots()
  }, [])

  const loadScreenshots = async () => {
    try {
      // TODO: API endpoint для отримання списку скріншотів
      // const response = await fetch('/api/vision/screenshots')
      // const data = await response.json()
      // setScreenshots(data.screenshots)
    } catch (e) {
      console.error('Failed to load screenshots:', e)
    }
  }

  const handleCapture = async () => {
    setAnalyzing(true)
    try {
      const data = await captureScreenshot()
      setResult(data)
      loadScreenshots() // Оновлюємо галерею
    } catch (e) {
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const data = await describeScreen(prompt || undefined)
      setResult(data)
    } catch (e) {
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleDetectErrors = async () => {
    setAnalyzing(true)
    try {
      const response = await fetch('/api/vision/detect-errors', { method: 'POST' })
      const data = await response.json()
      setResult(data)

      if (data.has_errors) {
        setErrorHistory(prev => [{
          timestamp: new Date().toISOString(),
          analysis: data.analysis,
          screenshot: data.screenshot
        }, ...prev.slice(0, 9)]) // Зберігаємо останні 10
      }
    } catch (e) {
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleReadText = async () => {
    setAnalyzing(true)
    try {
      const screenshot = await captureScreenshot()
      const response = await fetch('/api/vision/ocr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_path: screenshot.screenshot })
      })
      const data = await response.json()
      setResult({ ...screenshot, ocr_text: data.text })
    } catch (e) {
      console.error(e)
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="card">
        <div className="flex space-x-2 border-b border-dark-border pb-3">
          <button
            onClick={() => setActiveTab('analyze')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'analyze'
                ? 'bg-primary-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Eye size={18} className="inline mr-2" />
            Аналіз
          </button>
          <button
            onClick={() => setActiveTab('gallery')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'gallery'
                ? 'bg-primary-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <ImageIcon size={18} className="inline mr-2" />
            Галерея
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'history'
                ? 'bg-primary-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <History size={18} className="inline mr-2" />
            Історія
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeTab === 'settings'
                ? 'bg-primary-500 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Settings size={18} className="inline mr-2" />
            Налаштування
          </button>
        </div>
      </div>

      {/* Analyze Tab */}
      {activeTab === 'analyze' && (
        <>
          <div className="card">
            <div className="flex items-center space-x-2 mb-4">
              <Eye className="text-primary-500" />
              <h2 className="text-xl font-bold">Screen Understanding</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Промпт (опціонально)
                </label>
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Що ви хочете дізнатися про екран?"
                  className="input w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={handleCapture}
                  disabled={analyzing}
                  className="btn btn-secondary flex items-center justify-center space-x-2"
                >
                  {analyzing ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Camera size={18} />
                  )}
                  <span>Скріншот</span>
                </button>

                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="btn btn-primary flex items-center justify-center space-x-2"
                >
                  {analyzing ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Eye size={18} />
                  )}
                  <span>Аналіз</span>
                </button>

                <button
                  onClick={handleDetectErrors}
                  disabled={analyzing}
                  className="btn btn-secondary flex items-center justify-center space-x-2"
                >
                  {analyzing ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <AlertCircle size={18} />
                  )}
                  <span>Помилки</span>
                </button>

                <button
                  onClick={handleReadText}
                  disabled={analyzing}
                  className="btn btn-secondary flex items-center justify-center space-x-2"
                >
                  {analyzing ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <FileText size={18} />
                  )}
                  <span>OCR</span>
                </button>
              </div>
            </div>
          </div>

          {/* Result */}
          {result && (
            <div className="card animate-fadeIn">
              <h3 className="text-lg font-semibold mb-4">Результат</h3>

              {result.screenshot && (
                <div className="mb-4">
                  <div className="flex items-center space-x-2 text-sm text-gray-400 mb-2">
                    <ImageIcon size={16} />
                    <span>Скріншот: {result.screenshot.split('/').pop()}</span>
                  </div>
                </div>
              )}

              {result.description && (
                <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                  <p className="text-sm text-gray-300 whitespace-pre-wrap">
                    {result.description}
                  </p>
                </div>
              )}

              {result.has_errors !== undefined && (
                <div className={`mt-4 p-4 rounded-lg border ${
                  result.has_errors
                    ? 'bg-red-500/10 border-red-500/20'
                    : 'bg-green-500/10 border-green-500/20'
                }`}>
                  <div className="flex items-center space-x-2 mb-2">
                    <AlertCircle size={18} className={result.has_errors ? 'text-red-500' : 'text-green-500'} />
                    <span className="font-semibold">
                      {result.has_errors ? 'Виявлено помилки' : 'Помилок не виявлено'}
                    </span>
                  </div>
                  {result.analysis && (
                    <p className="text-sm text-gray-300">{result.analysis}</p>
                  )}
                </div>
              )}

              {result.ocr_text && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-gray-400 mb-2">
                    Розпізнаний текст (OCR):
                  </h4>
                  <div className="bg-dark-bg rounded-lg p-4 border border-dark-border max-h-48 overflow-y-auto">
                    <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                      {result.ocr_text}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Gallery Tab */}
      {activeTab === 'gallery' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Галерея скріншотів</h3>
          {screenshots.length > 0 ? (
            <div className="grid grid-cols-3 gap-4">
              {screenshots.map((screenshot, idx) => (
                <div key={idx} className="border border-dark-border rounded-lg p-2 hover:border-primary-500 transition-colors cursor-pointer">
                  <div className="aspect-video bg-dark-bg rounded flex items-center justify-center">
                    <ImageIcon size={32} className="text-gray-600" />
                  </div>
                  <p className="text-xs text-gray-400 mt-2 truncate">{screenshot.name}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <ImageIcon size={48} className="mx-auto mb-4 opacity-50" />
              <p>Скріншотів поки немає</p>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Історія виявлених помилок</h3>
          {errorHistory.length > 0 ? (
            <div className="space-y-3">
              {errorHistory.map((error, idx) => (
                <div key={idx} className="bg-dark-bg rounded-lg p-4 border border-red-500/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-400">
                      {new Date(error.timestamp).toLocaleString('uk-UA')}
                    </span>
                    <AlertCircle size={16} className="text-red-500" />
                  </div>
                  <p className="text-sm text-gray-300">{error.analysis}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <History size={48} className="mx-auto mb-4 opacity-50" />
              <p>Історія порожня</p>
            </div>
          )}
        </div>
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Налаштування Vision</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Якість стиснення JPEG (1-100)
              </label>
              <input
                type="range"
                min="1"
                max="100"
                defaultValue="85"
                className="w-full"
              />
              <span className="text-xs text-gray-500">85</span>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                TTL кешу (секунди)
              </label>
              <input
                type="number"
                defaultValue="300"
                className="input w-full"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Максимальна ширина зображення
              </label>
              <input
                type="number"
                defaultValue="1920"
                className="input w-full"
              />
            </div>

            <button className="btn btn-primary w-full">
              Зберегти налаштування
            </button>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="card bg-primary-500/10 border-primary-500/20">
        <p className="text-sm text-gray-300">
          💡 <strong>Підказка:</strong> Vision використовує Ollama LLaVA (локально).
          Скріншоти зберігаються в data/screenshots/.
        </p>
      </div>
    </div>
  )
}
