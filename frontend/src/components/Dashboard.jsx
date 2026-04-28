import { useStore } from '../store'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, CheckCircle, XCircle, Clock } from 'lucide-react'

export default function Dashboard() {
  const { stats, patterns, feedback } = useStore()

  const successData = [
    { name: 'Success', value: stats.successRate || 0, color: '#10b981' },
    { name: 'Failed', value: 100 - (stats.successRate || 0), color: '#ef4444' }
  ]

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<TrendingUp className="text-primary-500" />}
          label="Total Commands"
          value={stats.totalCommands || 0}
        />
        <StatCard
          icon={<CheckCircle className="text-green-500" />}
          label="Success Rate"
          value={`${(stats.successRate || 0).toFixed(1)}%`}
        />
        <StatCard
          icon={<Clock className="text-blue-500" />}
          label="Avg Response"
          value={`${(stats.avgResponseTime || 0).toFixed(0)}ms`}
        />
        <StatCard
          icon={<XCircle className="text-yellow-500" />}
          label="Avg Rating"
          value={`${(feedback.averageRating || 0).toFixed(1)} ⭐`}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Success Rate Pie */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Success Rate</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={successData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={5}
                dataKey="value"
              >
                {successData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center space-x-4 mt-4">
            {successData.map((item) => (
              <div key={item.name} className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-sm text-gray-400">{item.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Patterns */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Detected Patterns</h3>
          <div className="space-y-3">
            {patterns.length > 0 ? (
              patterns.slice(0, 5).map((pattern, idx) => (
                <div key={idx} className="bg-dark-bg rounded-lg p-3 border border-dark-border">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-300">{pattern.description}</span>
                    <span className="text-xs text-primary-500">
                      {(pattern.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 text-center py-8">
                No patterns detected yet. Keep using AIVA!
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value }) {
  return (
    <div className="card">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-dark-bg rounded-lg">
          {icon}
        </div>
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </div>
    </div>
  )
}
