// src/pages/SystemStatus.tsx
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
  InfoCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { 
  useHealthCheckQuery, 
  useGetSystemStatsQuery, 
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
  const { data: systemStats, isLoading: statsLoading, refetch: refetchStats } = useGetSystemStatsQuery()
  const { data: validation, isLoading: validationLoading, refetch: refetchValidation } = useValidateSystemQuery()
  const [triggerSync, { isLoading: syncLoading }] = useTriggerSyncMutation()
  
  const wsConnected = useSelector(selectWebSocketConnected)
  const wsConnecting = useSelector(selectWebSocketConnecting)
  const reconnectAttempts = useSelector(selectReconnectAttempts)

  const handleRefreshAll = () => {
    refetchHealth()
    refetchStats()
    refetchValidation()
  }

  const handleSync = async (fullSync = false) => {
    try {
      await triggerSync({ full_sync: fullSync }).unwrap()
    } catch (error) {
      console.error('Sync failed:', error)
    }
  }

  const getStatusIcon = (status: boolean) => {
    return status ? (
      <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
    ) : (
      <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
    )
  }

  const getStatusTag = (status: string, loading = false) => {
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
    
    if (loading) {
      return <Tag color="processing">Checking...</Tag>
    }
    
    return <Tag color={colors[status as keyof typeof colors] || 'default'}>{status}</Tag>
  }

  const getWebSocketStatus = () => {
    if (wsConnecting) return { status: 'connecting', text: 'Connecting...', color: '#faad14' }
    if (wsConnected) return { status: 'connected', text: 'Connected', color: '#52c41a' }
    return { status: 'disconnected', text: 'Disconnected', color: '#ff4d4f' }
  }

  const wsStatus = getWebSocketStatus()

  const systemComponents = [
    {
      title: 'API Server',
      status: health?.status === 'healthy',
      description: health?.status || 'Unknown',
      icon: <ApiOutlined />,
      details: healthError ? 'Connection failed' : 'All endpoints responding'
    },
    {
      title: 'Database',
      status: health?.database?.connected,
      description: health?.database?.connected ? 'Connected' : 'Disconnected',
      icon: <DatabaseOutlined />,
      details: `${health?.database?.entity_count || 0} entities in database`
    },
    {
      title: 'File System',
      status: health?.file_system?.accessible,
      description: health?.file_system?.accessible ? 'Accessible' : 'Error',
      icon: <HddOutlined />,
      details: `${health?.file_system?.total_entities || 0} files, ${health?.file_system?.total_size_mb || 0}MB`
    },
    {
      title: 'WebSocket',
      status: wsConnected,
      description: wsStatus.text,
      icon: <WifiOutlined />,
      details: reconnectAttempts > 0 ? `${reconnectAttempts} reconnect attempts` : 'Real-time updates active'
    }
  ]

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
              loading={healthLoading || statsLoading || validationLoading}
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
      {health && (
        <Alert
          message={`System Status: ${health.status === 'healthy' ? 'Operational' : 'Issues Detected'}`}
          description={
            health.status === 'healthy' 
              ? 'All systems are functioning normally'
              : 'Some components require attention'
          }
          type={health.status === 'healthy' ? 'success' : 'warning'}
          showIcon
          style={{ marginBottom: 24 }}
          action={
            health.status !== 'healthy' && (
              <Button size="small" onClick={handleRefreshAll}>
                Recheck
              </Button>
            )
          }
        />
      )}

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
                {getStatusTag(component.description.toLowerCase(), healthLoading)}
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
            loading={statsLoading}
            style={{ height: 400 }}
          >
            {systemStats ? (
              <div>
                <Descriptions column={1} size="small" bordered>
                  <Descriptions.Item label="Database Entities">
                    <Statistic
                      value={systemStats.database?.total_entities || 0}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="WebSocket Connections">
                    <Statistic
                      value={systemStats.websocket?.active_connections || 0}
                      valueStyle={{ fontSize: 16, color: wsConnected ? '#52c41a' : '#ff4d4f' }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="File System Size">
                    <Statistic
                      value={systemStats.file_system?.total_size_mb || 0}
                      suffix="MB"
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Descriptions.Item>
                  <Descriptions.Item label="Total Files">
                    <Statistic
                      value={systemStats.file_system?.total_entities || 0}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Descriptions.Item>
                </Descriptions>

                {systemStats.file_system?.entities_by_type && (
                  <div style={{ marginTop: 20 }}>
                    <Text strong>Entity Distribution:</Text>
                    <div style={{ marginTop: 8 }}>
                      {Object.entries(systemStats.file_system.entities_by_type).map(([type, count]) => (
                        <div key={type} style={{ marginBottom: 8 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <Text style={{ textTransform: 'capitalize' }}>{type}</Text>
                            <Text strong>{count as number}</Text>
                          </div>
                          <Progress 
                            percent={((count as number) / systemStats.file_system.total_entities) * 100} 
                            size="small" 
                            showInfo={false}
                            strokeColor="#1890ff"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Text type="secondary">No system statistics available</Text>
              </div>
            )}
          </Card>
        </Col>

        {/* Data Validation Results */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <DatabaseOutlined />
                <span>Data Validation</span>
              </Space>
            } 
            loading={validationLoading}
            style={{ height: 400 }}
          >
            {validation ? (
              <div>
                {validation.status === 'valid' ? (
                  <Alert
                    message="Validation Passed"
                    description="All database entries have corresponding files"
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                    style={{ marginBottom: 20 }}
                  />
                ) : (
                  <Alert
                    message="Validation Issues Found"
                    description={`${validation.validation?.missing_files || 0} missing files detected`}
                    type="warning"
                    showIcon
                    icon={<WarningOutlined />}
                    style={{ marginBottom: 20 }}
                  />
                )}

                <Row gutter={16} style={{ marginBottom: 20 }}>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Total"
                        value={validation.validation?.total_entities || 0}
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Valid"
                        value={validation.validation?.valid_files || 0}
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Missing"
                        value={validation.validation?.missing_files || 0}
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {validation.validation?.errors && validation.validation.errors.length > 0 && (
                  <div>
                    <Text strong style={{ marginBottom: 8, display: 'block' }}>
                      Validation Errors:
                    </Text>
                    <List
                      size="small"
                      dataSource={validation.validation.errors.slice(0, 5)}
                      renderItem={(error: any) => (
                        <List.Item>
                          <Text code style={{ fontSize: 12 }}>{error.qid}</Text>
                          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                            {error.error}
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

        {/* Recent System Events */}
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
                      {health ? dayjs().format('YYYY-MM-DD HH:mm:ss') : 'Never'}
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
                      {syncLoading ? 'In Progress' : 'Ready'}
                    </Tag>
                  </div>
                </div>
              </Col>
            </Row>

            <div style={{ marginTop: 24, padding: 16, backgroundColor: '#fafafa', borderRadius: 6 }}>
              <Space direction="vertical" size="small">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                  <Text strong>System Health Tips:</Text>
                </div>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>
                    <Text type="secondary">
                      Run Quick Sync regularly to keep database in sync with files
                    </Text>
                  </li>
                  <li>
                    <Text type="secondary">
                      Monitor WebSocket connection for real-time updates
                    </Text>
                  </li>
                  <li>
                    <Text type="secondary">
                      Check validation results to ensure data integrity
                    </Text>
                  </li>
                  <li>
                    <Text type="secondary">
                      Use Full Sync if you notice inconsistencies
                    </Text>
                  </li>
                </ul>
              </Space>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}