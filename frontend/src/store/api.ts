// src/store/api.ts
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type {
  Entity,
  EntitiesResponse,
  EntityPreview,
  QueueEntry,
  QueueResponse,
  BatchOperation,
  BatchOperationResult,
  DashboardStats,
  AnalyticsData,
  SearchSuggestion,
  EntityFilter,
  QueueType,
  Priority,
  // NEW TYPES
  ExtractionConfig,
  ExtractionSession,
  ExtractionProgress,
  ExtractionLog,
  ExtractionStatus,
  DeduplicationStats,
  DiscoverySource,
  ManualEntityRequest,
  ManualEntityResponse,
  BulkReviewOperation,
  BulkReviewResult
} from '../types'

export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1',
    prepareHeaders: (headers) => {
      headers.set('Content-Type', 'application/json')
      return headers
    },
  }),
  tagTypes: ['Entity', 'Queue', 'Analytics', 'Dashboard', 'Extraction', 'DeduplicationStats'],
  endpoints: (builder) => ({
    // ===== EXISTING ENTITY ENDPOINTS (unchanged) =====
    getEntities: builder.query<EntitiesResponse, EntityFilter>({
      query: (filters) => {
        const params = new URLSearchParams()
        
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            if (Array.isArray(value)) {
              value.forEach(v => params.append(key, v.toString()))
            } else {
              params.append(key, value.toString())
            }
          }
        })
        
        return `entities?${params.toString()}`
      },
      providesTags: ['Entity'],
    }),

    getEntity: builder.query<Entity, string>({
      query: (qid) => `entities/${qid}`,
      providesTags: (result, error, qid) => [{ type: 'Entity', id: qid }],
    }),

    updateEntity: builder.mutation<Entity, { qid: string; data: Partial<Entity> }>({
      query: ({ qid, data }) => ({
        url: `entities/${qid}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { qid }) => [
        { type: 'Entity', id: qid },
        'Entity',
        'Queue',
        'Dashboard'
      ],
    }),

    getEntityPreview: builder.query<EntityPreview, string>({
      query: (qid) => `entities/${qid}/preview`,
    }),

    getEntityRelationships: builder.query<{ relationships: any[] }, string>({
      query: (qid) => `entities/${qid}/relationships`,
    }),

    getSearchSuggestions: builder.query<{ suggestions: SearchSuggestion[] }, string>({
      query: (query) => `entities/search/suggestions?query=${encodeURIComponent(query)}&limit=10`,
    }),

    // ===== NEW MANUAL ENTITY ENDPOINT =====
    addManualEntity: builder.mutation<ManualEntityResponse, ManualEntityRequest>({
      query: (entityData) => ({
        url: 'entities/manual',
        method: 'POST',
        body: entityData,
      }),
      invalidatesTags: ['Entity', 'Queue', 'Dashboard', 'DeduplicationStats'],
    }),

    // ===== EXISTING QUEUE ENDPOINTS (updated) =====
    getAllQueues: builder.query<Record<string, any>, void>({
      query: () => 'queues',
      providesTags: ['Queue'],
    }),

    getQueueEntities: builder.query<QueueResponse, {
      queue_type: QueueType;
      limit?: number;
      offset?: number;
      sort_by?: string;
      sort_order?: string;
      discovery_source?: string;  // NEW FILTER
    }>({
      query: ({ 
        queue_type, 
        limit = 50, 
        offset = 0, 
        sort_by = 'added_date', 
        sort_order = 'desc',
        discovery_source
      }) => {
        const params = new URLSearchParams({
          limit: limit.toString(),
          offset: offset.toString(),
          sort_by,
          sort_order
        })
        
        if (discovery_source) {
          params.append('discovery_source', discovery_source)
        }
        
        return `queues/${queue_type}?${params.toString()}`
      },
      providesTags: ['Queue'],
    }),

    addToQueue: builder.mutation<QueueEntry, {
      qid: string;
      queue_type: QueueType;
      priority?: Priority;
      notes?: string;
    }>({
      query: (data) => ({
        url: 'queues/entries',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: ['Queue', 'Entity', 'Dashboard'],
    }),

    updateQueueEntry: builder.mutation<QueueEntry, {
      entry_id: number;
      data: {
        queue_type?: QueueType;
        priority?: Priority;
        notes?: string;
      };
    }>({
      query: ({ entry_id, data }) => ({
        url: `queues/entries/${entry_id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: ['Queue', 'Entity', 'Dashboard'],
    }),

    removeFromQueue: builder.mutation<{ message: string }, number>({
      query: (entry_id) => ({
        url: `queues/entries/${entry_id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Queue', 'Entity', 'Dashboard'],
    }),

    batchQueueOperation: builder.mutation<BatchOperationResult, BatchOperation>({
      query: (operation) => ({
        url: 'queues/batch',
        method: 'POST',
        body: operation,
      }),
      invalidatesTags: ['Queue', 'Entity', 'Dashboard'],
    }),

    getQueueStats: builder.query<any, void>({
      query: () => 'queues/stats/summary',
      providesTags: ['Queue'],
    }),

    // ===== NEW REVIEW QUEUE ENDPOINTS =====
    getReviewQueueSources: builder.query<{ sources: DiscoverySource[] }, void>({
      query: () => 'queues/review/sources',
      providesTags: ['Queue'],
    }),

    bulkApproveReview: builder.mutation<BulkReviewResult, BulkReviewOperation>({
      query: (operation) => ({
        url: 'queues/review/bulk-approve',
        method: 'POST',
        body: operation,
      }),
      invalidatesTags: ['Queue', 'Entity', 'Dashboard', 'DeduplicationStats'],
    }),

    bulkRejectReview: builder.mutation<BulkReviewResult, BulkReviewOperation>({
      query: (operation) => ({
        url: 'queues/review/bulk-reject',
        method: 'POST',
        body: operation,
      }),
      invalidatesTags: ['Queue', 'Entity', 'Dashboard', 'DeduplicationStats'],
    }),

    // ===== NEW EXTRACTION ENDPOINTS =====
    startExtraction: builder.mutation<{ 
      success: boolean; 
      message: string; 
      session_id: number 
    }, {
      entities: string[];
      config?: Partial<ExtractionConfig>;
      session_name?: string;
    }>({
      query: (data) => ({
        url: 'extraction/start',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: ['Extraction', 'Queue', 'Dashboard'],
    }),

    pauseExtraction: builder.mutation<{ 
      success: boolean; 
      message: string 
    }, void>({
      query: () => ({
        url: 'extraction/pause',
        method: 'POST',
      }),
      invalidatesTags: ['Extraction'],
    }),

    resumeExtraction: builder.mutation<{ 
      success: boolean; 
      message: string 
    }, void>({
      query: () => ({
        url: 'extraction/resume',
        method: 'POST',
      }),
      invalidatesTags: ['Extraction'],
    }),

    cancelExtraction: builder.mutation<{ 
      success: boolean; 
      message: string 
    }, void>({
      query: () => ({
        url: 'extraction/cancel',
        method: 'POST',
      }),
      invalidatesTags: ['Extraction', 'Queue', 'Dashboard'],
    }),

    getExtractionStatus: builder.query<{
      status: ExtractionStatus;
      current_session?: ExtractionSession;
      progress?: ExtractionProgress;
    }, void>({
      query: () => 'extraction/status',
      providesTags: ['Extraction'],
    }),

    configureExtraction: builder.mutation<{ 
      success: boolean; 
      message: string 
    }, ExtractionConfig>({
      query: (config) => ({
        url: 'extraction/configure',
        method: 'POST',
        body: config,
      }),
    }),

    getExtractionConfig: builder.query<ExtractionConfig, void>({
      query: () => 'extraction/config',
    }),

    getExtractionSessions: builder.query<{ 
      sessions: ExtractionSession[] 
    }, {
      limit?: number;
      offset?: number;
    }>({
      query: ({ limit = 20, offset = 0 } = {}) => 
        `extraction/sessions?limit=${limit}&offset=${offset}`,
      providesTags: ['Extraction'],
    }),

    getSessionLogs: builder.query<{ 
      logs: ExtractionLog[] 
    }, {
      session_id: number;
      limit?: number;
      offset?: number;
    }>({
      query: ({ session_id, limit = 50, offset = 0 }) => 
        `extraction/sessions/${session_id}/logs?limit=${limit}&offset=${offset}`,
      providesTags: ['Extraction'],
    }),

    getExtractionQueueStats: builder.query<{
      total_in_queue: number;
      by_queue_type: Record<string, number>;
      by_priority: Record<string, number>;
      estimated_processing_time?: number;
    }, void>({
      query: () => 'extraction/queue-stats',
      providesTags: ['Queue', 'Extraction'],
    }),

    // ===== NEW DEDUPLICATION ENDPOINTS =====
    getDeduplicationStats: builder.query<DeduplicationStats, void>({
      query: () => 'deduplication/stats',
      providesTags: ['DeduplicationStats'],
    }),

    // ===== EXISTING ANALYTICS ENDPOINTS (unchanged) =====
    getDashboardStats: builder.query<DashboardStats, void>({
      query: () => 'analytics/dashboard',
      providesTags: ['Dashboard'],
    }),

    getExtractionTrends: builder.query<any, { days?: number }>({
      query: ({ days = 30 }) => `analytics/extraction-trends?days=${days}`,
      providesTags: ['Analytics'],
    }),

    getTypeAnalysis: builder.query<any, void>({
      query: () => 'analytics/type-analysis',
      providesTags: ['Analytics'],
    }),

    getDepthAnalysis: builder.query<any, void>({
      query: () => 'analytics/depth-analysis',
      providesTags: ['Analytics'],
    }),

    getQueueFlowAnalysis: builder.query<any, { days?: number }>({
      query: ({ days = 7 }) => `analytics/queue-flow?days=${days}`,
      providesTags: ['Analytics'],
    }),

    getUserDecisionPatterns: builder.query<any, { days?: number }>({
      query: ({ days = 30 }) => `analytics/user-decisions?days=${days}`,
      providesTags: ['Analytics'],
    }),

    getContentQualityMetrics: builder.query<any, void>({
      query: () => 'analytics/content-quality',
      providesTags: ['Analytics'],
    }),

    getExtractionPerformance: builder.query<any, { days?: number }>({
      query: ({ days = 7 }) => `analytics/extraction-performance?days=${days}`,
      providesTags: ['Analytics'],
    }),

    getTopEntities: builder.query<any, {
      metric?: string;
      limit?: number;
      entity_type?: string;
    }>({
      query: ({ metric = 'num_links', limit = 20, entity_type }) => {
        const params = new URLSearchParams({ metric, limit: limit.toString() })
        if (entity_type) params.append('entity_type', entity_type)
        return `analytics/top-entities?${params.toString()}`
      },
      providesTags: ['Analytics'],
    }),

    // ===== EXISTING SYSTEM ENDPOINTS (unchanged) =====
    getSystemStats: builder.query<any, void>({
      query: () => 'system/stats',
    }),

    triggerSync: builder.mutation<any, { full_sync?: boolean }>({
      query: ({ full_sync = false }) => ({
        url: 'sync',
        method: 'POST',
        body: { full_sync },
      }),
      invalidatesTags: ['Entity', 'Queue', 'Dashboard', 'Analytics'],
    }),

    validateSystem: builder.query<any, void>({
      query: () => 'validate',
    }),

    healthCheck: builder.query<any, void>({
      query: () => '/health',
    }),
  }),
})

export const {
  // ===== EXISTING ENTITY HOOKS (unchanged) =====
  useGetEntitiesQuery,
  useGetEntityQuery,
  useUpdateEntityMutation,
  useGetEntityPreviewQuery,
  useGetEntityRelationshipsQuery,
  useGetSearchSuggestionsQuery,

  // ===== NEW MANUAL ENTITY HOOK =====
  useAddManualEntityMutation,

  // ===== EXISTING QUEUE HOOKS (unchanged) =====
  useGetAllQueuesQuery,
  useGetQueueEntitiesQuery,
  useAddToQueueMutation,
  useUpdateQueueEntryMutation,
  useRemoveFromQueueMutation,
  useBatchQueueOperationMutation,
  useGetQueueStatsQuery,

  // ===== NEW REVIEW QUEUE HOOKS =====
  useGetReviewQueueSourcesQuery,
  useBulkApproveReviewMutation,
  useBulkRejectReviewMutation,

  // ===== NEW EXTRACTION HOOKS =====
  useStartExtractionMutation,
  usePauseExtractionMutation,
  useResumeExtractionMutation,
  useCancelExtractionMutation,
  useGetExtractionStatusQuery,
  useConfigureExtractionMutation,
  useGetExtractionConfigQuery,
  useGetExtractionSessionsQuery,
  useGetSessionLogsQuery,
  useGetExtractionQueueStatsQuery,

  // ===== NEW DEDUPLICATION HOOKS =====
  useGetDeduplicationStatsQuery,

  // ===== EXISTING ANALYTICS HOOKS (unchanged) =====
  useGetDashboardStatsQuery,
  useGetExtractionTrendsQuery,
  useGetTypeAnalysisQuery,
  useGetDepthAnalysisQuery,
  useGetQueueFlowAnalysisQuery,
  useGetUserDecisionPatternsQuery,
  useGetContentQualityMetricsQuery,
  useGetExtractionPerformanceQuery,
  useGetTopEntitiesQuery,

  // ===== EXISTING SYSTEM HOOKS (unchanged) =====
  useGetSystemStatsQuery,
  useTriggerSyncMutation,
  useValidateSystemQuery,
  useHealthCheckQuery,
} = api