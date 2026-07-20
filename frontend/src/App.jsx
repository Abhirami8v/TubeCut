import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import CreateClipPage from './pages/CreateClipPage'
import MyClipsPage from './pages/MyClipsPage'
import CaptionStylesPage from './pages/CaptionStylesPage'
import SettingsPage from './pages/SettingsPage'
import ClipEditorPage from './pages/ClipEditorPage'
import AdminPage from './pages/AdminPage'
import LoginPage from './pages/LoginPage'

export default function App() {
  const [loggedIn, setLoggedIn] = useState(
    () => localStorage.getItem('tubecut_logged_in') === 'true'
  )

  if (!loggedIn) {
    return <LoginPage onLoginSuccess={() => setLoggedIn(true)} />
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<CreateClipPage />} />
        <Route path="/clips" element={<MyClipsPage />} />
        <Route path="/clips/:clipId" element={<ClipEditorPage />} />
        <Route path="/styles" element={<CaptionStylesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </AppShell>
  )
}
