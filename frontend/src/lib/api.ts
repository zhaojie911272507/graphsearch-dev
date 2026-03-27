import axios, { type AxiosRequestConfig } from 'axios'

const API_BASE = '/api/v1'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Asset APIs
export const assetApi = {
  list: (params?: {
    type?: string
    entity_type?: string
    q?: string
    page?: number
    page_size?: number
  }) => api.get('/metadata/assets', { params }),

  getDetail: (nodeId: string) => api.get(`/metadata/${nodeId}`),

  getLineage: (nodeId: string, direction?: string, max_depth?: number) =>
    api.get(`/metadata/${nodeId}/lineage`, { params: { direction, max_depth } }),

  getAnnotations: (nodeId: string) => api.get(`/metadata/${nodeId}/annotations`),

  createAnnotation: (nodeId: string, data: { annotation_type: string; content: Record<string, unknown> }) =>
    api.post(`/metadata/${nodeId}/annotations`, data),
}

// Ontology APIs
export const ontologyApi = {
  getEntityTypes: (include_builtin?: boolean, include_counts?: boolean) =>
    api.get('/ontology/entity-types', { params: { include_builtin, include_counts } }),

  createEntityType: (data: { name: string; description: string; color: string; icon: string; extraction_prompt_template?: string }) =>
    api.post('/ontology/entity-types', data),

  updateEntityType: (name: string, data: Partial<{ description: string; color: string; icon: string; extraction_prompt_template?: string }>) =>
    api.put(`/ontology/entity-types/${name}`, data),

  deleteEntityType: (name: string) => api.delete(`/ontology/entity-types/${name}`),

  getRelationTypes: (include_builtin?: boolean, include_counts?: boolean) =>
    api.get('/ontology/relation-types', { params: { include_builtin, include_counts } }),

  createRelationType: (data: Record<string, unknown>) =>
    api.post('/ontology/relation-types', data),

  updateRelationType: (name: string, data: Partial<Record<string, unknown>>) =>
    api.put(`/ontology/relation-types/${name}`, data),

  deleteRelationType: (name: string) => api.delete(`/ontology/relation-types/${name}`),

  getVersions: (limit?: number) => api.get('/ontology/versions', { params: { limit } }),

  createVersion: (data: { version: string; change_summary: string; changes: string[] }) =>
    api.post('/ontology/versions', data),

  // AI-powered recommendation APIs
  getRecommendations: (data?: { documents?: any[]; max_entity_types?: number; max_relation_types?: number; domain_key?: string }) =>
    api.post('/ontology/recommend', data || {}),

  applyRecommendations: (data: { entity_types: any[]; relation_types: any[] }) =>
    api.post('/ontology/recommendations/apply', data),

  getDocumentsForAnalysis: (limit?: number) =>
    api.get('/ontology/documents/for-analysis', { params: { limit } }),

  getOntologyDiff: (version: string, compare_to?: string) =>
    api.get(`/ontology/versions/${version}/diff`, { params: { compare_to } }),

  rollbackOntology: (version: string) =>
    api.post(`/ontology/versions/${version}/rollback`),
}

// Intelligence APIs
export const intelligenceApi = {
  getReviewQueue: (params?: { status_filter?: string; limit?: number }) =>
    api.get('/intelligence/review-queue', { params }),

  voteReview: (itemId: string, data: { vote_type: string; comment: string }) =>
    api.post(`/intelligence/review-queue/${itemId}/vote`, data),

  getExplorations: (params?: { user_id?: string; sort?: string; limit?: number }) =>
    api.get('/intelligence/explorations', { params }),

  createExploration: (data: { title: string; description: string; start_node_id: string; visited_nodes: string[] }) =>
    api.post('/intelligence/explorations', data),

  getRecommendations: (params?: { node_id?: string; limit?: number }) =>
    api.get('/intelligence/recommendations', { params }),
}

