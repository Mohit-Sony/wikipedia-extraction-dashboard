// src/pages/SystemStatus.tsx - CORRECTED VERSION
import React from 'react'
import { Row, Col, Card, Statistic, Alert, Button, Typography, Space, Tag, Progress, List, Descriptions } from 'antd'
import {
  DatabaseOutlined,
  WifiOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
  MonitorOutlined,
  ApiOutlined,
  HddOutlined,
  WarningOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { 
  useHealthCheckQuery, 
  useValidateSystemQuery,
  useTriggerSyncMutation 
} from '../store/api'
import { useSelector } from 'react-redux'
import { 
  selectWebSocketConnected, 
  selectWebSocketConnecting,
  selectReconnectAttempts 
} from '../store/slices/webSocketSlice'
import dayjs from 'dayjs'

const { Title, Text } = Typography

export const SystemStatus: React.FC = () => {
  const { data: health, isLoading: healthLoading, refetch: refetchHealth, error: healthError } = useHealthCheckQuery()
  const { data: validation, isLoading: validationLoading, refetch: refetchValidation } = useValidateSystemQuery()
  const [triggerSync, { isLoading: syncLoading }] = useTriggerSyncMutation()
  
  const wsConnected = useSelector(selectWebSocketConnected)
  const wsConnecting = useSelector(selectWebSocketConnecting)
  const reconnectAttempts = useSelector(selectReconnectAttempts)

  const handleRefreshAll = () => {
    refetchHealth()
    refetchValidation()
  }

  const handleSync = async (fullSync = false) => {
    try {
      await triggerSync({ full_sync: fullSync }).unwrap()
      // Refresh data after sync
      setTimeout(() => {
        refetchHealth()
        refetchValidation()
      }, 1000)
    } catch (error) {
      console.error('Sync failed:', error)
    }
  }

  const getStatusIcon = (status: boolean | undefined) => {
    return status ? (
      <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
    ) : (
      <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
    )
  }

  const getStatusTag = (status: string | boolean | undefined, loading = false) => {
    if (loading) {
      return <Tag color="processing">Checking...</Tag>
    }
    
    if (typeof status === 'boolean') {
      return <Tag color={status ? 'success' : 'error'}>{status ? 'Connected' : 'Disconnected'}</Tag>
    }
    
    const colors = {
      healthy: 'success',
      operational: 'success',
      warning: 'warning',
      error: 'error',
      unhealthy: 'error',
      connected: 'success',
      disconnected: 'error',
      connecting: 'processing',
      accessible: 'success',
      inaccessible: 'error'
    }
    
    const statusStr = String(status || 'unknown').toLowerCase()
    return <Tag color={colors[statusStr as keyof typeof colors] || 'default'}>{statusStr}</Tag>
  }

  const getWebSocketStatus = () => {
    if (wsConnecting) return { status: 'connecting', text: 'Connecting...', color: '#faad14' }
    if (wsConnected) return { status: 'connected', text: 'Connected', color: '#52c41a' }
    return { status: 'disconnected', text: 'Disconnected', color: '#ff4d4f' }
  }

  const wsStatus = getWebSocketStatus()

  // IMPROVED: Better error handling and status determination
  const getComponentStatus = (component: string) => {
    // If health check failed completely
    if (healthError) {
      return {
        status: false,
        description: 'Connection Failed',
        details: `Cannot connect to API server: ${healthError}`
      }
    }

    // If health data is loading
    if (healthLoading) {
      return {
        status: undefined,
        description: 'Checking...',
        details: 'Performing health check...'
      }
    }

    // If no health data available
    if (!health) {
      return {
        status: false,
        description: 'Unknown',
        details: 'Health data unavailable'
      }
    }

    // Component-specific status
    switch (component) {
      case 'api':
        return {
          status: health.system_health === 'operational',
          description: health.system_health || 'Unknown',
          details: health.system_health === 'operational' ? 'All endpoints responding' : `Status: ${health.status}`
        }
      
      case 'database':
        return {
          status: health.database?.connection_status == "connected",
          description: health.database?.connection_status == "connected" ? 'Connected' : 'Disconnected',
          details: `${health.database?.total_entities || 0} entities in database`
        }
      
      case 'filesystem':
        return {
          status: health.file_system?.status == "accessible",
          description: health.file_system?.status == "accessible" ? 'Accessible' : 'Error',
          details: `${health.file_system?.total_files || 0} files, ${health.file_system?.total_size_mb || 0}MB`
        }
      
      case 'websocket':
        return {
          status: wsConnected,
          description: wsStatus.text,
          details: reconnectAttempts > 0 ? `${reconnectAttempts} reconnect attempts` : 'Real-time updates active'
        }
      
      default:
        return {
          status: false,
          description: 'Unknown',
          details: 'Component status unavailable'
        }
    }
  }

  const apiStatus = getComponentStatus('api')
  const dbStatus = getComponentStatus('database')
  const fsStatus = getComponentStatus('filesystem')
  const wsComponentStatus = getComponentStatus('websocket')

  const systemComponents = [
    {
      title: 'API Server',
      status: apiStatus.status,
      description: apiStatus.description,
      icon: <ApiOutlined />,
      details: apiStatus.details
    },
    {
      title: 'Database',
      status: dbStatus.status,
      description: dbStatus.description,
      icon: <DatabaseOutlined />,
      details: dbStatus.details
    },
    {
      title: 'File System',
      status: fsStatus.status,
      description: fsStatus.description,
      icon: <HddOutlined />,
      details: fsStatus.details
    },
    {
      title: 'WebSocket',
      status: wsComponentStatus.status,
      description: wsComponentStatus.description,
      icon: <WifiOutlined />,
      details: wsComponentStatus.details
    }
  ]

  // Overall system health
  const overallHealthy = !healthError && health?.status === 'healthy' && wsConnected

  return (
    <div>
      {/* Page Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            System Status
          </Title>
          <Text type="secondary">
            Monitor system health, performance metrics, and data integrity
          </Text>
        </Col>
        <Col>
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleRefreshAll}
              loading={healthLoading || validationLoading}
            >
              Refresh Status
            </Button>
            <Button 
              icon={<SyncOutlined spin={syncLoading} />}
              onClick={() => handleSync(false)}
              loading={syncLoading}
              type="primary"
            >
              Quick Sync
            </Button>
            <Button 
              icon={<SyncOutlined spin={syncLoading} />}
              onClick={() => handleSync(true)}
              loading={syncLoading}
              danger
            >
              Full Sync
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Overall System Health Alert */}
      <Alert
        message={`System Status: ${overallHealthy ? 'Operational' : 'Issues Detected'}`}
        description={
          overallHealthy
            ? 'All systems are functioning normally'
            : healthError
            ? 'Cannot connect to backend server'
            : 'Some components require attention'
        }
        type={overallHealthy ? 'success' : 'warning'}
        showIcon
        style={{ marginBottom: 24 }}
        action={
          !overallHealthy && (
            <Button size="small" onClick={handleRefreshAll}>
              Recheck
            </Button>
          )
        }
      />

      {/* System Components Status */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {systemComponents.map((component, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                <div style={{ marginRight: 12, fontSize: 20, color: '#1890ff' }}>
                  {component.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <Text strong>{component.title}</Text>
                </div>
                {getStatusIcon(component.status)}
              </div>
              <div style={{ marginBottom: 8 }}>
                {getStatusTag(component.description, healthLoading)}
              </div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {component.details}
              </Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        {/* Detailed System Statistics */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <MonitorOutlined />
                <span>System Statistics</span>
              </Space>
            } 
            loading={healthLoading}
            style={{ height: 400 }}
          >
            {health ? (
              <div>
                <Descriptions column={1} size="small" bordered>
                  <Descriptions.Item label="Database Entities">
                    <Statistic
                      value={health.database?.total_entities || 0}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="WebSocket Connections">
                    <Statistic
                      value={health.websocket?.active_connections || 0}
                      valueStyle={{ fontSize: 16, color: wsConnected ? '#52c41a' : '#ff4d4f' }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="File System Entities">
                    <Statistic
                      value={health.file_system?.total_files || 0}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="Storage Size">
                    <Statistic
                      value={health.file_system?.total_size_mb || 0}
                      suffix="MB"
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="Extraction Status">
                    <Tag color={health.extraction_service?.is_running ? 'processing' : 'default'}>
                      {health.extraction_service?.status || 'idle'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="System Version">
                    <Text code>{health.system?.version || '2.0.0'}</Text>
                  </Descriptions.Item>
                </Descriptions>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Text type="secondary">System statistics unavailable</Text>
              </div>
            )}
          </Card>
        </Col>

        {/* Data Validation */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <WarningOutlined />
                <span>Data Validation</span>
              </Space>
            } 
            loading={validationLoading}
            // style={{ height: 400 }}
          >
            {validation ? (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <Progress
                    percent={
                      validation.validation?.total_entities > 0
                        ? Math.round(
                            ((validation.validation.total_entities - validation.validation.missing_files) /
                              validation.validation.total_entities) *
                            100
                          )
                        : 100
                    }
                    status={validation.validation?.missing_files > 0 ? 'exception' : 'success'}
                  />
                </div>

                <Descriptions column={1} size="small" bordered>
                  <Descriptions.Item label="Total Entities">
                    {validation.validation?.total_entities || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label="Valid Files">
                    {validation.validation?.valid_files || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label="Missing Files">
                    <Text type={validation.validation?.missing_files > 0 ? 'danger' : 'secondary'}>
                      {validation.validation?.missing_files || 0}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Invalid Paths">
                    <Text type={validation.validation?.invalid_paths > 0 ? 'danger' : 'secondary'}>
                      {validation.validation?.invalid_paths || 0}
                    </Text>
                  </Descriptions.Item>
                </Descriptions>

                {validation.validation?.errors && validation.validation.errors.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <Text strong style={{ color: '#ff4d4f' }}>Recent Errors:</Text>
                    <List
                      size="small"
                      dataSource={validation.validation.errors.slice(0, 2)}
                      renderItem={(error: any) => (
                        <List.Item>
                          <Text type="danger" style={{ fontSize: 12 }}>
                            {error.qid}: {error.error}
                          </Text>
                        </List.Item>
                      )}
                      footer={
                        validation.validation.errors.length > 5 && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            ... and {validation.validation.errors.length - 5} more errors
                          </Text>
                        )
                      }
                    />
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Text type="secondary">No validation data available</Text>
              </div>
            )}
          </Card>
        </Col>

        {/* System Information */}
        <Col xs={24}>
          <Card 
            title={
              <Space>
                <ClockCircleOutlined />
                <span>System Information</span>
              </Space>
            }
          >
            <Row gutter={16}>
              <Col xs={24} sm={12} lg={8}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>Last Health Check:</Text>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary">
                      {health?.timestamp ? dayjs(health.timestamp).format('YYYY-MM-DD HH:mm:ss') : 'Never'}
                    </Text>
                  </div>
                </div>
              </Col>
              <Col xs={24} sm={12} lg={8}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>WebSocket Status:</Text>
                  <div style={{ marginTop: 4 }}>
                    <Tag color={wsStatus.color}>{wsStatus.text}</Tag>
                    {reconnectAttempts > 0 && (
                      <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                        ({reconnectAttempts} reconnect attempts)
                      </Text>
                    )}
                  </div>
                </div>
              </Col>
              <Col xs={24} sm={12} lg={8}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong>Sync Status:</Text>
                  <div style={{ marginTop: 4 }}>
                    <Tag color={syncLoading ? 'processing' : 'default'}>
                      {syncLoading ? 'Syncing...' : 'Ready'}
                    </Tag>
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}