import { useState, useEffect, useCallback } from 'react'
import { Play, Trash2, Plus, X, ChevronDown, ChevronUp, Zap } from 'lucide-react'

const API = 'http://localhost:8787/api/macros/'

export default function MacroPanel() {
  const [macros, setMacros] = useState([])
  const [loading, setLoading] = useState(false)
  const [runningId, setRunningId] = useState(null)
  const [runResult, setRunResult] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [form, setForm] = useState({ name: '', triggers: '', commands: '' })
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchMacros = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(API)
      if (res.ok) setMacros(await res.json())
    } catch (_) {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchMacros() }, [fetchMacros])

  async function runMacro(id) {
    setRunningId(id)
    setRunResult(null)
    try {
      const res = await fetch(`${API}${id}/run`, { method: 'POST' })
      const data = await res.json()
      setRunResult({ ok: data.ok, text: data.summary || 'Виконано', macro: data.macro })
      fetchMacros()
    } catch (_) {
      setRunResult({ ok: false, text: 'Помилка зв\'язку з сервером' })
    }
    setRunningId(null)
  }

  async function deleteMacro(id, name) {
    if (!confirm(`Видалити макрос "${name}"?`)) return
    try {
      await fetch(`${API}${id}`, { method: 'DELETE' })
      setMacros(prev => prev.filter(m => m.id !== id))
      if (runResult?.macro === name) setRunResult(null)
    } catch (_) {}
  }

  async function createMacro(e) {
    e.preventDefault()
    setFormError('')
    const name = form.name.trim()
    const triggers = form.triggers.split(',').map(t => t.trim()).filter(Boolean)
    const commands = form.commands.split('\n').map(c => c.trim()).filter(Boolean)

    if (!name) return setFormError('Вкажіть назву')
    if (!triggers.length) return setFormError('Вкажіть хоча б один тригер')
    if (!commands.length) return setFormError('Вкажіть хоча б одну команду')

    setSubmitting(true)
    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, triggers, commands }),
      })
      if (res.ok) {
        setForm({ name: '', triggers: '', commands: '' })
        setShowForm(false)
        fetchMacros()
      } else {
        const err = await res.json()
        setFormError(err.detail || 'Помилка створення')
      }
    } catch (_) {
      setFormError('Немає зв\'язку з сервером')
    }
    setSubmitting(false)
  }

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Zap size={20} className="text-yellow-400" />
          <h2 className="text-lg font-semibold">Макроси</h2>
          {macros.length > 0 && (
            <span className="text-xs bg-dark-bg text-gray-400 px-2 py-0.5 rounded-full">
              {macros.length}
            </span>
          )}
        </div>
        <button
          onClick={() => { setShowForm(v => !v); setFormError('') }}
          className="flex items-center space-x-1 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm transition-colors"
        >
          {showForm ? <X size={16} /> : <Plus size={16} />}
          <span>{showForm ? 'Скасувати' : 'Новий'}</span>
        </button>
      </div>

      {/* Result banner */}
      {runResult && (
        <div className={`flex items-start justify-between rounded-lg p-3 text-sm ${
          runResult.ok ? 'bg-green-900/40 border border-green-700' : 'bg-red-900/40 border border-red-700'
        }`}>
          <span className="text-gray-200">{runResult.ok ? '✅' : '❌'} {runResult.text}</span>
          <button onClick={() => setRunResult(null)} className="text-gray-400 hover:text-white ml-2">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <form onSubmit={createMacro} className="bg-dark-bg border border-dark-border rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Назва</label>
            <input
              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
              placeholder="Робочий режим"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              Тригери <span className="text-gray-600">(через кому)</span>
            </label>
            <input
              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
              placeholder="робочий режим, почни роботу"
              value={form.triggers}
              onChange={e => setForm(f => ({ ...f, triggers: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">
              Команди <span className="text-gray-600">(кожна з нового рядка)</span>
            </label>
            <textarea
              rows={3}
              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 resize-none"
              placeholder={"відкрий chrome\nгучність 40"}
              value={form.commands}
              onChange={e => setForm(f => ({ ...f, commands: e.target.value }))}
            />
          </div>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {submitting ? 'Створення...' : 'Створити макрос'}
          </button>
        </form>
      )}

      {/* Macro list */}
      {loading ? (
        <p className="text-center text-gray-500 text-sm py-6">Завантаження...</p>
      ) : macros.length === 0 ? (
        <p className="text-center text-gray-500 text-sm py-8">
          Макросів ще немає. Створіть перший!
        </p>
      ) : (
        <div className="space-y-2">
          {macros.map(macro => (
            <div key={macro.id} className="bg-dark-bg border border-dark-border rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3">
                <button
                  className="flex-1 flex items-center space-x-2 text-left"
                  onClick={() => setExpandedId(v => v === macro.id ? null : macro.id)}
                >
                  {expandedId === macro.id
                    ? <ChevronUp size={16} className="text-gray-400 shrink-0" />
                    : <ChevronDown size={16} className="text-gray-400 shrink-0" />
                  }
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{macro.name}</p>
                    <p className="text-xs text-gray-500">
                      {macro.commands.length} команд{macro.use_count > 0 ? ` · ${macro.use_count} запусків` : ''}
                    </p>
                  </div>
                </button>
                <div className="flex items-center space-x-2 ml-3">
                  <button
                    onClick={() => runMacro(macro.id)}
                    disabled={runningId === macro.id}
                    className="flex items-center space-x-1 px-3 py-1.5 bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white rounded text-xs transition-colors"
                  >
                    <Play size={13} />
                    <span>{runningId === macro.id ? '...' : 'Run'}</span>
                  </button>
                  <button
                    onClick={() => deleteMacro(macro.id, macro.name)}
                    className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              {expandedId === macro.id && (
                <div className="border-t border-dark-border px-4 py-3 space-y-2">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Тригери</p>
                    <div className="flex flex-wrap gap-1">
                      {macro.triggers.map((t, i) => (
                        <span key={i} className="text-xs bg-dark-card text-primary-400 border border-primary-900 px-2 py-0.5 rounded-full">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Команди</p>
                    <div className="space-y-1">
                      {macro.commands.map((c, i) => (
                        <div key={i} className="text-xs text-gray-300 bg-dark-card px-2 py-1 rounded font-mono">
                          {i + 1}. {c}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
