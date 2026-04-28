import { useStore } from '../store'
import { Activity, Brain, Eye, History, MessageSquare, Wifi, WifiOff } from 'lucide-react'

export default function Header() {
  const { activeTab, setActiveTab, connected } = useStore()

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'context', label: 'Context', icon: MessageSquare },
    { id: 'learning', label: 'Learning', icon: Brain },
    { id: 'vision', label: 'Vision', icon: Eye },
    { id: 'history', label: 'History', icon: History },
  ]

  return (
    <header className="bg-dark-card border-b border-dark-border sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">A</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AIVA</h1>
              <p className="text-xs text-gray-400">AI Voice Assistant</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center space-x-2 px-4 py-2 rounded-lg transition-all
                    ${isActive
                      ? 'bg-primary-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-dark-bg'
                    }
                  `}
                >
                  <Icon size={18} />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </nav>

          {/* Connection status */}
          <div className="flex items-center space-x-2">
            {connected ? (
              <>
                <Wifi size={18} className="text-green-500" />
                <span className="text-sm text-gray-400 hidden sm:inline">Connected</span>
              </>
            ) : (
              <>
                <WifiOff size={18} className="text-red-500" />
                <span className="text-sm text-gray-400 hidden sm:inline">Disconnected</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
