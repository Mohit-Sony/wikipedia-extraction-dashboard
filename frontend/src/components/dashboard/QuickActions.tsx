
// src/components/dashboard/QuickActions.tsx
import React from 'react'
import { Card, Button, Space, Typography, Divider } from 'antd'
import { 
  SyncOutlined, 
  DatabaseOutlined, 
  BarChartOutlined, 
  SettingOutlined,
  PlayCircleOutlined,
  
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTriggerSyncMutation } from '../../store/api'

const { Title, Text } = Typography

export const QuickActions: React.FC = () => {
  const navigate = useNavigate()
  const [triggerSync, { isLoading: syncLoading }] = useTriggerSyncMutation()

  const handleSync = async () => {
    try {
      await triggerSync({ full_sync: false }).unwrap()
    } catch (error) {
      console.error('Sync failed:', error)
    }
  }

  const handleFullSync = async () => {
    try {
      await triggerSync({ full_sync: true }).unwrap()
    } catch (error) {
      console.error('Full sync failed:', error)
    }
  }

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <PlayCircleOutlined />
          <Title level={4} style={{ margin: 0 }}>Quick Actions</Title>
        </div>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={5}>Database Operations</Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button 
              icon={<SyncOutlined spin={syncLoading} />}
              onClick={handleSync}
              loading={syncLoading}
              block
            >
              Quick Sync
            </Button>
            <Button 
              icon={<DatabaseOutlined />}
              onClick={handleFullSync}
              loading={syncLoading}
              block
            >
              Full Database Sync
            </Button>
          </Space>
        </div>

        <Divider />

        <div>
          <Title level={5}>Navigation</Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button 
              icon={<DatabaseOutlined />}
              onClick={() => navigate('/entities')}
              block
            >
              Manage Entities
            </Button>
            <Button 
              icon={<PlayCircleOutlined />}
              onClick={() => navigate('/queues')}
              block
            >
              Queue Manager
            </Button>
            <Button 
              icon={<BarChartOutlined />}
              onClick={() => navigate('/analytics')}
              block
            >
              View Analytics
            </Button>
            <Button 
              icon={<SettingOutlined />}
              onClick={() => navigate('/system')}
              block
            >
              System Status
            </Button>
          </Space>
        </div>

        <Divider />

        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Quick actions to help you manage your Wikipedia extraction pipeline efficiently.
          </Text>
        </div>
      </Space>
    </Card>
  )
}