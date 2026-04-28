import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // WebSocket
  ws: null,
  connected: false,

  // System stats
  stats: {
    uptime: 0,
    totalCommands: 0,
    successRate: 0,
    avgResponseTime: 0
  },

  // Command history
  history: [],

  // Learning data
  habits: [],
  patterns: [],
  feedback: {
    averageRating: 0,
    totalFeedback: 0
  },

  // Vision
  screenshots: [],

  // Context & User Profile
  currentSession: null,
  conversationHistory: [],
  userProfile: null,

  // UI state
  activeTab: 'dashboard',
  loading: false,
  error: null,

  // Actions
  setConnected: (connected) => set({ connected }),

  setStats: (stats) => set({ stats }),

  addHistory: (command) => set((state) => ({
    history: [command, ...state.history].slice(0, 50)
  })),

  setHistory: (history) => set({ history }),

  setHabits: (habits) => set({ habits }),

  setPatterns: (patterns) => set({ patterns }),

  setFeedback: (feedback) => set({ feedback }),

  setScreenshots: (screenshots) => set({ screenshots }),

  setCurrentSession: (session) => set({ currentSession: session }),

  setConversationHistory: (history) => set({ conversationHistory: history }),

  setUserProfile: (profile) => set({ userProfile: profile }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  // WebSocket connection
  connectWebSocket: () => {
    const wsUrl = `ws://${window.location.hostname}:8787/ws/dashboard`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      set({ connected: true, ws })
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'command') {
          get().addHistory(data)
        } else if (data.type === 'stats') {
          get().setStats(data.stats)
        } else if (data.type === 'suggestion') {
          // Handle habit suggestion
          console.log('Suggestion:', data.text)
        }
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      set({ connected: false })
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      set({ connected: false, ws: null })

      // Reconnect after 5 seconds
      setTimeout(() => {
        get().connectWebSocket()
      }, 5000)
    }
  },

  // API calls
  fetchStats: async () => {
    try {
      const response = await fetch('/api/dashboard/stats')
      const data = await response.json()
      set({ stats: data })
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  },

  fetchHistory: async () => {
    try {
      const response = await fetch('/api/dashboard/history?limit=50')
      const data = await response.json()
      set({ history: data })
    } catch (e) {
      console.error('Failed to fetch history:', e)
    }
  },

  fetchLearningData: async () => {
    try {
      const [habitsRes, feedbackRes] = await Promise.all([
        fetch('/api/learning/habits'),
        fetch('/api/learning/feedback/stats')
      ])

      const habits = await habitsRes.json()
      const feedback = await feedbackRes.json()

      set({
        habits: habits.habits || [],
        feedback: {
          averageRating: feedback.average_rating || 0,
          totalFeedback: feedback.total_feedback || 0
        }
      })
    } catch (e) {
      console.error('Failed to fetch learning data:', e)
    }
  },

  executeCommand: async (command) => {
    set({ loading: true, error: null })

    try {
      const response = await fetch('/api/dashboard/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command })
      })

      const data = await response.json()

      if (data.ok) {
        get().addHistory({
          command,
          response: data.result.text,
          timestamp: new Date().toISOString(),
          success: true
        })
        return data.result.text
      } else {
        throw new Error(data.error || 'Command failed')
      }
    } catch (e) {
      set({ error: e.message })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  rateResponse: async (command, response, rating) => {
    try {
      await fetch('/api/learning/feedback/rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, response, rating })
      })
    } catch (e) {
      console.error('Failed to rate response:', e)
    }
  },

  captureScreenshot: async () => {
    try {
      const response = await fetch('/api/vision/screenshot', {
        method: 'POST'
      })
      const data = await response.json()
      return data
    } catch (e) {
      console.error('Failed to capture screenshot:', e)
      throw e
    }
  },

  describeScreen: async (prompt) => {
    try {
      const response = await fetch('/api/vision/describe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })
      const data = await response.json()
      return data
    } catch (e) {
      console.error('Failed to describe screen:', e)
      throw e
    }
  },

  // Context API calls
  fetchSession: async (userId = 'default') => {
    try {
      const response = await fetch(`/api/context/session/active/${userId}`)
      const data = await response.json()
      set({ currentSession: data })
      return data
    } catch (e) {
      console.error('Failed to fetch session:', e)
    }
  },

  fetchConversationHistory: async () => {
    try {
      const session = get().currentSession
      if (!session) {
        await get().fetchSession()
      }

      const sessionId = get().currentSession?.session_id
      if (!sessionId) return

      const response = await fetch(`/api/context/window/${sessionId}`)
      const data = await response.json()
      set({ conversationHistory: data })
    } catch (e) {
      console.error('Failed to fetch conversation history:', e)
    }
  },

  fetchUserProfile: async (userId = 'default') => {
    try {
      const response = await fetch(`/api/users/profile/${userId}`)
      if (response.ok) {
        const data = await response.json()
        set({ userProfile: data })
      } else if (response.status === 404) {
        // Create default profile
        const createResponse = await fetch('/api/users/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            name: 'User',
            timezone: 'Europe/Kiev',
            language: 'uk'
          })
        })
        if (createResponse.ok) {
          const data = await createResponse.json()
          set({ userProfile: data })
        }
      }
    } catch (e) {
      console.error('Failed to fetch user profile:', e)
    }
  },

  clearHistory: async () => {
    try {
      const sessionId = get().currentSession?.session_id
      if (!sessionId) return

      await fetch(`/api/context/history/${sessionId}`, {
        method: 'DELETE'
      })

      set({ conversationHistory: [] })
    } catch (e) {
      console.error('Failed to clear history:', e)
      throw e
    }
  },

  endSession: async () => {
    try {
      const sessionId = get().currentSession?.session_id
      if (!sessionId) return

      await fetch(`/api/context/session/${sessionId}/end`, {
        method: 'POST'
      })

      // Create new session
      await get().fetchSession()
      set({ conversationHistory: [] })
    } catch (e) {
      console.error('Failed to end session:', e)
      throw e
    }
  }
}))
