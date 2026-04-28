import { useStore } from '../store'
import { Brain, ThumbsUp, ThumbsDown, TrendingUp } from 'lucide-react'

export default function LearningPanel() {
  const { habits, feedback } = useStore()

  return (
    <div className="space-y-6">
      {/* Habits */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-4">
          <Brain className="text-primary-500" />
          <h2 className="text-xl font-bold">Learned Habits</h2>
        </div>

        <div className="space-y-3">
          {habits.length > 0 ? (
            habits.map((habit) => (
              <HabitCard key={habit.id} habit={habit} />
            ))
          ) : (
            <p className="text-sm text-gray-500 text-center py-8">
              No habits learned yet. AIVA is observing your patterns...
            </p>
          )}
        </div>
      </div>

      {/* Feedback Stats */}
      <div className="card">
        <div className="flex items-center space-x-2 mb-4">
          <TrendingUp className="text-green-500" />
          <h2 className="text-xl font-bold">Feedback Statistics</h2>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <p className="text-sm text-gray-400 mb-1">Average Rating</p>
            <p className="text-3xl font-bold text-yellow-500">
              {feedback.averageRating.toFixed(1)} ⭐
            </p>
          </div>
          <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <p className="text-sm text-gray-400 mb-1">Total Feedback</p>
            <p className="text-3xl font-bold text-primary-500">
              {feedback.totalFeedback}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function HabitCard({ habit }) {
  const acceptanceRate = habit.times_observed > 0
    ? (habit.times_accepted / habit.times_observed * 100).toFixed(0)
    : 0

  return (
    <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <p className="text-sm text-gray-300 mb-1">{habit.description}</p>
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <span className="px-2 py-1 bg-dark-card rounded">
              {habit.type}
            </span>
            <span>Confidence: {(habit.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center space-x-1 text-xs">
            <ThumbsUp size={14} className="text-green-500" />
            <span className="text-gray-400">{habit.times_accepted}</span>
          </div>
          <div className="flex items-center space-x-1 text-xs mt-1">
            <ThumbsDown size={14} className="text-red-500" />
            <span className="text-gray-400">{habit.times_rejected}</span>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>Acceptance Rate</span>
          <span>{acceptanceRate}%</span>
        </div>
        <div className="w-full bg-dark-card rounded-full h-2">
          <div
            className="bg-primary-500 h-2 rounded-full transition-all"
            style={{ width: `${acceptanceRate}%` }}
          />
        </div>
      </div>
    </div>
  )
}