// Evaluation APIs
export const evaluationApi = {
  getMetrics: (params?: { days?: number }) =>
    api.get('/evaluation/metrics', { params }),

  getTrend: (params: Record<string, string>) => api.get('/evaluation/trend', { params }),

  getAblationStudy: (params?: { days?: number }) =>
    api.get('/evaluation/ablation-study', { params }),

  getPipelineConfigs: () => api.get('/evaluation/pipeline/configs'),

  createPipelineConfig: (data: Record<string, unknown>) =>
    api.post('/evaluation/pipeline/configs', data),

  activatePipelineConfig: (version: string) =>
    api.post(`/evaluation/pipeline/configs/${version}/activate`, {}),

  getPromptTemplates: (params?: { template_type?: string }) =>
    api.get('/evaluation/prompts', { params }),

  createPromptTemplate: (data: Record<string, unknown>) =>
    api.post('/evaluation/prompts', data),

  testPrompt: (data: Record<string, unknown>) =>
    api.post('/evaluation/prompts/test', data),
}

// Graph Visualization API
export const graphVizApi = {
  getGraph: (params?: { limit?: number }) =>
    api.get('/metadata/graph-viz', { params: { limit: params?.limit || 100 } }),
}

// Domain Management APIs
export const domainApi = {
  list: (include_inactive?: boolean) =>
    api.get('/domains', { params: { include_inactive } }),

  get: (domainKey: string) =>
    api.get(`/domains/${domainKey}`),

  create: (data: {
    domain_key: string
    name: string
    description?: string
    extraction_prompt_template?: string
    parent_domain_key?: string | null
    inherits_base_ontology?: boolean
  }) =>
    api.post('/domains', data),

  update: (domainKey: string, data: Partial<{
    name: string
    description: string
    extraction_prompt_template: string
    parent_domain_key: string | null
    inherits_base_ontology: boolean
  }>) =>
    api.put(`/domains/${domainKey}`, data),

  delete: (domainKey: string) =>
    api.delete(`/domains/${domainKey}`),

  activate: (domainKey: string) =>
    api.post(`/domains/${domainKey}/activate`),

  getActive: () =>
    api.get('/domains/active'),

  getEntityTypes: (domainKey: string) =>
    api.get(`/domains/${domainKey}/entity-types`),

  getRelationTypes: (domainKey: string) =>
    api.get(`/domains/${domainKey}/relation-types`),

  getInheritanceChain: (domainKey: string) =>
    api.get(`/domains/${domainKey}/inheritance-chain`),
}

// Audit Log APIs
export const auditApi = {
  getLogs: (params?: {
    user_id?: string
    action?: string
    resource_type?: string
    limit?: number
  }) => api.get('/audit/logs', { params }),

  getLogById: (logId: string) => api.get(`/audit/logs/${logId}`),
}

const formDataUploadConfig: AxiosRequestConfig = {
  transformRequest: [
    (data, headers) => {
      if (data instanceof FormData && headers && typeof headers === 'object') {
        if ('delete' in headers && typeof headers.delete === 'function') {
          headers.delete('Content-Type')
        } else {
          delete (headers as Record<string, unknown>)['Content-Type']
        }
      }
      return data
    },
  ],
}

// Document Management APIs
export const documentApi = {
  upload: (file: File, domainKey?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (domainKey) formData.append('domain_key', domainKey)
    return api.post('/documents/upload', formData, formDataUploadConfig)
  },

  batchUpload: (files: File[], domainKey?: string) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    if (domainKey) formData.append('domain_key', domainKey)
    return api.post('/documents/batch-upload', formData, formDataUploadConfig)
  },

  list: (params?: {
    q?: string
    page?: number
    page_size?: number
    status_filter?: string
  }) =>
    api.get('/documents', { params }),

  getDetail: (documentId: string) =>
    api.get(`/documents/${documentId}`),

  delete: (documentId: string) =>
    api.delete(`/documents/${documentId}`),

  batchImport: (directoryPath: string) =>
    api.post('/documents/batch-import', { directory_path: directoryPath })
}

