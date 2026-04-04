import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { AssetCatalog } from './pages/AssetCatalog'
import { NodeDetail } from './pages/NodeDetail'
import { OntologyManager } from './pages/OntologyManager'
import { ReviewQueue } from './pages/ReviewQueue'
import { Explorations } from './pages/Explorations'
import { EvaluationDashboard } from './pages/EvaluationDashboard'
import { GraphViz } from './pages/GraphViz'
import { GraphQuery } from './pages/GraphQuery'
import { TemporalQuery } from './pages/TemporalQuery'
import { TemporalStats } from './pages/TemporalStats'
import LineageTracking from './pages/LineageTracking'
import { SettingsPage } from './pages/SettingsPage'
import { LineageIndex } from './pages/LineageIndex'
import { NotFoundPage } from './pages/NotFoundPage'
import { DomainManager } from './pages/DomainManager'
import { DocumentManager } from './pages/DocumentManager'
import { DocumentDetail } from './pages/DocumentDetail'
import { SimulationExecution } from './pages/SimulationExecution'
import { SimulationReports } from './pages/SimulationReports'
import { SimulationDialogue } from './pages/SimulationDialogue'
import PipelineConfig from './pages/PipelineConfig'
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
        <Route path="lineage" element={<LineageIndex />} />
        <Route path="lineage/:nodeId" element={<LineageTracking />} />
        <Route path="ontology" element={<OntologyManager />} />
        <Route path="domains" element={<DomainManager />} />
        <Route path="review" element={<ReviewQueue />} />
        <Route path="explorations" element={<Explorations />} />
        <Route path="evaluation" element={<EvaluationDashboard />} />
        <Route path="pipeline" element={<PipelineConfig />} />
        <Route path="graph" element={<GraphViz />} />
        <Route path="graph/query" element={<GraphQuery />} />
        <Route path="temporal" element={<TemporalQuery />} />
        <Route path="temporal/stats" element={<TemporalStats />} />
        <Route path="simulation" element={<SimulationExecution />} />
        <Route path="simulation/reports" element={<SimulationReports />} />
        <Route path="simulation/dialogue" element={<SimulationDialogue />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App