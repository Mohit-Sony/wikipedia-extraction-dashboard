// src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { api } from '../store/api'
import {
  connectionStarted,
  connectionEstablished,
  connectionFailed,
  connectionClosed,
  messageReceived,
  subscriptionUpdated,
  pingReceived,
  selectWebSocketConnected,
  selectWebSocketConnecting,
  selectReconnectAttempts,
  selectSubscriptions
} from '../store/slices/webSocketSlice'
import {
  addSuccessNotification,
  addErrorNotification,
  addInfoNotification,
  addWarningNotification
} from '../store/slices/notificationSlice'
import type { 
  WebSocketMessage,
  ExtractionProgressEvent,
  LinksDiscoveredEvent,
  ExtractionStatusChangeEvent,
  DeduplicationStatsEvent
} from '../types'

const WEBSOCKET_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8001/api/v1/ws"
const RECONNECT_INTERVAL = 5000 // 5 seconds
const MAX_RECONNECT_ATTEMPTS = 5
const PING_INTERVAL = 30000 // 30 seconds

export const useWebSocket = () => {
  const dispatch = useDispatch()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const pingIntervalRef = useRef<number | null>(null)
  
  const connected = useSelector(selectWebSocketConnected)
  const connecting = useSelector(selectWebSocketConnecting)
  const reconnectAttempts = useSelector(selectReconnectAttempts)
  const subscriptions = useSelector(selectSubscriptions)

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      dispatch(messageReceived(message))
      
      // Handle different message types
      switch (message.type) {
        case 'connection_established':
          dispatch(connectionEstablished({ 
            connectionCount: message.data.connection_count 
          }))
          dispatch(addSuccessNotification({
            title: 'Connected',
            message: 'Real-time updates are now active',
            duration: 3000
          }))
          break

        // ===== EXISTING HANDLERS (unchanged) =====
        case 'entity_processed':
          dispatch(api.util.invalidateTags(['Entity', 'Queue', 'Dashboard']))
          
          dispatch(addInfoNotification({
            title: 'Entity Processed',
            message: `${message.data.title} has been processed`,
            duration: 5000
          }))
          break
          
        case 'queue_updated':
          dispatch(api.util.invalidateTags(['Queue', 'Dashboard']))
          
          if (message.data.change_type === 'added') {
            dispatch(addInfoNotification({
              title: 'Queue Updated',
              message: `Entity added to ${message.data.queue_type} queue`,
              duration: 3000
            }))
          }
          break
          
        case 'batch_operation_complete':
          dispatch(api.util.invalidateTags(['Entity', 'Queue', 'Dashboard']))
          
          const { operation, success_count, error_count } = message.data
          if (error_count > 0) {
            dispatch(addWarningNotification({
              title: 'Batch Operation Completed',
              message: `${operation}: ${success_count} successful, ${error_count} errors`,
              duration: 5000
            }))
          } else {
            dispatch(addSuccessNotification({
              title: 'Batch Operation Completed',
              message: `${operation}: ${success_count} entities processed successfully`,
              duration: 4000
            }))
          }
          break
          
        case 'system_status_change':
          const { status, message: statusMessage } = message.data
          
          if (status === 'sync_completed') {
            dispatch(api.util.invalidateTags(['Entity', 'Queue', 'Dashboard', 'Analytics']))
            dispatch(addSuccessNotification({
              title: 'Sync Completed',
              message: statusMessage,
              duration: 4000
            }))
          } else if (status === 'sync_failed') {
            dispatch(addErrorNotification({
              title: 'Sync Failed',
              message: statusMessage,
              duration: 0
            }))
          }
          break

        // ===== NEW EXTRACTION EVENT HANDLERS =====
        case 'extraction_progress':
          handleExtractionProgress(message as ExtractionProgressEvent)
          break

        case 'links_discovered':
          handleLinksDiscovered(message as LinksDiscoveredEvent)
          break

        case 'extraction_status_change':
          handleExtractionStatusChange(message as ExtractionStatusChangeEvent)
          break

        case 'deduplication_stats':
          handleDeduplicationStats(message as DeduplicationStatsEvent)
          break

        // ===== EXISTING HANDLERS (unchanged) =====
        case 'error_occurred':
          dispatch(addErrorNotification({
            title: 'System Error',
            message: message.data.error_message,
            duration: 0
          }))
          break
          
        case 'pong':
          dispatch(pingReceived(message.data.timestamp))
          break
          
        case 'subscription_confirmed':
          dispatch(subscriptionUpdated(message.data.topics))
          break
          
        default:
          console.log('Unhandled WebSocket message:', message)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }, [dispatch])

  // ===== NEW EVENT HANDLERS =====
  const handleExtractionProgress = useCallback((event: ExtractionProgressEvent) => {
    const { data } = event
    
    // Invalidate extraction-related queries to trigger refetch
    dispatch(api.util.invalidateTags(['Extraction', 'Queue']))
    
    // Show progress notification (less frequent to avoid spam)
    if (data.progress_percentage % 10 === 0 || data.progress_percentage <= 100) {
      const progressPercent = data.progress_percentage  

      dispatch(addInfoNotification({
        title: 'Extraction Progress',
        message: `Processing ${data.current_entity_qid} - ${data.current_entity_title} done - ${data.processed_count} processed (${progressPercent}%)`,
        duration: 3000
      }))
    }

    // Show completion notification
    if (data.progress_percentage === 100) {
      dispatch(addSuccessNotification({
        title: 'Extraction Completed',
        message: `Successfully processed ${data.processed_count} entities`,
        duration: 6000
      }))
    }

    // // Show error notification
    // if (data.status === 'error') {
    //   dispatch(addErrorNotification({
    //     title: 'Extraction Error',
    //     message: `Extraction stopped due to error at entity: ${data.current_entity}`,
    //     duration: 0
    //   }))
    // }
  }, [dispatch])

  const handleLinksDiscovered = useCallback((event: LinksDiscoveredEvent) => {
    const { data } = event
    
    // Invalidate relevant queries
    dispatch(api.util.invalidateTags(['Queue', 'DeduplicationStats']))
    
    // Show discovery notification
    if (data.new_entities > 0) {
      dispatch(addInfoNotification({
        title: 'New Links Discovered',
        message: `Found ${data.new_entities} new entities from ${data.parent_title} (${data.duplicates} duplicates filtered)`,
        duration: 4000
      }))
    }

    // Show high duplicate rate warning
    if (data.links_found > 0 && data.duplicates / data.links_found > 0.8) {
      dispatch(addWarningNotification({
        title: 'High Duplicate Rate',
        message: `${Math.round((data.duplicates / data.links_found) * 100)}% of links from ${data.parent_title} were duplicates`,
        duration: 5000
      }))
    }
  }, [dispatch])

  const handleExtractionStatusChange = useCallback((event: ExtractionStatusChangeEvent) => {
    const { data } = event
    
    // Invalidate extraction queries
    dispatch(api.util.invalidateTags(['Extraction']))
    
    // Show status change notifications
    switch (data.new_status) {
      case 'running':
        dispatch(addSuccessNotification({
          title: 'Extraction Started',
          message: data.message,
          duration: 4000
        }))
        break
        
      case 'paused':
        dispatch(addWarningNotification({
          title: 'Extraction Paused',
          message: data.message,
          duration: 4000
        }))
        break
        
      case 'cancelled':
        dispatch(addWarningNotification({
          title: 'Extraction Cancelled',
          message: data.message,
          duration: 5000
        }))
        break
        
      case 'completed':
        dispatch(addSuccessNotification({
          title: 'Extraction Completed',
          message: data.message,
          duration: 6000
        }))
        break
        
      case 'error':
        dispatch(addErrorNotification({
          title: 'Extraction Failed',
          message: data.message,
          duration: 0
        }))
        break
        
      default:
        dispatch(addInfoNotification({
          title: 'Extraction Status Changed',
          message: `Status changed to ${data.new_status}`,
          duration: 3000
        }))
    }
  }, [dispatch])

  const handleDeduplicationStats = useCallback((event: DeduplicationStatsEvent) => {
    const { data } = event
    
    // Invalidate deduplication stats
    dispatch(api.util.invalidateTags(['DeduplicationStats']))
    
    // Show efficiency notification for high deduplication rates
    if (data.deduplication_rate > 0.9) {
      dispatch(addInfoNotification({
        title: 'High Deduplication Efficiency',
        message: `${Math.round(data.deduplication_rate * 100)}% of discovered entities were duplicates`,
        duration: 4000
      }))
    }
    
    // Show discovery source stats
    const topSource = Object.entries(data.discovery_sources)
      .sort(([,a], [,b]) => b - a)[0]
    
    if (topSource && topSource[1] > 50) {
      dispatch(addInfoNotification({
        title: 'Discovery Source Update',
        message: `${topSource[0]} has discovered ${topSource[1]} entities`,
        duration: 3000
      }))
    }
  }, [dispatch])

  // ===== CONNECTION MANAGEMENT (unchanged) =====
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || connecting) {
      return
    }

    dispatch(connectionStarted())
    
    try {
      wsRef.current = new WebSocket(WEBSOCKET_URL)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        
        // Subscribe to all updates including new extraction events
        const subscribeMessage = {
          type: 'subscribe',
          data: { 
            topics: [
              'entities', 
              'queues', 
              'progress', 
              'batch_operations', 
              'errors', 
              'extraction_progress',      // NEW
              'links_discovered',        // NEW
              'extraction_status',       // NEW
              'deduplication_stats',     // NEW
              'all'
            ] 
          }
        }
        
        wsRef.current?.send(JSON.stringify(subscribeMessage))
        
        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping', data: {} }))
          }
        }, PING_INTERVAL)
      }
      
      wsRef.current.onmessage = handleMessage
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        dispatch(connectionClosed())
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }
        
        // Attempt to reconnect if not a manual close
        if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, RECONNECT_INTERVAL)
        }
      }
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        dispatch(connectionFailed('WebSocket connection error'))
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      dispatch(connectionFailed('Failed to create WebSocket connection'))
    }
  }, [dispatch, connecting, reconnectAttempts, handleMessage])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
      return true
    }
    return false
  }, [])

  const subscribe = useCallback((topics: string[]) => {
    return sendMessage({
      type: 'subscribe',
      data: { topics }
    })
  }, [sendMessage])

  const unsubscribe = useCallback((topics: string[]) => {
    return sendMessage({
      type: 'unsubscribe',
      data: { topics }
    })
  }, [sendMessage])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    connected,
    connecting,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
    reconnectAttempts,
    subscriptions
  }
}