import axios, { type AxiosRequestConfig, type AxiosError } from 'axios'

import type {
  AgentGenerateRequestPayload,
  DialogueHistoryTurn,
  OntologyApplyRecommendationsRequest,
  OntologyApplyResponse,
  OntologyRecommendRequest,
  OntologyRecommendResponse,
  WorldConfigRequestPayload,
} from '@/schemas/api-contracts'

const API_BASE = '/api/v1'

// Retry configuration
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 1 second

// Helper function to delay execution
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// Helper function to check if error should be retried
const shouldRetry = (error: AxiosError): boolean => {
  const status = error.response?.status
  // Retry on 5xx server errors, 408 timeout, and 429 rate limit
  return (
    status === 408 ||
    status === 429 ||
    (status !== undefined && status >= 500 && status < 600) ||
    error.code === 'ECONNABORTED' ||
    error.code === 'NETWORK_ERROR'
  )
}

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor with retry logic and error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  async (error: AxiosError) => {
    const config = error.config as AxiosRequestConfig & {
      _retryCount?: number
    }

    // Check if we should retry
    if (shouldRetry(error)) {
      config._retryCount = config._retryCount || 0

      if (config._retryCount < MAX_RETRIES) {
        config._retryCount++
        const retryDelay = RETRY_DELAY * Math.pow(2, config._retryCount - 1) // Exponential backoff
        console.log(`[API] Retry ${config._retryCount}/${MAX_RETRIES} after ${retryDelay}ms`)
        await delay(retryDelay)
        return api(config)
      }
    }

    // Handle specific error codes
    let errorMessage = '请求失败，请稍后重试'

    if (error.response) {
      const status = error.response.status
      const data = error.response.data as { detail?: string } | undefined

      switch (status) {
        case 400:
          errorMessage = data?.detail || '请求参数错误'
          break
        case 401:
          errorMessage = '未授权，请登录'
          // Clear token and redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          break
        case 403:
          errorMessage = '拒绝访问'
          break
        case 404:
          errorMessage = '请求的资源不存在'
          break
        case 408:
          errorMessage = '请求超时'
          break
        case 429:
          errorMessage = '请求过于频繁，请稍后重试'
          break
        case 500:
          errorMessage = '服务器内部错误'
          break
        case 502:
          errorMessage = '网关错误'
          break
        case 503:
          errorMessage = '服务不可用'
          break
        case 504:
          errorMessage = '网关超时'
          break
        default:
          errorMessage = `请求失败 (${status})`
      }
    } else if (error.request) {
      errorMessage = '无法连接到服务器，请检查网络连接'
    }

    console.error('[API] Error:', errorMessage, error)

    // Reject with custom error
    return Promise.reject(new Error(errorMessage))
  }
)

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

  getLineage: (
    nodeId: string,
    direction?: string,
    max_depth?: number,
    node_types?: string[],
    relation_types?: string[]
  ) =>
    api.get(`/metadata/${nodeId}/lineage`, {
      params: { direction, max_depth, node_types, relation_types }
    }),

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
  getRecommendations: (data?: OntologyRecommendRequest) =>
    api.post<OntologyRecommendResponse>('/ontology/recommend', data ?? {}),

  applyRecommendations: (data: OntologyApplyRecommendationsRequest) =>
    api.post<OntologyApplyResponse>('/ontology/recommendations/apply', data),

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
  getNodeDetail: (nodeId: string) =>
    api.get(`/metadata/nodes/${nodeId}`),
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

// Auth APIs
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),

  logout: () => api.post('/auth/logout'),

  getCurrentUser: () => api.get('/auth/me'),

  getUsers: () => api.get('/auth/users'),

  createUser: (data: { username: string; password: string; name: string; role: string }) =>
    api.post('/auth/users', data),

  updateUserRole: (username: string, role: string) =>
    api.put(`/auth/users/${username}/role`, null, { params: { role } }),
}

// Helper to get current user from localStorage
export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user')
  return userStr ? JSON.parse(userStr) : null
}

// Helper to check if logged in
export const isLoggedIn = () => {
  return !!localStorage.getItem('access_token')
}

// Helper to logout
export const logout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  window.location.href = '/login'
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
  generateAgents: (data: AgentGenerateRequestPayload) =>
    api.post('/simulation/agents/generate', data),
  configureWorld: (data: WorldConfigRequestPayload) =>
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
  chatWithAgent: (agentId: string, message: string, conversationHistory?: DialogueHistoryTurn[]) =>
    api.post(`/simulation/dialogue/agents/${agentId}/chat`, {
      message,
      conversation_history: conversationHistory,
    }),
}

// Query APIs (Graph RAG)
export const queryApi = {
  query: (data: {
    question: string
    top_k?: number
    traversal_depth?: number
    include_sources?: boolean
  }) => api.post('/query', data),
}

// Temporal Knowledge Graph APIs
export const temporalApi = {
  // Query temporal data
  query: (data: {
    entity_id?: string
    source_id?: string
    target_id?: string
    query_type: string
    from_time?: string
    to_time?: string
    timestamp?: string
  }) => api.post('/temporal/query', data),

  // Generate summary
  getSummary: (data: {
    level: 'entity' | 'relationship' | 'global'
    entity_id?: string
    entity_name?: string
    entity_type?: string
    source_id?: string
    target_id?: string
    source_name?: string
    target_name?: string
    relation_type?: string
    time_range?: [string, string]
  }) => api.post('/temporal/summary', data),

  // Get service status
  getStatus: () => api.get('/temporal/status'),

  // Trigger manual merge
  triggerMerge: () => api.post('/temporal/merge'),
}
