
// src/components/dashboard/QueueOverview.tsx
import React from 'react'
import { Card, Row, Col, Progress, Typography,  } from 'antd'
import { UnorderedListOutlined } from '@ant-design/icons'
import { QueueStats } from '../../types'

const { Title , Text } = Typography

interface QueueOverviewProps {
  queueStats: QueueStats[]
}

export const QueueOverview: React.FC<QueueOverviewProps> = ({ queueStats }) => {
  const getQueueColor = (queueType: string) => {
    switch (queueType) {
      case 'active':
        return '#1890ff'
      case 'completed':
        return '#52c41a'
      case 'failed':
        return '#ff4d4f'
      case 'rejected':
        return '#faad14'
      case 'on_hold':
        return '#722ed1'
      default:
        return '#d9d9d9'
    }
  }

  const totalEntities = queueStats.reduce((sum, stat) => sum + stat.count, 0)

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <UnorderedListOutlined />
          <Title level={4} style={{ margin: 0 }}>Queue Overview</Title>
        </div>
      }
      style={{ height: 400 }}
    >
      <Row gutter={[16, 16]}>
        {queueStats.map((stat) => {
          const percentage = totalEntities > 0 ? (stat.count / totalEntities) * 100 : 0
          return (
            <Col span={24} key={stat.queue_type}>
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Text strong style={{ textTransform: 'capitalize' }}>
                    {stat.queue_type.replace('_', ' ')}
                  </Text>
                  <Text>{stat.count}</Text>
                </div>
                <Progress 
                  percent={percentage} 
                  strokeColor={getQueueColor(stat.queue_type)}
                  size="small"
                  showInfo={false}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Avg Links: {stat.avg_links.toFixed(1)}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {percentage.toFixed(1)}%
                  </Text>
                </div>
              </div>
            </Col>
          )
        })}
      </Row>
    </Card>
  )
}
