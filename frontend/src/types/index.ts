// src/types/index.ts

// ===== EXISTING TYPES (unchanged) =====
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

// ===== UPDATED ENUMS =====
export enum QueueType {
  UNPROCESSED = 'unprocessed',
  ACTIVE = 'active',
  REVIEW = 'review',           // NEW
  REJECTED = 'rejected',
  ON_HOLD = 'on_hold',
  COMPLETED = 'completed',
  FAILED = 'failed',
  PROCESSING = 'processing'    // NEW
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

// ===== NEW EXTRACTION TYPES =====
export enum ExtractionStatus {
  IDLE = 'idle',
  RUNNING = 'running',
  PAUSED = 'paused',
  CANCELLED = 'cancelled',
  COMPLETED = 'completed',
  ERROR = 'error'
}

export interface ExtractionConfig {
  max_depth: number;
  batch_size: number;
  max_workers: number;
  pause_between_requests: number;
  auto_save_interval: number;
  enable_deduplication: boolean;
  retry_attempts: number;
  retry_delay: number;
}

export interface ExtractionSession {
  id: number;
  session_name: string;
  start_time: string;
  end_time?: string;
  status: ExtractionStatus;
  total_extracted: number;
  total_errors: number;
  total_duplicates: number;
  config_snapshot: ExtractionConfig;
  current_depth: number;
  queue_size: number;
}

export interface ExtractionProgress {
  session_id: string
  current_entity_qid: string | null
  current_entity_title: string | null
  progress_percentage: number
  processed_count: number
  total_count: number
  discovered_links: number
  skipped_duplicates: number
  timestamp: string // ISO 8601 datetime string
}

export interface ExtractionLog {
  id: number;
  session_id: number;
  qid: string;
  title: string;
  action: string;
  status: string;
  error_message?: string;
  processing_time?: number;
  timestamp: string;
}

// ===== NEW QUEUE ENTRY TYPES =====
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
  discovered_by?: string;        // NEW
  discovery_source?: string;     // NEW
  entity: Entity;
}

// ===== NEW DEDUPLICATION TYPES =====
export interface DeduplicationStats {
  total_discovered: number;
  total_duplicates: number;
  deduplication_rate: number;
  duplicates_by_status: {
    completed: number;
    rejected: number;
    in_queue: number;
    processing: number;
  };
  discovery_sources: {
    [source: string]: number;
  };
}

export interface DiscoverySource {
  type: string;
  discovered_count: number;
  last_discovery: string;
  qid: string;
  title: string;
}

// ===== NEW MANUAL ENTITY TYPES =====
export interface ManualEntityRequest {
  qid?: string;
  title: string;
  type?: string;
  short_desc?: string;
  priority?: Priority;
  notes?: string;
}

export interface ManualEntityResponse {
  success: boolean;
  message: string;
  entity?: Entity;
  queue_entry?: QueueEntry;
  was_duplicate?: boolean;
  existing_status?: string;
}

// ===== NEW BULK OPERATION TYPES =====
export interface BulkReviewOperation {
  operation: 'approve' | 'reject';
  qids: string[];
  target_queue?: QueueType;
  priority?: Priority;
  notes?: string;
}

export interface BulkReviewResult {
  success_count: number;
  error_count: number;
  duplicate_count: number;
  errors: Array<{
    qid: string;
    error: string;
  }>;
}

// ===== NEW WEBSOCKET EVENT TYPES =====
export interface ExtractionProgressEvent {
  type: 'extraction_progress';
  data: ExtractionProgress;
}

export interface LinksDiscoveredEvent {
  type: 'links_discovered';
  data: {
    session_id: number;
    parent_qid: string;
    parent_title: string;
    links_found: number;
    new_entities: number;
    duplicates: number;
    discovery_source: string;
  };
}

export interface ExtractionStatusChangeEvent {
  type: 'extraction_status_change';
  data: {
    session_id: number;
    old_status: ExtractionStatus;
    new_status: ExtractionStatus;
    message: string;
  };
}

export interface DeduplicationStatsEvent {
  type: 'deduplication_stats';
  data: DeduplicationStats;
}

// ===== EXISTING TYPES (unchanged) =====
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