// src/components/extraction/ExtractionMonitor.tsx
import React, { useState } from 'react'
import {
  Card,
  Typography,
  Tag,
  Space,
  Timeline,
  Descriptions,
  Alert,
  Button,
  Modal,
  List,
  Spin
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DatabaseOutlined,
  LinkOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  EyeOutlined
} from '@ant-design/icons'
import {
  useGetExtractionStatusQuery,
  useGetSessionLogsQuery
} from '../../store/api'
import { ExtractionStatus } from '../../types'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import duration from 'dayjs/plugin/duration'

dayjs.extend(relativeTime)
dayjs.extend(duration)

const { Title, Text } = Typography

export const ExtractionMonitor: React.FC = () => {
  const [logsModalOpen, setLogsModalOpen] = useState(false)
  
  const {
    data: statusData,
    isLoading: statusLoading,
    refetch: refetchStatus
  } = useGetExtractionStatusQuery(undefined, {
    pollingInterval: 2000, // Poll every 2 seconds for real-time updates
  })

  const {
    data: logsData,
    isLoading: logsLoading
  } = useGetSessionLogsQuery(
    { session_id: statusData?.session_id || 0 },
    { skip: !statusData?.failed_entities }
  )

  const getStatusColor = (status: ExtractionStatus) => {
    switch (status) {
      case ExtractionStatus.RUNNING:
        return 'processing'
      case ExtractionStatus.COMPLETED:
        return 'success'
      case ExtractionStatus.PAUSED:
        return 'warning'
      case ExtractionStatus.CANCELLED:
        return 'default'
      case ExtractionStatus.ERROR:
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status: ExtractionStatus) => {
    switch (status) {
      case ExtractionStatus.RUNNING:
        return <PlayCircleOutlined />
      case ExtractionStatus.COMPLETED:
        return <CheckCircleOutlined />
      case ExtractionStatus.PAUSED:
        return <PauseCircleOutlined />
      case ExtractionStatus.CANCELLED:
        return <StopOutlined />
      case ExtractionStatus.ERROR:
        return <ExclamationCircleOutlined />
      default:
        return <InfoCircleOutlined />
    }
  }

  // const calculateProgress = () => {
  //   if (!statusData?.progress) return 0
  //   const { entities_processed, queue_size } = statusData.progress
  //   const total = entities_processed + queue_size
  //   return total > 0 ? Math.round((entities_processed / total) * 100) : 0
  // }

  // const calculateETA = () => {
  //   const progress = statusData?.progress
  //   if (!progress || progress.extraction_rate <= 0 || progress.queue_size <= 0) {
  //     return null
  //   }
    
  //   const remainingSeconds = progress.queue_size / progress.extraction_rate
  //   return dayjs.duration(remainingSeconds, 'seconds').humanize()
  // }

  // const formatExtractionRate = () => {
  //   const rate = statusData?.progress?.extraction_rate || 0
  //   return rate > 0 ? `${rate.toFixed(2)} entities/min` : 'Calculating...'
  // }

  if (statusLoading && !statusData) {
    return (
      <Card title="Extraction Monitor" style={{ height: 600 }}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  const status = statusData?.status || ExtractionStatus.IDLE
  const session = statusData
  // const progress = statusData?.progress

  return (
    <>
      <Card 
        title={
          <Space>
            <DatabaseOutlined />
            <Title level={4} style={{ margin: 0 }}>Extraction Monitor</Title>
            <Button 
              size="small" 
              icon={<EyeOutlined />}
              onClick={() => setLogsModalOpen(true)}
              disabled={!session}
            >
              View Logs
            </Button>
          </Space>
        }
        style={{ height: 600 }}
        extra={
          <Space>
            <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
              {status.toUpperCase()}
            </Tag>
            <Button size="small" onClick={() => refetchStatus()}>
              Refresh
            </Button>
          </Space>
        }
      >
        {status === ExtractionStatus.IDLE ? (
          <Alert
            message="No Active Extraction"
            description="Start an extraction to monitor progress here"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
        ) : (
          <>
            {/* Progress Section */}
            {/* {progress && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>Progress Overview</Title>
                <Progress
                  percent={calculateProgress()}
                  status={status === ExtractionStatus.ERROR ? 'exception' : 'active'}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                  style={{ marginBottom: 16 }}
                />
                
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="Current Entity"
                      value={progress.current_entity || 'N/A'}
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="Processed"
                      value={progress.entities_processed}
                      suffix={`/ ${progress.entities_processed + progress.queue_size}`}
                      valueStyle={{ fontSize: 16, color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="Queue Size"
                      value={progress.queue_size}
                      valueStyle={{ fontSize: 16, color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="Rate"
                      value={formatExtractionRate()}
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Col>
                </Row>

                {calculateETA() && (
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">
                      <ClockCircleOutlined /> Estimated time remaining: {calculateETA()}
                    </Text>
                  </div>
                )}
              </div>
            )} */}

{/* Session Information */}
{session && (
  <div style={{ marginBottom: 24 }}>
    <Title level={5}>Session Information</Title>
    <Descriptions column={2} size="small" bordered>
      <Descriptions.Item label="Session ID">
        {session.session_id ?? '—'}
      </Descriptions.Item>
      <Descriptions.Item label="Status">
        {session.status}
      </Descriptions.Item>
      <Descriptions.Item label="Started">
        {session.start_time
          ? dayjs(session.start_time).format('YYYY-MM-DD HH:mm:ss')
          : 'Not started'}
      </Descriptions.Item>
      <Descriptions.Item label="ETA">
        {session.estimated_completion
          ? dayjs(session.estimated_completion).format('YYYY-MM-DD HH:mm:ss')
          : '—'}
      </Descriptions.Item>
      <Descriptions.Item label="Duration">
        {session.start_time && session.estimated_completion
          ? `${dayjs(session.estimated_completion).diff(
              dayjs(session.start_time),
              'minute'
            )} minutes`
          : '—'}
      </Descriptions.Item>
      <Descriptions.Item label="Current Entity QID">
        {session.current_entity ?? '—'}
      </Descriptions.Item>
      <Descriptions.Item label="Progress %">
        {session.progress_percentage?.toFixed(2) ?? 0}%
      </Descriptions.Item>
      <Descriptions.Item label="Processed">
        {session.processed_entities ?? 0} / {session.total_entities ?? 0}
      </Descriptions.Item>
      <Descriptions.Item label="Failed">
        {session.failed_entities ?? 0}
      </Descriptions.Item>
      <Descriptions.Item label="Skipped">
        {session.skipped_entities ?? 0}
      </Descriptions.Item>
      <Descriptions.Item label="Discovered">
        {session.discovered_entities ?? 0}
      </Descriptions.Item>
    </Descriptions>
  </div>
)}
            {/* Deduplication Statistics */}
            {/* {dedupStats && (
              <div style={{ marginBottom: 24 }}>
                <Title level={5}>Smart Deduplication</Title>
                <Row gutter={16}>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Total Discovered"
                        value={dedupStats.total_discovered}
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Duplicates Filtered"
                        value={dedupStats.total_duplicates}
                        valueStyle={{ color: '#faad14' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <Statistic
                        title="Efficiency Rate"
                        value={Math.round(dedupStats.deduplication_rate * 100)}
                        suffix="%"
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                </Row>

                <div style={{ marginTop: 16 }}>
                  <Text strong>Duplicates by Status:</Text>
                  <div style={{ marginTop: 8 }}>
                    <Space wrap>
                      <Tag color="green">Completed: {dedupStats.duplicates_by_status.completed}</Tag>
                      <Tag color="red">Rejected: {dedupStats.duplicates_by_status.rejected}</Tag>
                      <Tag color="blue">In Queue: {dedupStats.duplicates_by_status.in_queue}</Tag>
                      <Tag color="orange">Processing: {dedupStats.duplicates_by_status.processing}</Tag>
                    </Space>
                  </div>
                </div>
              </div>
            )} */}

{/* Recent Activity Timeline */}
{session?.status === ExtractionStatus.RUNNING && (
  <div>
    <Title level={5}>
      <Space>
        <LinkOutlined />
        Discovery Activity
      </Space>
    </Title>

    <Timeline
      items={[
        {
          color: 'blue',
          children: (
            <div>
              <Text strong>Currently Processing</Text>
              <br />
              <Text type="secondary">
                QID: {session.current_entity ?? '—'}
              </Text>
              <br />
              <Text type="secondary">
                Title: {session.current_entity ?? '—'}
              </Text>
            </div>
          ),
        },
        {
          color: 'green',
          children: (
            <div>
              <Text>Entities Discovered</Text>
              <br />
              <Text type="secondary">
                {session.discovered_entities ?? 0} total found
              </Text>
            </div>
          ),
        },
        {
          color: 'orange',
          children: (
            <div>
              <Text>Queue Status</Text>
              <br />
              <Text type="secondary">
                {session.total_entities && session.processed_entities !== null
                  ? `${session.total_entities - session.processed_entities} entities remaining`
                  : '—'}
              </Text>
            </div>
          ),
        },
      ]}
    />
  </div>
)}
          </>
        )}
      </Card>

      {/* Session Logs Modal */}
      <Modal
        title={`Session Logs - ${session?.session_id || 'Current Session'}`}
        open={logsModalOpen}
        onCancel={() => setLogsModalOpen(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setLogsModalOpen(false)}>
            Close
          </Button>
        ]}
      >
        {logsLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : (
          <List
            dataSource={logsData?.logs || []}
            renderItem={(log) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{log.title}</Text>
                      <Tag color={log.status === 'completed' ? 'green' : log.status === 'failed' ? 'red' : 'blue'}>
                        {log.status}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {dayjs(log.timestamp).format('HH:mm:ss')}
                      </Text>
                    </Space>
                  }
                  description={
                    <div>
                      <Text>Action: {log.action}</Text>
                      {log.processing_time && (
                        <>
                          <br />
                          <Text type="secondary">Processing time: {log.processing_time}s</Text>
                        </>
                      )}
                      {log.error_message && (
                        <>
                          <br />
                          <Text type="danger">Error: {log.error_message}</Text>
                        </>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>
    </>
  )
}