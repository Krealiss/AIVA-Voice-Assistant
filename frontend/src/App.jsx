import { useEffect } from 'react'
import { useStore } from './store'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import CommandPanel from './components/CommandPanel'
import LearningPanel from './components/LearningPanel'
import VisionPanel from './components/VisionPanel'
import HistoryPanel from './components/HistoryPanel'
import ContextPanel from './components/ContextPanel'
import MacroPanel from './components/MacroPanel'

function App() {
  const { activeTab, connectWebSocket, fetchStats, fetchHistory, fetchLearningData, fetchSession, fetchUserProfile } = useStore()

  useEffect(() => {
    // Connect WebSocket
    connectWebSocket()

    // Initial data fetch
    fetchStats()
    fetchHistory()
    fetchLearningData()
    fetchSession()
    fetchUserProfile()

    // Periodic refresh
    const interval = setInterval(() => {
      fetchStats()
      fetchLearningData()
    }, 30000) // Every 30 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-dark-bg">
      <Header />

      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {activeTab === 'dashboard' && <Dashboard />}
            {activeTab === 'learning' && <LearningPanel />}
            {activeTab === 'vision' && <VisionPanel />}
            {activeTab === 'history' && <HistoryPanel />}
            {activeTab === 'context' && <ContextPanel />}
            {activeTab === 'macros' && <MacroPanel />}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <CommandPanel />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
