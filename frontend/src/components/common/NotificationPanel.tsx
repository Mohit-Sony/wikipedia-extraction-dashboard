// src/components/common/NotificationPanel.tsx
import React from 'react'
import { Dropdown, List, Button, Typography, Empty, Space, Tag } from 'antd'
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  InfoCircleOutlined, 
  WarningOutlined,
  DeleteOutlined,
  ClearOutlined
} from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { 
  selectNotifications, 
  removeNotification, 
  clearAllNotifications 
} from '../../store/slices/notificationSlice'
import { NotificationMessage } from '../../types'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Text, Title } = Typography

interface NotificationPanelProps {
  children: React.ReactNode
}

export const NotificationPanel: React.FC<NotificationPanelProps> = ({ children }) => {
  const notifications = useSelector(selectNotifications)
  const dispatch = useDispatch()

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />
    }
  }

  const getTypeTag = (type: string) => {
    const colors = {
      success: 'success',
      error: 'error',
      warning: 'warning',
      info: 'processing'
    }
    return <Tag color={colors[type as keyof typeof colors] || 'default'}>{type}</Tag>
  }

  const handleRemoveNotification = (id: string) => {
    dispatch(removeNotification(id))
  }

  const handleClearAll = () => {
    dispatch(clearAllNotifications())
  }

  const overlay = (
    <div className="notification-panel" style={{ width: 400, maxHeight: 600, overflow: 'hidden' }}>
      <div style={{ 
        padding: '16px 20px', 
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Title level={5} style={{ margin: 0 }}>
          Notifications ({notifications.length})
        </Title>
        {notifications.length > 0 && (
          <Button 
            type="text" 
            size="small" 
            icon={<ClearOutlined />}
            onClick={handleClearAll}
          >
            Clear All
          </Button>
        )}
      </div>
      
      <div style={{ maxHeight: 500, overflow: 'auto' }}>
        {notifications.length === 0 ? (
          <div style={{ padding: 40 }}>
            <Empty 
              description="No notifications"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </div>
        ) : (
          <List
            dataSource={notifications}
            renderItem={(notification: NotificationMessage) => (
              <List.Item
                key={notification.id}
                style={{ 
                  padding: '12px 20px',
                  borderBottom: '1px solid #f5f5f5',
                  cursor: 'pointer'
                }}
                actions={[
                  <Button
                    key="delete"
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveNotification(notification.id)
                    }}
                  />
                ]}
                onClick={() => handleRemoveNotification(notification.id)}
              >
                <List.Item.Meta
                  avatar={getIcon(notification.type)}
                  title={
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'flex-start',
                      marginBottom: 4
                    }}>
                      <Text strong style={{ fontSize: 14 }}>
                        {notification.title}
                      </Text>
                      <Space>
                        {getTypeTag(notification.type)}
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(notification.timestamp).fromNow()}
                        </Text>
                      </Space>
                    </div>
                  }
                  description={
                    <Text 
                      type="secondary" 
                      style={{ 
                        fontSize: 13, 
                        lineHeight: 1.4,
                        display: 'block'
                      }}
                    >
                      {notification.message}
                    </Text>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </div>
    </div>
  )

  return (
    <Dropdown 
      overlay={overlay} 
      trigger={['click']} 
      placement="bottomRight"
      arrow
    >
      {children}
    </Dropdown>
  )
}