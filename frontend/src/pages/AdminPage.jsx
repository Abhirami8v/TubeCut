import { useEffect, useState } from 'react'
import { Shield, Trash2, Users, Loader2, Sparkles, UserCheck, ShieldAlert } from 'lucide-react'
import { api } from '../lib/api'
import Button from '../components/ui/Button'

export default function AdminPage() {
  const [users, setUsers] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionUserId, setActionUserId] = useState(null)

  const currentEmail = localStorage.getItem('tubecut_email')

  async function fetchUsers() {
    try {
      setLoading(true)
      const data = await api.adminListUsers()
      setUsers(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  async function handleDelete(userId, email) {
    if (email === currentEmail) {
      alert("You cannot delete your own logged-in admin account.")
      return
    }
    if (!confirm(`Are you absolutely sure you want to delete user "${email}" and all their associated jobs, clips, and settings? This action is irreversible.`)) {
      return
    }

    setActionUserId(userId)
    try {
      await api.adminDeleteUser(userId)
      await fetchUsers()
    } catch (err) {
      alert(err.message)
    } finally {
      setActionUserId(null)
    }
  }

  async function handleToggleAdmin(userId, email) {
    if (email === currentEmail) {
      alert("You cannot toggle your own admin privileges.")
      return
    }

    setActionUserId(userId)
    try {
      await api.adminToggleAdmin(userId)
      await fetchUsers()
    } catch (err) {
      alert(err.message)
    } finally {
      setActionUserId(null)
    }
  }

  return (
    <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto min-h-screen relative">
      {/* Glow ambient background */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#C45EFF]/3 blur-[140px] pointer-events-none" />

      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10 pb-6 border-b border-[#2A2633] relative z-10">
        <div>
          <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold flex items-center gap-1.5">
            <Shield size={12} /> System Administration
          </span>
          <h1 className="font-display font-extrabold text-3xl md:text-4xl text-white tracking-tight mt-1">
            User Management
          </h1>
          <p className="text-sm text-[var(--color-text-dim)] mt-2">
            View system metrics, assign administrative privileges, and delete user workspaces.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-[#141318] border border-[#2A2633] px-4 py-2.5 rounded-xl font-mono text-xs text-white">
          <Users size={14} className="text-[#C45EFF]" />
          Total Users: <span className="font-bold text-[#C45EFF]">{users ? users.length : '...'}</span>
        </div>
      </div>

      {error && (
        <p className="text-sm text-[#FF5A79] bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-3 px-4 mb-6 relative z-10">
          {error}
        </p>
      )}

      {loading ? (
        <div className="flex items-center justify-center min-h-[30vh]">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="animate-spin text-[#C45EFF]" size={28} />
            <span className="text-sm text-[var(--color-text-dim)] font-mono">Retrieving accounts list...</span>
          </div>
        </div>
      ) : (
        <div className="bg-[#141318] border border-[#2A2633] rounded-3xl overflow-hidden shadow-2xl relative z-10">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#2A2633] bg-[#1E1C22]/50 text-xs font-bold text-[var(--color-text-dim)] uppercase tracking-wider font-mono">
                  <th className="py-4 px-6">Email / Account</th>
                  <th className="py-4 px-6">Joined Date</th>
                  <th className="py-4 px-6">System Role</th>
                  <th className="py-4 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2A2633]/60 text-sm">
                {users && users.map((user) => {
                  const isCurrent = user.email === currentEmail
                  const isAction = actionUserId === user.id
                  return (
                    <tr key={user.id} className="hover:bg-[#1E1C22]/20 transition-colors">
                      <td className="py-4 px-6 font-medium text-white">
                        <div className="flex items-center gap-2">
                          <span>{user.email}</span>
                          {isCurrent && (
                            <span className="text-[10px] font-mono font-bold bg-[#C45EFF]/10 border border-[#C45EFF]/30 text-[#C45EFF] px-1.5 py-0.5 rounded">
                              Current User
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-[var(--color-text-dim)] font-mono text-xs">
                        {user.created_at ? new Date(user.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        }) : 'N/A'}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-1.5">
                          {user.is_admin ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                              <Shield size={10} /> Admin
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#2A2633] text-[var(--color-text-dim)]">
                              Creator
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="xs"
                            onClick={() => handleToggleAdmin(user.id, user.email)}
                            disabled={isCurrent || isAction}
                            className={`rounded-lg font-bold text-xs tracking-wide px-3 py-1.5 transition-all cursor-pointer ${
                              user.is_admin
                                ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400 hover:bg-amber-500/20'
                                : 'bg-blue-500/10 border border-blue-500/20 text-blue-400 hover:bg-blue-500/20'
                            }`}
                          >
                            {isAction && actionUserId === user.id ? (
                              <Loader2 size={12} className="animate-spin inline mr-1" />
                            ) : user.is_admin ? (
                              'Revoke Admin'
                            ) : (
                              'Make Admin'
                            )}
                          </Button>
                          <Button
                            size="xs"
                            onClick={() => handleDelete(user.id, user.email)}
                            disabled={isCurrent || isAction}
                            className="rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/25 font-bold text-xs tracking-wide px-3 py-1.5 transition-all flex items-center justify-center gap-1 cursor-pointer"
                          >
                            <Trash2 size={12} />
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
