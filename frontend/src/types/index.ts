// src/types/index.ts

export interface Entity {
    id: number;
    qid: string;
    title: string;
    type: string;
    short_desc?: string;
    num_links: number;
    num_tables: number;
    num_images: number;
    num_chunks: number;
    page_length: number;
    extraction_date?: string;
    last_modified?: string;
    file_path: string;
    status: EntityStatus;
    parent_qid?: string;
    depth: number;
    created_at: string;
    updated_at: string;
  }
  
  export interface EntityPreview {
    qid: string;
    title: string;
    type: string;
    content: {
      extract: string;
      description: string;
      summary: string;
    };
    infobox: Record<string, any>;
    links: {
      internal_count: number;
      external_count: number;
      sample_internal: Array<{
        qid: string;
        title: string;
        type: string;
        shortDesc?: string;
      }>;
    };
    metadata: {
      page_length: number;
      last_modified?: string;
      num_tables: number;
      num_images: number;
      num_chunks: number;
    };
  }
  
  export interface QueueEntry {
    id: number;
    qid: string;
    queue_type: QueueType;
    priority: Priority;
    position: number;
    added_by: string;
    added_date: string;
    processed_date?: string;
    notes?: string;
    entity: Entity;
  }
  
  export enum QueueType {
    UNPROCESSED = 'unprocessed',
    ACTIVE = 'active',
    REJECTED = 'rejected',
    ON_HOLD = 'on_hold',
    COMPLETED = 'completed',
    FAILED = 'failed',
    PROCESSING = 'processing'
  }
  
  export enum EntityStatus {
    UNPROCESSED = 'unprocessed',
    QUEUED = 'queued',
    PROCESSING = 'processing',
    COMPLETED = 'completed',
    FAILED = 'failed',
    REJECTED = 'rejected'
  }
  
  export enum Priority {
    HIGH = 1,
    MEDIUM = 2,
    LOW = 3
  }
  
  export interface EntityFilter {
    search?: string;
    types?: string[];
    status?: EntityStatus[];
    queue_type?: QueueType[];
    parent_qid?: string;
    depth_min?: number;
    depth_max?: number;
    links_min?: number;
    links_max?: number;
    page_length_min?: number;
    page_length_max?: number;
    limit: number;
    offset: number;
    sort_by: string;
    sort_order: 'asc' | 'desc';
  }
  
  export interface EntitiesResponse {
    entities: Entity[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  }
  
  export interface QueueResponse {
    queue_type: string;
    entries: QueueEntry[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  }
  
  export interface BatchOperation {
    operation: 'move' | 'delete' | 'update_priority' | 'update_status';
    qids: string[];
    target_queue?: QueueType;
    priority?: Priority;
    notes?: string;
  }
  
  export interface BatchOperationResult {
    success_count: number;
    error_count: number;
    errors: Array<{
      qid: string;
      error: string;
    }>;
  }
  
  export interface DashboardStats {
    total_entities: number;
    total_processed: number;
    total_pending: number;
    total_failed: number;
    queue_stats: QueueStats[];
    type_stats: TypeStats[];
    recent_activity: Entity[];
  }
  
  export interface QueueStats {
    queue_type: QueueType;
    count: number;
    avg_links: number;
    avg_page_length: number;
  }
  
  export interface TypeStats {
    type: string;
    count: number;
    avg_links: number;
    avg_page_length: number;
  }
  
  export interface WebSocketMessage {
    type: string;
    data: any;
  }
  
  export interface EntityRelationship {
    source: string;
    target: string;
    title: string;
    type: string;
    description: string;
  }
  
  export interface NetworkGraphData {
    nodes: Array<{
      id: string;
      label: string;
      type: string;
      size?: number;
      color?: string;
    }>;
    edges: Array<{
      source: string;
      target: string;
      label?: string;
    }>;
  }
  
  export interface AnalyticsData {
    extraction_trends: Array<{
      date: string;
      count: number;
    }>;
    type_analysis: Array<{
      type: string;
      total_count: number;
      completed_count: number;
      failed_count: number;
      success_rate: number;
      avg_links: number;
      avg_tables: number;
      avg_images: number;
      avg_page_length: number;
    }>;
    depth_analysis: Array<{
      depth: number;
      count: number;
      avg_links: number;
      avg_page_length: number;
    }>;
  }
  
  export interface SearchSuggestion {
    qid: string;
    title: string;
    type: string;
  }
  
  // UI State interfaces
  export interface UIState {
    selectedEntities: string[];
    currentView: 'table' | 'grid' | 'network';
    sidebarCollapsed: boolean;
    filters: EntityFilter;
    loading: boolean;
    error: string | null;
  }
  
  export interface NotificationMessage {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    timestamp: string;
    duration?: number;
  }