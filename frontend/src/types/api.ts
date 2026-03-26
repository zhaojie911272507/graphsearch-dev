// API types for the GraphRAG Metadata Management Platform

export interface AssetListItem {
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

export interface AssetListResponse {
  items: AssetListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface NodeDetail {
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

export interface Relation {
  relation_type: string
  other_node_id: string
  other_node_name: string
  other_node_type: string
  weight: number
}

export interface LineagePath {
  path: Array<{ id: string; type: string; label: string }>
  confidence: number
}

export interface LineageResponse {
  lineage_paths: LineagePath[]
  upstream_count: number
  downstream_count: number
}

export interface Annotation {
  id: string
  node_id: string
  user_id: string
  annotation_type: string
  content: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
  votes: Vote[]
}

export interface Vote {
  id: string
  annotation_id: string
  user_id: string
  vote_type: string
  comment: string
  created_at: string
}

export interface EntityType {
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

export interface RelationType {
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

export interface ReviewQueueItem {
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

export interface ExplorationPath {
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

export interface EvaluationMetrics {
  precision: Metric
  recall: Metric
  faithfulness: Metric
  relevance: Metric
}

export interface Metric {
  name: string
  value: number
  previous_value?: number
  change?: number
  trend: string
  target?: number
}

export interface PipelineConfig {
  version: string
  retrieval: Record<string, unknown>
  generation: Record<string, unknown>
  created_at: string
  created_by: string
  is_active: boolean
}