// Simulation APIs
export const simulationApi = {
  // Session management
  listSessions: () => api.get('/simulation/sessions'),
  createSession: (data: {
    name: string
    agent_count: number
    platforms: string[]
    seed_content?: string
  }) => api.post('/simulation/sessions', data),

  getSession: (sessionId: string) => api.get(`/simulation/sessions/${sessionId}`),
  deleteSession: (sessionId: string) => api.delete(`/simulation/sessions/${sessionId}`),

  // Control
  startSession: (sessionId: string) => api.post(`/simulation/sessions/${sessionId}/start`),
  pauseSession: (sessionId: string) => api.post(`/simulation/sessions/${sessionId}/pause`),
  stopSession: (sessionId: string) => api.post(`/simulation/sessions/${sessionId}/stop`),
  runStep: (sessionId: string, stepCount?: number) =>
    api.post(`/simulation/sessions/${sessionId}/step`, { step_count: stepCount }),

  // Status & metrics
  getStatus: (sessionId: string) => api.get(`/simulation/sessions/${sessionId}/status`),
  getMetrics: (sessionId: string) => api.get(`/simulation/sessions/${sessionId}/metrics`),
  getAgents: (sessionId: string, limit?: number) =>
    api.get(`/simulation/sessions/${sessionId}/agents`, { params: { limit } }),
  applyMemoryDecay: (sessionId: string, decayRate?: number) =>
    api.post(`/simulation/sessions/${sessionId}/memory/decay`, { decay_rate: decayRate }),

  // Bootstrap (initialization)
  bootstrap: (data: {
    name: string
    seed_sources: Array<{ source_type: string; content: string }>
    agent_count: number
    platforms: string[]
  }) => api.post('/simulation/bootstrap', data),
  extractSeeds: (data: { source_type: string; content: string }) =>
    api.post('/simulation/seeds/extract', data),
  generateAgents: (data: { seed_entities: any[]; seed_relations: any[]; agent_count: number }) =>
    api.post('/simulation/agents/generate', data),
  configureWorld: (data: { session_id: string; world_state_config: any }) =>
    api.post('/simulation/world/configure', data),
}

// Simulation Reports APIs
export const simulationReportApi = {
  listReports: (sessionId?: string) =>
    api.get('/simulation/reports', { params: { session_id: sessionId } }),

  generateReport: (data: {
    session_id: string
    report_type: string
    time_range?: { start: string; end: string }
  }) => api.post('/simulation/reports/generate', data),

  getReport: (reportId: string) => api.get(`/simulation/reports/${reportId}`),
  deleteReport: (reportId: string) => api.delete(`/simulation/reports/${reportId}`),

  // Agent analysis
  getAgentAnalysis: (agentId: string) =>
    api.get(`/simulation/reports/agents/${agentId}/analysis`),

  // Network analysis
  getNetworkAnalysis: (sessionId: string) =>
    api.get(`/simulation/reports/session/${sessionId}/network`),
}

// Simulation Dialogue APIs
export const simulationDialogueApi = {
  // Conversation management
  startConversation: (data: { user_id: string; agent_id: string }) =>
    api.post('/simulation/dialogue/start', data),

  getConversation: (conversationId: string) =>
    api.get(`/simulation/dialogue/${conversationId}`),

  getConversationHistory: (conversationId: string, limit?: number) =>
    api.get(`/simulation/dialogue/${conversationId}/history`, { params: { limit } }),

  sendMessage: (data: { conversation_id: string; message: string }) =>
    api.post('/simulation/dialogue/message', data),

  // Direct chat with agent
  chatWithAgent: (agentId: string, message: string, conversation_history?: any[]) =>
    api.post(`/simulation/dialogue/agents/${agentId}/chat`, {
      message,
      conversation_history,
    }),
}
