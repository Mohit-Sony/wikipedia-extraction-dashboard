// src/store/slices/notificationSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { NotificationMessage } from '../../types'

interface NotificationState {
  notifications: NotificationMessage[]
  maxNotifications: number
}

const initialState: NotificationState = {
  notifications: [],
  maxNotifications: 10,
}

export const notificationSlice = createSlice({
  name: 'notifications',
  initialState,
  reducers: {
    addNotification: (state, action: PayloadAction<Omit<NotificationMessage, 'id' | 'timestamp'>>) => {
      const notification: NotificationMessage = {
        ...action.payload,
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
      }
      
      state.notifications.unshift(notification)
      
      // Keep only the latest notifications
      if (state.notifications.length > state.maxNotifications) {
        state.notifications = state.notifications.slice(0, state.maxNotifications)
      }
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      )
    },
    
    clearAllNotifications: (state) => {
      state.notifications = []
    },
    
    markAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload)
      if (notification) {
        // You could add a 'read' property to NotificationMessage if needed
      }
    },
    
    addSuccessNotification: (state, action: PayloadAction<{ title: string; message: string; duration?: number }>) => {
      const notification: NotificationMessage = {
        ...action.payload,
        type: 'success',
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
      }
      
      state.notifications.unshift(notification)
      
      if (state.notifications.length > state.maxNotifications) {
        state.notifications = state.notifications.slice(0, state.maxNotifications)
      }
    },
    
    addErrorNotification: (state, action: PayloadAction<{ title: string; message: string; duration?: number }>) => {
      const notification: NotificationMessage = {
        ...action.payload,
        type: 'error',
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
        duration: action.payload.duration || 0, // Error notifications don't auto-dismiss by default
      }
      
      state.notifications.unshift(notification)
      
      if (state.notifications.length > state.maxNotifications) {
        state.notifications = state.notifications.slice(0, state.maxNotifications)
      }
    },
    
    addWarningNotification: (state, action: PayloadAction<{ title: string; message: string; duration?: number }>) => {
      const notification: NotificationMessage = {
        ...action.payload,
        type: 'warning',
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
      }
      
      state.notifications.unshift(notification)
      
      if (state.notifications.length > state.maxNotifications) {
        state.notifications = state.notifications.slice(0, state.maxNotifications)
      }
    },
    
    addInfoNotification: (state, action: PayloadAction<{ title: string; message: string; duration?: number }>) => {
      const notification: NotificationMessage = {
        ...action.payload,
        type: 'info',
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
      }
      
      state.notifications.unshift(notification)
      
      if (state.notifications.length > state.maxNotifications) {
        state.notifications = state.notifications.slice(0, state.maxNotifications)
      }
    },
  },
})

export const {
  addNotification,
  removeNotification,
  clearAllNotifications,
  markAsRead,
  addSuccessNotification,
  addErrorNotification,
  addWarningNotification,
  addInfoNotification,
} = notificationSlice.actions

// Selectors
export const selectNotifications = (state: { notifications: NotificationState }) => 
  state.notifications.notifications

export const selectUnreadNotifications = (state: { notifications: NotificationState }) =>
  state.notifications.notifications // Could filter by read status if implemented

export const selectNotificationCount = (state: { notifications: NotificationState }) =>
  state.notifications.notifications.length