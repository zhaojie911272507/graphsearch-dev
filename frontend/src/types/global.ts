// Global type declarations for the GraphRAG Metadata Management Platform

declare global {
  interface Window {
    // Add any window properties if needed
  }
}

// Asset types
interface AssetListItem {
  id: string
  node_type: string
  name: string
  entity_type?: string
  created_at: string
  quality_score: number
  relation_count: number
  document_count: number
  tags: string[]
  confidence_avg: number
}

interface AssetListResponse {
  items: AssetListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// Node detail types
interface Relation {
  relation_type: string
  other_node_id: string
  other_node_name: string
  other_node_type: string
  weight: number
  direction?: string
}

interface NodeDetail {
  id: string
  node_type: string
  name: string
  entity_type?: string
  description: string
  content_preview: string
  created_at: string
  updated_at: string
  source: string
  tags: string[]
  quality_score: number
  relation_count: number
  incoming_relations: Relation[]
  outgoing_relations: Relation[]
  metadata: Record<string, unknown>
}

// Ontology types
interface EntityType {
  name: string
  description: string
  color: string
  icon: string
  is_builtin: boolean
  instance_count: number
  extraction_prompt_template: string
  created_at?: string
  updated_at?: string
}

interface RelationType {
  name: string
  description: string
  source_types: string[]
  target_types: string[]
  directionality: string
  is_builtin: boolean
  instance_count: number
  properties: Array<{ name: string; type: string }>
  extraction_prompt: string
}

// Intelligence types
interface ReviewQueueItem {
  id: string
  node_id: string
  node_type: string
  node_name: string
  reason: string
  auto_confidence: number
  source_document: string
  original_text: string
  status: string
  vote_count: number
  approve_count: number
  reject_count: number
  modify_count: number
  created_at: string
  priority: number
}

interface ExplorationPath {
  id: string
  user_id: string
  title: string
  description: string
  start_node_id: string
  visited_nodes: string[]
  highlights: string[]
  view_count: number
  likes: number
  is_public: boolean
  created_at: string
  updated_at: string
}

// Evaluation types
interface Metric {
  name: string
  value: number
  previous_value?: number
  change?: number
  trend: string
  target?: number
}

interface EvaluationMetricsResponse {
  metrics: Record<string, Metric>
  overall_score: number
  evaluated_queries: number
  evaluation_period: Record<string, unknown>
}

interface AblationStudyResponse {
  vector_only: Record<string, Metric>
  hybrid: Record<string, Metric>
  improvement: Record<string, number>
  statistical_significance: Record<string, number>
  sample_size: number
}

// Export for module usage
export type {
  AssetListItem,
  AssetListResponse,
  Relation,
  NodeDetail,
  EntityType,
  RelationType,
  ReviewQueueItem,
  ExplorationPath,
  Metric,
  EvaluationMetricsResponse,
  AblationStudyResponse,
}
