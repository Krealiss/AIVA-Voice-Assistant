import { useEffect } from 'react'
import { useStore } from '../store'
import { MessageSquare, Trash2, User, Clock, CheckCircle } from 'lucide-react'

export default function ContextPanel() {
  const {
    currentSession,
    conversationHistory,
    userProfile,
    fetchSession,
    fetchConversationHistory,
    fetchUserProfile,
    clearHistory,
    loading
  } = useStore()

  useEffect(() => {
    fetchSession()
    fetchConversationHistory()
    fetchUserProfile()
  }, [])

  const handleClearHistory = async () => {
    if (confirm('Очистити історію розмов?')) {
      await clearHistory()
    }
  }

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })
  }

  const formatDate = (timestamp) => {
    const date = new Date(timestamp)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === today.toDateString()) {
      return 'Сьогодні'
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Вчора'
    } else {
      return date.toLocaleDateString('uk-UA', { day: 'numeric', month: 'short' })
    }
  }

  return (
    <div className="space-y-6">
      {/* User Profile Card */}
      {userProfile && (
        <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <User className="w-5 h-5 text-primary" />
              Профіль
            </h3>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Ім'я:</span>
              <span className="text-white font-medium">{userProfile.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Мова:</span>
              <span className="text-white">{userProfile.language === 'uk' ? '🇺🇦 Українська' : userProfile.language}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Часовий пояс:</span>
              <span className="text-white text-xs">{userProfile.timezone}</span>
            </div>
          </div>
        </div>
      )}

      {/* Session Info */}
      {currentSession && (
        <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-primary" />
              Поточна сесія
            </h3>
            {currentSession.is_active && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="w-3 h-3" />
                Активна
              </span>
            )}
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-gray-400">
              <Clock className="w-4 h-4" />
              <span>Початок: {formatDate(currentSession.start_time)} о {formatTime(currentSession.start_time)}</span>
            </div>
            <div className="text-xs text-gray-500">
              ID: {currentSession.session_id.slice(0, 20)}...
            </div>
          </div>
        </div>
      )}

      {/* Conversation History */}
      <div className="bg-dark-card rounded-lg p-4 border border-dark-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" />
            Історія розмов
          </h3>
          {conversationHistory.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="text-red-400 hover:text-red-300 transition-colors"
              title="Очистити історію"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-2 text-sm">Завантаження...</p>
          </div>
        ) : conversationHistory.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Історія порожня</p>
            <p className="text-xs mt-1">Почніть діалог з AIVA</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar">
            {conversationHistory.map((msg, idx) => (
              <div
                key={msg.message_id || idx}
                className={`p-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-primary/10 border border-primary/20 ml-4'
                    : 'bg-dark-bg border border-dark-border mr-4'
                }`}
              >
                <div className="flex items-start justify-between mb-1">
                  <span className={`text-xs font-medium ${
                    msg.role === 'user' ? 'text-primary' : 'text-purple-400'
                  }`}>
                    {msg.role === 'user' ? '👤 Ви' : '🤖 AIVA'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatTime(msg.timestamp)}
                  </span>
                </div>
                <p className="text-sm text-gray-200 whitespace-pre-wrap break-words">
                  {msg.content}
                </p>
              </div>
            ))}
          </div>
        )}

        {conversationHistory.length > 0 && (
          <div className="mt-3 pt-3 border-t border-dark-border text-xs text-gray-500 text-center">
            {conversationHistory.length} повідомлень у контексті
          </div>
        )}
      </div>
    </div>
  )
}
