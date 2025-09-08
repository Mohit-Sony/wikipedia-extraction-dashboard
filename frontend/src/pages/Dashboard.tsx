// src/pages/Dashboard.tsx
import React from 'react'
import { Row, Col, Card, Statistic,  Typography, Spin, Alert, Button, Space } from 'antd'
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useGetDashboardStatsQuery, useTriggerSyncMutation } from '../store/api'
import { RecentActivity } from '../components/dashboard/RecentActivity'
import { QueueOverview } from '../components/dashboard/QueueOverview'
import { TypeDistribution } from '../components/dashboard/TypeDistribution'
import { ExtractionTrends } from '../components/dashboard/ExtractionTrends'
import { QuickActions } from '../components/dashboard/QuickActions'

const { Title, Paragraph } = Typography

export const Dashboard: React.FC = () => {
  const { 
    data: dashboardStats, 
    isLoading, 
    error, 
    refetch 
  } = useGetDashboardStatsQuery()
  
  const [triggerSync, { isLoading: syncLoading }] = useTriggerSyncMutation()

  const handleRefresh = () => {
    refetch()
  }

  const handleSync = async () => {
    try {
      await triggerSync({ full_sync: false }).unwrap()
    } catch (error) {
      console.error('Sync failed:', error)
    }
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert
        message="Error Loading Dashboard"
        description="Failed to load dashboard statistics. Please try refreshing the page."
        type="error"
        showIcon
        action={
          <Button size="small" onClick={handleRefresh}>
            Retry
          </Button>
        }
      />
    )
  }

  return (
    <div>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              Dashboard Overview
            </Title>
            <Paragraph type="secondary">
              Monitor your Wikipedia extraction pipeline performance and queue status
            </Paragraph>
          </Col>
          <Col>
            <Space>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={handleRefresh}
                type="default"
              >
                Refresh
              </Button>
              <Button 
                icon={<SyncOutlined spin={syncLoading} />} 
                onClick={handleSync}
                loading={syncLoading}
                type="primary"
              >
                Sync Database
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Key Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Entities"
              value={dashboardStats?.total_entities || 0}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Processed"
              value={dashboardStats?.total_processed || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Pending"
              value={dashboardStats?.total_pending || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Failed"
              value={dashboardStats?.total_failed || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content Sections */}
      <Row gutter={[16, 16]}>
        {/* Queue Overview */}
        <Col xs={24} lg={12}>
          <QueueOverview queueStats={dashboardStats?.queue_stats || []} />
        </Col>

        {/* Type Distribution */}
        <Col xs={24} lg={12}>
          <TypeDistribution typeStats={dashboardStats?.type_stats || []} />
        </Col>

        {/* Extraction Trends */}
        <Col xs={24}>
          <ExtractionTrends />
        </Col>

        {/* Recent Activity */}
        <Col xs={24} lg={14}>
          <RecentActivity recentActivity={dashboardStats?.recent_activity || []} />
        </Col>

        {/* Quick Actions */}
        <Col xs={24} lg={10}>
          <QuickActions />
        </Col>
      </Row>
    </div>
  )
}