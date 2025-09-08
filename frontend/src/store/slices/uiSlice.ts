// src/store/slices/uiSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { EntityFilter, UIState, QueueType, EntityStatus } from '../../types'

const initialFilters: EntityFilter = {
  search: '',
  types: [],
  status: [],
  queue_type: [],
  parent_qid: '',
  depth_min: undefined,
  depth_max: undefined,
  links_min: undefined,
  links_max: undefined,
  page_length_min: undefined,
  page_length_max: undefined,
  limit: 50,
  offset: 0,
  sort_by: 'updated_at',
  sort_order: 'desc'
}

const initialState: UIState = {
  selectedEntities: [],
  currentView: 'table',
  sidebarCollapsed: false,
  filters: initialFilters,
  loading: false,
  error: null,
}

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setSelectedEntities: (state, action: PayloadAction<string[]>) => {
      state.selectedEntities = action.payload
    },
    
    toggleEntitySelection: (state, action: PayloadAction<string>) => {
      const qid = action.payload
      const index = state.selectedEntities.indexOf(qid)
      if (index === -1) {
        state.selectedEntities.push(qid)
      } else {
        state.selectedEntities.splice(index, 1)
      }
    },
    
    selectAllEntities: (state, action: PayloadAction<string[]>) => {
      state.selectedEntities = action.payload
    },
    
    clearSelection: (state) => {
      state.selectedEntities = []
    },
    
    setCurrentView: (state, action: PayloadAction<'table' | 'grid' | 'network'>) => {
      state.currentView = action.payload
    },
    
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed
    },
    
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload
    },
    
    updateFilters: (state, action: PayloadAction<Partial<EntityFilter>>) => {
      state.filters = { ...state.filters, ...action.payload }
      // Reset offset when filters change (except when it's explicitly set)
      if (!action.payload.hasOwnProperty('offset')) {
        state.filters.offset = 0
      }
    },
    
    resetFilters: (state) => {
      state.filters = { ...initialFilters }
      state.selectedEntities = []
    },
    
    setSearch: (state, action: PayloadAction<string>) => {
      state.filters.search = action.payload
      state.filters.offset = 0
    },
    
    addTypeFilter: (state, action: PayloadAction<string>) => {
      if (!state.filters.types?.includes(action.payload)) {
        state.filters.types = [...(state.filters.types || []), action.payload]
        state.filters.offset = 0
      }
    },
    
    removeTypeFilter: (state, action: PayloadAction<string>) => {
      state.filters.types = state.filters.types?.filter(type => type !== action.payload) || []
      state.filters.offset = 0
    },
    
    addStatusFilter: (state, action: PayloadAction<EntityStatus>) => {
      if (!state.filters.status?.includes(action.payload)) {
        state.filters.status = [...(state.filters.status || []), action.payload]
        state.filters.offset = 0
      }
    },
    
    removeStatusFilter: (state, action: PayloadAction<EntityStatus>) => {
      state.filters.status = state.filters.status?.filter(status => status !== action.payload) || []
      state.filters.offset = 0
    },
    
    addQueueTypeFilter: (state, action: PayloadAction<QueueType>) => {
      if (!state.filters.queue_type?.includes(action.payload)) {
        state.filters.queue_type = [...(state.filters.queue_type || []), action.payload]
        state.filters.offset = 0
      }
    },
    
    removeQueueTypeFilter: (state, action: PayloadAction<QueueType>) => {
      state.filters.queue_type = state.filters.queue_type?.filter(qt => qt !== action.payload) || []
      state.filters.offset = 0
    },
    
    setSorting: (state, action: PayloadAction<{ sort_by: string; sort_order: 'asc' | 'desc' }>) => {
      state.filters.sort_by = action.payload.sort_by
      state.filters.sort_order = action.payload.sort_order
      state.filters.offset = 0
    },
    
    setPagination: (state, action: PayloadAction<{ limit?: number; offset?: number }>) => {
      if (action.payload.limit !== undefined) {
        state.filters.limit = action.payload.limit
      }
      if (action.payload.offset !== undefined) {
        state.filters.offset = action.payload.offset
      }
    },
    
    nextPage: (state) => {
      state.filters.offset += state.filters.limit
    },
    
    prevPage: (state) => {
      state.filters.offset = Math.max(0, state.filters.offset - state.filters.limit)
    },
    
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload
    },
    
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
  },
})

export const {
  setSelectedEntities,
  toggleEntitySelection,
  selectAllEntities,
  clearSelection,
  setCurrentView,
  toggleSidebar,
  setSidebarCollapsed,
  updateFilters,
  resetFilters,
  setSearch,
  addTypeFilter,
  removeTypeFilter,
  addStatusFilter,
  removeStatusFilter,
  addQueueTypeFilter,
  removeQueueTypeFilter,
  setSorting,
  setPagination,
  nextPage,
  prevPage,
  setLoading,
  setError,
} = uiSlice.actions

// Selectors
export const selectSelectedEntities = (state: { ui: UIState }) => state.ui.selectedEntities
export const selectCurrentView = (state: { ui: UIState }) => state.ui.currentView
export const selectSidebarCollapsed = (state: { ui: UIState }) => state.ui.sidebarCollapsed
export const selectFilters = (state: { ui: UIState }) => state.ui.filters
export const selectLoading = (state: { ui: UIState }) => state.ui.loading
export const selectError = (state: { ui: UIState }) => state.ui.error