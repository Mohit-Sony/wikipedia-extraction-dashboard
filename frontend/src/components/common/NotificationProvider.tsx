// src/components/common/NotificationProvider.tsx
import React, { useEffect, useRef } from 'react'
import { notification } from 'antd'
import { useSelector, useDispatch } from 'react-redux'
import { 
  selectNotifications, 
  removeNotification 
} from '../../store/slices/notificationSlice'
import { NotificationMessage } from '../../types'

interface NotificationProviderProps {
  children: React.ReactNode
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const notifications = useSelector(selectNotifications)
  const dispatch = useDispatch()
  const shownNotifications = useRef<Set<string>>(new Set())

  useEffect(() => {
    // Configure notification settings
    notification.config({
      placement: 'topRight',
      duration: 4.5,
      maxCount: 5,
    })
  }, [])

  useEffect(() => {
    // Process new notifications
    notifications.forEach((notif: NotificationMessage) => {
      const key = notif.id
      
      // Check if notification is already shown using our ref
      if (shownNotifications.current.has(key)) {
        return
      }

      // Mark as shown
      shownNotifications.current.add(key)

      const config = {
        key,
        message: notif.title,
        description: notif.message,
        duration: notif.duration !== undefined ? notif.duration / 1000 : 4.5,
        onClose: () => {
          dispatch(removeNotification(notif.id))
          shownNotifications.current.delete(key)
        },
        onClick: () => {
          dispatch(removeNotification(notif.id))
          shownNotifications.current.delete(key)
        },
        className: `notification-${key}`, // Add custom class for tracking
        style: {
          cursor: 'pointer'
        }
      }

      switch (notif.type) {
        case 'success':
          notification.success(config)
          break
        case 'error':
          notification.error({
            ...config,
            duration: notif.duration !== undefined ? notif.duration / 1000 : 0 // Don't auto-close errors
          })
          break
        case 'warning':
          notification.warning(config)
          break
        case 'info':
          notification.info(config)
          break
        default:
          notification.open(config)
      }
    })
  }, [notifications, dispatch])

  // Clean up shown notifications ref when notifications are removed
  useEffect(() => {
    const currentNotificationIds = new Set(notifications.map(n => n.id))
    const toRemove: string[] = []
    
    shownNotifications.current.forEach(id => {
      if (!currentNotificationIds.has(id)) {
        toRemove.push(id)
      }
    })
    
    toRemove.forEach(id => {
      shownNotifications.current.delete(id)
    })
  }, [notifications])

  return <>{children}</>
}