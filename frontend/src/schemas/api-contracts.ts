/**
 * Zod schemas aligned with FastAPI bodies where practical.
 * Use z.infer types for request/response typing; schemas enable optional runtime validation.
 */

import { z } from 'zod'

/** Document samples or DB rows sent to ontology recommend. */
export const ontologyRecommendDocumentSchema = z
  .object({
    id: z.string().optional(),
    title: z.string().optional(),
    content: z.string().optional(),
    raw_content: z.string().optional(),
  })
  .passthrough()

export const ontologyRecommendRequestSchema = z.object({
  documents: z.array(ontologyRecommendDocumentSchema).optional(),
  max_entity_types: z.number().int().positive().optional(),
  max_relation_types: z.number().int().positive().optional(),
  domain_key: z.string().optional(),
})

export type OntologyRecommendRequest = z.infer<typeof ontologyRecommendRequestSchema>

export const recommendedEntityTypeDraftSchema = z
  .object({
    name: z.string(),
    description: z.string(),
    color: z.string().optional(),
    icon: z.string().optional(),
    extraction_prompt_template: z.string().optional(),
    example_instances: z.array(z.string()).optional(),
  })
  .passthrough()

export const recommendedRelationTypeDraftSchema = z
  .object({
    name: z.string(),
    description: z.string(),
    source_types: z.array(z.string()),
    target_types: z.array(z.string()),
    directionality: z.string().optional(),
    extraction_prompt: z.string().optional(),
  })
  .passthrough()

export type RecommendedEntityTypeDraft = z.infer<typeof recommendedEntityTypeDraftSchema>
export type RecommendedRelationTypeDraft = z.infer<typeof recommendedRelationTypeDraftSchema>

export const ontologyRecommendationsBundleSchema = z.object({
  entity_types: z.array(recommendedEntityTypeDraftSchema),
  relation_types: z.array(recommendedRelationTypeDraftSchema),
  analysis_summary: z.string().optional(),
})

export type OntologyRecommendationsBundle = z.infer<typeof ontologyRecommendationsBundleSchema>

export const ontologyRecommendResponseSchema = z.discriminatedUnion('success', [
  z.object({
    success: z.literal(false),
    message: z.string(),
    recommendations: ontologyRecommendationsBundleSchema.optional(),
  }),
  z.object({
    success: z.literal(true),
    domain_context: z.string().optional(),
    analysis_summary: z.string().optional(),
    confidence_score: z.number().optional(),
    recommendations: ontologyRecommendationsBundleSchema,
    existing_count: z
      .object({
        entity_types: z.number(),
        relation_types: z.number(),
      })
      .optional(),
  }),
])

export type OntologyRecommendResponse = z.infer<typeof ontologyRecommendResponseSchema>

export const ontologyApplyRecommendationsRequestSchema = z.object({
  entity_types: z.array(recommendedEntityTypeDraftSchema),
  relation_types: z.array(recommendedRelationTypeDraftSchema),
})

export type OntologyApplyRecommendationsRequest = z.infer<
  typeof ontologyApplyRecommendationsRequestSchema
>

export const ontologyApplyResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  created: z.object({
    entity_types: z.array(z.record(z.unknown())),
    relation_types: z.array(z.record(z.unknown())),
  }),
})

export type OntologyApplyResponse = z.infer<typeof ontologyApplyResponseSchema>

/** Matches app.api.schemas.simulation.AgentGenerateRequest */
export const agentGenerateRequestSchema = z.object({
  seed_ids: z.array(z.string().uuid()).default([]),
  profile_count: z.number().int().min(1).max(100).default(5),
  platform: z.string().default('WECHAT'),
  custom_traits: z.record(z.unknown()).default({}),
})

export type AgentGenerateRequestPayload = z.input<typeof agentGenerateRequestSchema>

/** Matches app.api.schemas.simulation.PlatformConfigSchema */
export const platformConfigRequestSchema = z.object({
  platform: z.string(),
  post_frequency_range: z.tuple([z.number(), z.number()]).optional(),
  interaction_probability: z.number().optional(),
  content_topics: z.array(z.string()).optional(),
  trending_hashtags: z.array(z.string()).optional(),
  community_rules: z.array(z.string()).optional(),
})

export type PlatformConfigRequestPayload = z.infer<typeof platformConfigRequestSchema>

/** Matches app.api.schemas.simulation.WorldConfigRequest */
export const worldConfigRequestSchema = z.object({
  world_key: z.string().min(1).max(128),
  name: z.string().min(1).max(300),
  description: z.string().default(''),
  platform: z.string().default('WECHAT'),
  state_data: z.record(z.unknown()).default({}),
  platform_config: platformConfigRequestSchema.nullable().optional(),
})

export type WorldConfigRequestPayload = z.input<typeof worldConfigRequestSchema>

/** Optional client-side history payload (backend may ignore extra fields). */
export const dialogueHistoryTurnSchema = z
  .object({
    role: z.string(),
    content: z.string(),
  })
  .passthrough()

export type DialogueHistoryTurn = z.infer<typeof dialogueHistoryTurnSchema>
