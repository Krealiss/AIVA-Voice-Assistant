import { useStore } from '../store'
import { Clock, CheckCircle, XCircle } from 'lucide-react'

export default function HistoryPanel() {
  const { history } = useStore()

  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4">Command History</h2>

      <div className="space-y-3">
        {history.length > 0 ? (
          history.map((item, idx) => (
            <HistoryItem key={idx} item={item} />
          ))
        ) : (
          <p className="text-sm text-gray-500 text-center py-8">
            No commands executed yet
          </p>
        )}
      </div>
    </div>
  )
}

function HistoryItem({ item }) {
  const timestamp = new Date(item.timestamp).toLocaleTimeString()

  return (
    <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            {item.success ? (
              <CheckCircle size={16} className="text-green-500" />
            ) : (
              <XCircle size={16} className="text-red-500" />
            )}
            <span className="text-sm font-medium text-gray-300">
              {item.command}
            </span>
          </div>
          <p className="text-sm text-gray-400 ml-6">{item.response}</p>
        </div>
        <div className="flex items-center space-x-1 text-xs text-gray-500">
          <Clock size={12} />
          <span>{timestamp}</span>
        </div>
      </div>

      {item.duration_ms && (
        <div className="text-xs text-gray-500 ml-6">
          Duration: {item.duration_ms.toFixed(0)}ms
        </div>
      )}
    </div>
  )
}
