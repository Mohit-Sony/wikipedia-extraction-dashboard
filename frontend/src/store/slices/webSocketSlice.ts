// src/store/slices/webSocketSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { WebSocketMessage } from '../../types'

interface WebSocketState {
  connected: boolean
  connecting: boolean
  error: string | null
  lastMessage: WebSocketMessage | null
  subscriptions: string[]
  connectionCount: number
  reconnectAttempts: number
  lastPing: string | null
}

const initialState: WebSocketState = {
  connected: false,
  connecting: false,
  error: null,
  lastMessage: null,
  subscriptions: [],
  connectionCount: 0,
  reconnectAttempts: 0,
  lastPing: null,
}

export const webSocketSlice = createSlice({
  name: 'webSocket',
  initialState,
  reducers: {
    connectionStarted: (state) => {
      state.connecting = true
      state.error = null
    },
    
    connectionEstablished: (state, action: PayloadAction<{ connectionCount: number }>) => {
      state.connected = true
      state.connecting = false
      state.error = null
      state.reconnectAttempts = 0
      state.connectionCount = action.payload.connectionCount
    },
    
    connectionFailed: (state, action: PayloadAction<string>) => {
      state.connected = false
      state.connecting = false
      state.error = action.payload
      state.reconnectAttempts += 1
    },
    
    connectionClosed: (state) => {
      state.connected = false
      state.connecting = false
    },
    
    messageReceived: (state, action: PayloadAction<WebSocketMessage>) => {
      state.lastMessage = action.payload
      state.error = null
    },
    
    subscriptionUpdated: (state, action: PayloadAction<string[]>) => {
      state.subscriptions = action.payload
    },
    
    pingReceived: (state, action: PayloadAction<string>) => {
      state.lastPing = action.payload
    },
    
    resetReconnectAttempts: (state) => {
      state.reconnectAttempts = 0
    },
    
    clearError: (state) => {
      state.error = null
    },
  },
})

export const {
  connectionStarted,
  connectionEstablished,
  connectionFailed,
  connectionClosed,
  messageReceived,
  subscriptionUpdated,
  pingReceived,
  resetReconnectAttempts,
  clearError,
} = webSocketSlice.actions

// Selectors
export const selectWebSocketConnected = (state: { webSocket: WebSocketState }) => state.webSocket.connected
export const selectWebSocketConnecting = (state: { webSocket: WebSocketState }) => state.webSocket.connecting
export const selectWebSocketError = (state: { webSocket: WebSocketState }) => state.webSocket.error
export const selectLastMessage = (state: { webSocket: WebSocketState }) => state.webSocket.lastMessage
export const selectSubscriptions = (state: { webSocket: WebSocketState }) => state.webSocket.subscriptions
export const selectReconnectAttempts = (state: { webSocket: WebSocketState }) => state.webSocket.reconnectAttempts