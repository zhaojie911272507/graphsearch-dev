import { Routes, Route, useLocation } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { AssetCatalog } from './pages/AssetCatalog'
import { NodeDetail } from './pages/NodeDetail'
import { OntologyManager } from './pages/OntologyManager'
import { ReviewQueue } from './pages/ReviewQueue'
import { Explorations } from './pages/Explorations'
import { EvaluationDashboard } from './pages/EvaluationDashboard'
import { GraphViz } from './pages/GraphViz'
import { LineageTracking } from './pages/LineageTracking'
import { SettingsPage } from './pages/SettingsPage'
import { LineageIndex } from './pages/LineageIndex'
import { NotFoundPage } from './pages/NotFoundPage'
import { DomainManager } from './pages/DomainManager'

function App() {
  const location = useLocation()
  console.log('App rendering, current path:', location.pathname)
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<AssetCatalog />} />
        <Route path="assets" element={<AssetCatalog />} />
        <Route path="assets/:nodeId" element={<NodeDetail />} />
        <Route path="lineage" element={<LineageIndex />} />
        <Route path="lineage/:nodeId" element={<LineageTracking />} />
        <Route path="ontology" element={<OntologyManager />} />
        <Route path="domains" element={<DomainManager />} />
        <Route path="review" element={<ReviewQueue />} />
        <Route path="explorations" element={<Explorations />} />
        <Route path="evaluation" element={<EvaluationDashboard />} />
        <Route path="graph" element={<GraphViz />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
