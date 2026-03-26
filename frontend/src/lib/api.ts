import axios from 'axios'

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

  createEntityType: (data: { name: string; description: string; color: string; icon: string }) =>
    api.post('/ontology/entity-types', data),

  updateEntityType: (name: string, data: Partial<{ description: string; color: string; icon: string }>) =>
    api.put(`/ontology/entity-types/${name}`, data),

  deleteEntityType: (name: string) => api.delete(`/ontology/entity-types/${name}`),

  getRelationTypes: (include_builtin?: boolean, include_counts?: boolean) =>
    api.get('/ontology/relation-types', { params: { include_builtin, include_counts } }),

  createRelationType: (data: Record<string, unknown>) =>
    api.post('/ontology/relation-types', data),

  getVersions: (limit?: number) => api.get('/ontology/versions', { params: { limit } }),

  createVersion: (data: { version: string; change_summary: string; changes: string[] }) =>
    api.post('/ontology/versions', data),
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
