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
import type { WebSocketMessage } from '../types'

// const WEBSOCKET_URL = process.env.DEV 
//   ? 'ws://localhost:8000/api/v1/ws'
//   : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws`

const WEBSOCKET_URL = "ws://localhost:8000/api/v1/ws"
const RECONNECT_INTERVAL = 5000 // 5 seconds
const MAX_RECONNECT_ATTEMPTS = 5
const PING_INTERVAL = 30000 // 30 seconds

export const useWebSocket = () => {
  const dispatch = useDispatch()
  const wsRef = useRef<WebSocket | null>(null)
//   const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
//   const pingIntervalRef = useRef<NodeJS.Timeout | null>(null)
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
          
        case 'entity_processed':
          // Invalidate relevant queries to trigger refetch
          dispatch(api.util.invalidateTags(['Entity', 'Queue', 'Dashboard']))
          
          dispatch(addInfoNotification({
            title: 'Entity Processed',
            message: `${message.data.title} has been processed`,
            duration: 5000
          }))
          break
          
        case 'queue_updated':
          // Invalidate queue-related queries
          dispatch(api.util.invalidateTags(['Queue', 'Dashboard']))
          
          if (message.data.change_type === 'added') {
            dispatch(addInfoNotification({
              title: 'Queue Updated',
              message: `Entity added to ${message.data.queue_type} queue`,
              duration: 3000
            }))
          }
          break
          
        case 'extraction_progress':
          // Update progress in UI if needed
          const { current, total, percentage, current_entity } = message.data
          dispatch(addInfoNotification({
            title: 'Extraction Progress',
            message: `Processing ${current_entity} (${current}/${total} - ${percentage}%)`,
            duration: 2000
          }))
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
              duration: 0 // Don't auto-dismiss errors
            }))
          }
          break
          
        case 'error_occurred':
          dispatch(addErrorNotification({
            title: 'System Error',
            message: message.data.error_message,
            duration: 0 // Don't auto-dismiss errors
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

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || connecting) {
      return
    }

    dispatch(connectionStarted())
    
    try {
      wsRef.current = new WebSocket(WEBSOCKET_URL)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        
        // Subscribe to all updates by default
        const subscribeMessage = {
          type: 'subscribe',
          data: { topics: ['entities', 'queues', 'progress', 'batch_operations', 'errors', 'all'] }
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