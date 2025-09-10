// src/components/dashboard/RecentActivity.tsx
import React from 'react'
import { Card, List, Typography, Tag, Space, Avatar } from 'antd'
import { ClockCircleOutlined, UserOutlined, GlobalOutlined, TeamOutlined } from '@ant-design/icons'
import { Entity } from '../../types'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography

interface RecentActivityProps {
  recentActivity: Entity[]
}

export const RecentActivity: React.FC<RecentActivityProps> = ({ recentActivity }) => {
  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'human':
      case 'person':
        return <UserOutlined />
      case 'place':
      case 'location':
        return <GlobalOutlined />
      case 'organization':
        return <TeamOutlined />
      default:
        return <ClockCircleOutlined />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'human':
      case 'person':
        return 'blue'
      case 'place':
      case 'location':
        return 'green'
      case 'organization':
        return 'purple'
      case 'event':
        return 'orange'
      default:
        return 'default'
    }
  }

  return (
    <Card 
      title={
        <Space>
          <ClockCircleOutlined />
          <Title level={4} style={{ margin: 0 }}>Recent Activity</Title>
        </Space>
      }
      bodyStyle={{ padding: 0 }}
    >
      <List
        dataSource={recentActivity}
        renderItem={(entity) => (
          <List.Item style={{ padding: '12px 24px' }}>
            <List.Item.Meta
              avatar={
                <Avatar 
                  icon={getTypeIcon(entity.type)} 
                  style={{ backgroundColor: '#f0f2f5', color: '#1890ff' }}
                />
              }
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong>{entity.title}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {dayjs(entity.updated_at).fromNow()}
                  </Text>
                </div>
              }
              description={
                <Space>
                  <Tag color={getTypeColor(entity.type)}>{entity.type}</Tag>
                  <Text type="secondary">{entity.num_links} links</Text>
                  <Text type="secondary">{entity.page_length.toLocaleString()} chars</Text>
                </Space>
              }
            />
          </List.Item>
        )}
        locale={{ emptyText: 'No recent activity' }}
      />
    </Card>
  )
}
