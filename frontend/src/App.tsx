import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { AssetCatalog } from './pages/AssetCatalog'
import { NodeDetail } from './pages/NodeDetail'
import { GraphViz } from './pages/GraphViz'
import { GraphQuery } from './pages/GraphQuery'
import { NotFoundPage } from './pages/NotFoundPage'
import { DocumentManager } from './pages/DocumentManager'
import { DocumentDetail } from './pages/DocumentDetail'
import { SettingsPage } from './pages/SettingsPage'
import Login from './pages/Login'
import { isLoggedIn } from './lib/api'

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />

      {/* Protected routes */}
      <Route path="/" element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route index element={<AssetCatalog />} />
        <Route path="assets" element={<AssetCatalog />} />
        <Route path="assets/:nodeId" element={<NodeDetail />} />
        <Route path="documents" element={<DocumentManager />} />
        <Route path="documents/:documentId" element={<DocumentDetail />} />
        <Route path="graph" element={<GraphViz />} />
        <Route path="graph/query" element={<GraphQuery />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App