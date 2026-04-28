import { useState } from 'react'
import { useStore } from '../store'
import { Camera, Eye, Loader2, Image as ImageIcon } from 'lucide-react'

export default function VisionPanel() {
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [prompt, setPrompt] = useState('')
  const { captureScreenshot, describeScreen } = useStore()

  const handleCapture = async () => {
    setAnalyzing(true)
    try {
      const data = await captureScreenshot()
      setResult(data)
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

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-4">
          <Eye className="text-primary-500" />
          <h2 className="text-xl font-bold">Screen Understanding</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Custom Prompt (optional)
            </label>
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="What do you want to know about the screen?"
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
              <span>Capture</span>
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
              <span>Analyze</span>
            </button>
          </div>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="card animate-fadeIn">
          <h3 className="text-lg font-semibold mb-4">Analysis Result</h3>

          {result.screenshot && (
            <div className="mb-4">
              <div className="flex items-center space-x-2 text-sm text-gray-400 mb-2">
                <ImageIcon size={16} />
                <span>Screenshot saved: {result.screenshot.split('/').pop()}</span>
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

          {result.ocr_text && (
            <div className="mt-4">
              <h4 className="text-sm font-semibold text-gray-400 mb-2">
                Extracted Text (OCR):
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

      {/* Info */}
      <div className="card bg-primary-500/10 border-primary-500/20">
        <p className="text-sm text-gray-300">
          💡 <strong>Tip:</strong> Vision features require ANTHROPIC_API_KEY in .env file.
          Screenshots are saved to data/screenshots/ folder.
        </p>
      </div>
    </div>
  )
}
