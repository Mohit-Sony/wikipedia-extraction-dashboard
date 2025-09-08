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
  Priority
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
  tagTypes: ['Entity', 'Queue', 'Analytics', 'Dashboard'],
  endpoints: (builder) => ({
    // Entity endpoints
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

    // Queue endpoints
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
    }>({
      query: ({ queue_type, limit = 50, offset = 0, sort_by = 'added_date', sort_order = 'desc' }) =>
        `queues/${queue_type}?limit=${limit}&offset=${offset}&sort_by=${sort_by}&sort_order=${sort_order}`,
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

    // Analytics endpoints
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

    // System endpoints
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

    // Health check
    healthCheck: builder.query<any, void>({
      query: () => '/health',
    }),
  }),
})

export const {
  // Entity hooks
  useGetEntitiesQuery,
  useGetEntityQuery,
  useUpdateEntityMutation,
  useGetEntityPreviewQuery,
  useGetEntityRelationshipsQuery,
  useGetSearchSuggestionsQuery,

  // Queue hooks
  useGetAllQueuesQuery,
  useGetQueueEntitiesQuery,
  useAddToQueueMutation,
  useUpdateQueueEntryMutation,
  useRemoveFromQueueMutation,
  useBatchQueueOperationMutation,
  useGetQueueStatsQuery,

  // Analytics hooks
  useGetDashboardStatsQuery,
  useGetExtractionTrendsQuery,
  useGetTypeAnalysisQuery,
  useGetDepthAnalysisQuery,
  useGetQueueFlowAnalysisQuery,
  useGetUserDecisionPatternsQuery,
  useGetContentQualityMetricsQuery,
  useGetExtractionPerformanceQuery,
  useGetTopEntitiesQuery,

  // System hooks
  useGetSystemStatsQuery,
  useTriggerSyncMutation,
  useValidateSystemQuery,
  useHealthCheckQuery,
} = api