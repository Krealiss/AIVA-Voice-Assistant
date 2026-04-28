import { useState } from 'react'
import { useStore } from '../store'
import { Send, Loader2, Star } from 'lucide-react'

export default function CommandPanel() {
  const [command, setCommand] = useState('')
  const [response, setResponse] = useState('')
  const [rating, setRating] = useState(0)
  const { executeCommand, rateResponse, loading } = useStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!command.trim() || loading) return

    try {
      const result = await executeCommand(command)
      setResponse(result)
      setRating(0)
    } catch (e) {
      setResponse(`Error: ${e.message}`)
    }
  }

  const handleRate = async (stars) => {
    setRating(stars)
    if (command && response) {
      await rateResponse(command, response, stars)
    }
  }

  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4">Execute Command</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Enter command..."
            className="input w-full"
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          disabled={loading || !command.trim()}
          className="btn btn-primary w-full flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              <span>Processing...</span>
            </>
          ) : (
            <>
              <Send size={18} />
              <span>Execute</span>
            </>
          )}
        </button>
      </form>

      {response && (
        <div className="mt-4 space-y-3 animate-fadeIn">
          <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <p className="text-sm text-gray-300">{response}</p>
          </div>

          {/* Rating */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Rate this response:</span>
            <div className="flex space-x-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleRate(star)}
                  className="transition-transform hover:scale-110"
                >
                  <Star
                    size={20}
                    className={star <= rating ? 'fill-yellow-500 text-yellow-500' : 'text-gray-600'}
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
