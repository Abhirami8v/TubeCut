import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import CreateClipPage from './pages/CreateClipPage'
import MyClipsPage from './pages/MyClipsPage'
import CaptionStylesPage from './pages/CaptionStylesPage'
import SettingsPage from './pages/SettingsPage'
import ClipEditorPage from './pages/ClipEditorPage'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<CreateClipPage />} />
        <Route path="/clips" element={<MyClipsPage />} />
        <Route path="/clips/:clipId" element={<ClipEditorPage />} />
        <Route path="/styles" element={<CaptionStylesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppShell>
  )
}
