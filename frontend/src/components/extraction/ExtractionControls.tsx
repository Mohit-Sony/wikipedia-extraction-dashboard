// src/components/extraction/ExtractionControls.tsx - FIXED VERSION
import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Button, 
  Space, 
  Form, 
  Input, 
  InputNumber, 
  Switch, 
  Divider,
  Typography,
  Row,
  Col,
  Alert,
  Modal,
  Select,
  Tag,
  message,
  Statistic,
  Badge,
  Tooltip
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  SettingOutlined,
  RocketOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined
} from '@ant-design/icons'
import {
  useGetExtractionStatusQuery,
  useGetExtractionConfigQuery,
  useConfigureExtractionMutation,
  useStartExtractionMutation,
  usePauseExtractionMutation,
  useResumeExtractionMutation,
  useCancelExtractionMutation,
  useGetAllQueuesQuery
} from '../../store/api'
import { ExtractionStatus, QueueType } from '../../types'

const { Title, Text } = Typography
const { Option } = Select

interface QueueOption {
  key: QueueType
  label: string
  color: string
  icon: React.ReactNode
  description: string
}

const QUEUE_OPTIONS: QueueOption[] = [
  {
    key: QueueType.ACTIVE,
    label: 'Active Queue',
    color: 'green',
    icon: <PlayCircleOutlined />,
    description: 'Entities ready for immediate extraction'
  },
  {
    key: QueueType.ON_HOLD,
    label: 'On Hold Queue', 
    color: 'orange',
    icon: <ClockCircleOutlined />,
    description: 'Entities temporarily paused'
  },
  {
    key: QueueType.REVIEW,
    label: 'Review Queue',
    color: 'blue', 
    icon: <TeamOutlined />,
    description: 'Newly discovered entities awaiting review'
  }
]

export const ExtractionControls: React.FC = () => {
  const [form] = Form.useForm()
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [startModalOpen, setStartModalOpen] = useState(false)
  const [selectedQueues, setSelectedQueues] = useState<QueueType[]>([QueueType.ACTIVE])
  const [sessionName, setSessionName] = useState('')

  // API Hooks
  const { data: statusData } = useGetExtractionStatusQuery()
  const { data: configData } = useGetExtractionConfigQuery()
  const { data: allQueuesData } = useGetAllQueuesQuery()

  // Mutations
  const [configureExtraction, { isLoading: configuring }] = useConfigureExtractionMutation()
  const [startExtraction, { isLoading: starting }] = useStartExtractionMutation()
  const [pauseExtraction, { isLoading: pausing }] = usePauseExtractionMutation()
  const [resumeExtraction, { isLoading: resuming }] = useResumeExtractionMutation()
  const [cancelExtraction, { isLoading: cancelling }] = useCancelExtractionMutation()

  // Status and session info
  const status = statusData?.status || ExtractionStatus.IDLE
  const session = statusData
  // const progress = statusData?.progress

  // Button states
  const canStart = status === ExtractionStatus.IDLE && selectedQueues.length > 0
  const canPause = status === ExtractionStatus.RUNNING
  const canResume = status === ExtractionStatus.PAUSED
  const canCancel = [ExtractionStatus.RUNNING, ExtractionStatus.PAUSED].includes(status)

  // Auto-generate session name
  useEffect(() => {
    if (!sessionName && startModalOpen) {
      const timestamp = new Date().toLocaleString('en-US', {
        month: 'short',
        day: 'numeric', 
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      })
      setSessionName(`Extraction ${timestamp}`)
    }
  }, [startModalOpen, sessionName])

  // Get total entities count for selected queues
  const getTotalEntitiesForQueues = (): number => {
    if (!allQueuesData) return 0
    
    return selectedQueues.reduce((total, queueType) => {
      const queueData = allQueuesData[queueType]
      return total + (queueData?.count || 0)
    }, 0)
  }

  // Handlers
  const handleConfigSave = async () => {
    try {
      const values = await form.validateFields()
      await configureExtraction(values).unwrap()
      message.success('Configuration saved successfully')
      setConfigModalOpen(false)
    } catch (error) {
      message.error('Failed to save configuration')
    }
  }

  const handleStart = async () => {
    if (!sessionName.trim()) {
      message.error('Please enter a session name')
      return
    }

    if (selectedQueues.length === 0) {
      message.error('Please select at least one queue to process')
      return
    }

    const totalEntities = getTotalEntitiesForQueues()
    if (totalEntities === 0) {
      message.error('Selected queues are empty. Add entities to queues first.')
      return
    }

    try {
      const result = await startExtraction({
        queue_types: selectedQueues,
        session_name: sessionName,
        config: configData
      }).unwrap()
      
      message.success(`Extraction started - Session ID: ${result.session_id}`)
      setStartModalOpen(false)
      setSelectedQueues([QueueType.ACTIVE])
      setSessionName('')
    } catch (error: any) {
      const errorMsg = error?.data?.detail || 'Failed to start extraction'
      message.error(errorMsg)
    }
  }

  const handlePause = async () => {
    try {
      await pauseExtraction().unwrap()
      message.success('Extraction paused')
    } catch (error: any) {
      const errorMsg = error?.data?.detail || 'Failed to pause extraction'
      message.error(errorMsg)
    }
  }

  const handleResume = async () => {
    try {
      await resumeExtraction().unwrap()
      message.success('Extraction resumed')
    } catch (error: any) {
      const errorMsg = error?.data?.detail || 'Failed to resume extraction'
      message.error(errorMsg)
    }
  }

  const handleCancel = () => {
    Modal.confirm({
      title: 'Cancel Extraction',
      content: 'Are you sure you want to cancel the current extraction? This action cannot be undone.',
      okText: 'Yes, Cancel',
      okType: 'danger',
      cancelText: 'No',
      onOk: async () => {
        try {
          await cancelExtraction().unwrap()
          message.success('Extraction cancelled')
        } catch (error: any) {
          const errorMsg = error?.data?.detail || 'Failed to cancel extraction'
          message.error(errorMsg)
        }
      }
    })
  }

  const getStatusDisplay = () => {
    switch (status) {
      case ExtractionStatus.IDLE:
        return <Tag color="default">Ready to Start</Tag>
      case ExtractionStatus.RUNNING:
        return <Tag color="processing" icon={<PlayCircleOutlined />}>Running</Tag>
      case ExtractionStatus.PAUSED:
        return <Tag color="warning" icon={<PauseCircleOutlined />}>Paused</Tag>
      case ExtractionStatus.COMPLETED:
        return <Tag color="success" icon={<CheckCircleOutlined />}>Completed</Tag>
      case ExtractionStatus.ERROR:
        return <Tag color="error" icon={<ExclamationCircleOutlined />}>Error</Tag>
      case ExtractionStatus.CANCELLED:
        return <Tag color="default" icon={<StopOutlined />}>Cancelled</Tag>
      default:
        return <Tag color="default">{status}</Tag>
    }
  }

  const getQueueStats = (queueType: QueueType) => {
    const queueData = allQueuesData?.[queueType]
    return {
      count: queueData?.count || 0,
      recent: queueData?.recent_entries?.length || 0
    }
  }

  return (
    <>
      <Card 
        title={
          <Space>
            <RocketOutlined />
            <Title level={4} style={{ margin: 0 }}>Extraction Controls</Title>
          </Space>
        }
        extra={
          <Space>
            {getStatusDisplay()}
            <Button 
              icon={<SettingOutlined />}
              onClick={() => setConfigModalOpen(true)}
              disabled={status === ExtractionStatus.RUNNING}
            >
              Configure
            </Button>
          </Space>
        }
      >
        {/* Current Session Info */}
        {session && (
          <Alert
            message={`Active Session: ${session.session_id}`}
            // description={`Started: ${new Date(session.start_time).toLocaleString()} | 
            description={`Started: ${
              session.start_time
                ? new Date(session.start_time).toLocaleString()
                : 'Not started'
            } | 
            Total : ${session.total_entities} | 
                         Extracted: ${session.processed_entities} | 
                         Percent:${session.progress_percentage?.toFixed(2) ?? 0}
                         Errors: ${session.failed_entities} | 
                         Skipped: ${session?.skipped_entities || 0}`}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Control Buttons */}
        <Row gutter={16}>
          <Col span={12}>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => setStartModalOpen(true)}
              disabled={!canStart}
              loading={starting}
              block
              size="large"
            >
              Start Extraction
            </Button>
          </Col>
          <Col span={12}>
            <Space style={{ width: '100%' }}>
              <Button
                icon={<PauseCircleOutlined />}
                onClick={handlePause}
                disabled={!canPause}
                loading={pausing}
                style={{ flex: 1 }}
              >
                Pause
              </Button>
              <Button
                icon={<PlayCircleOutlined />}
                onClick={handleResume}
                disabled={!canResume}
                loading={resuming}
                style={{ flex: 1 }}
              >
                Resume
              </Button>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={handleCancel}
                disabled={!canCancel}
                loading={cancelling}
                style={{ flex: 1 }}
              >
                Cancel
              </Button>
            </Space>
          </Col>
        </Row>

        {/* Quick Stats */}
        <Divider />
        <Row gutter={16}>
          {QUEUE_OPTIONS.map((queue) => {
            const stats = getQueueStats(queue.key)
            return (
              <Col span={8} key={queue.key}>
                <Statistic
                  title={
                    <Space>
                      {queue.icon}
                      <Text>{queue.label}</Text>
                    </Space>
                  }
                  value={stats.count}
                  valueStyle={{ color: stats.count > 0 ? '#3f8600' : '#8c8c8c' }}
                  suffix="entities"
                />
              </Col>
            )
          })}
        </Row>

{session?.status === ExtractionStatus.RUNNING && (
  <>
    <Divider />
    <Row gutter={16}>
      <Col span={8}>
        <Statistic
          title="Progress"
          value={session.progress_percentage?.toFixed(2) ?? 0}
          precision={1}
          suffix="%"
        />
      </Col>
      <Col span={8}>
        <Statistic
          title="Processed"
          value={session.processed_entities ?? 0}
          suffix={`/ ${session.total_entities ?? 0}`}
        />
      </Col>
      <Col span={8}>
        <Statistic
          title="Discovered"
          value={session.discovered_entities ?? 0}
        />
      </Col>
    </Row>
  </>
)}
      </Card>

      {/* Configuration Modal */}
      <Modal
        title="Extraction Configuration"
        open={configModalOpen}
        onOk={handleConfigSave}
        onCancel={() => setConfigModalOpen(false)}
        confirmLoading={configuring}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={configData || {
            max_depth: 3,
            batch_size: 10,
            max_workers: 5,
            pause_between_requests: 1.0,
            enable_deduplication: true,
            retry_attempts: 3,
            auto_add_to_review: true
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Max Depth"
                name="max_depth"
                rules={[{ required: true, type: 'number', min: 1, max: 10 }]}
              >
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Batch Size"
                name="batch_size"
                rules={[{ required: true, type: 'number', min: 1, max: 50 }]}
              >
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Max Workers"
                name="max_workers"
                rules={[{ required: true, type: 'number', min: 1, max: 10 }]}
              >
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Pause Between Requests (seconds)"
                name="pause_between_requests"
                rules={[{ required: true, type: 'number', min: 0.1, max: 10 }]}
              >
                <InputNumber min={0.1} max={10} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="Retry Attempts"
                name="retry_attempts"
                rules={[{ required: true, type: 'number', min: 0, max: 10 }]}
              >
                <InputNumber min={0} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Enable Smart Deduplication"
                name="enable_deduplication"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Auto-add to Review Queue"
            name="auto_add_to_review"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Alert
            message="Configuration Tips"
            description={
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>Higher batch size = faster processing, but more memory usage</li>
                <li>More workers = parallel processing, but higher server load</li>
                <li>Smart deduplication prevents processing already-known entities</li>
                <li>Increase pause between requests if you encounter rate limiting</li>
              </ul>
            }
            type="info"
            showIcon
            icon={<InfoCircleOutlined />}
          />
        </Form>
      </Modal>

      {/* Start Extraction Modal */}
      <Modal
        title="Start New Extraction"
        open={startModalOpen}
        onOk={handleStart}
        onCancel={() => setStartModalOpen(false)}
        confirmLoading={starting}
        width={600}
      >
        <Form layout="vertical">
          <Form.Item label="Session Name" required>
            <Input
              value={sessionName}
              onChange={(e) => setSessionName(e.target.value)}
              placeholder="Enter a descriptive name for this extraction session"
            />
          </Form.Item>

          <Form.Item label="Select Queues to Process" required>
            <Select
              mode="multiple"
              placeholder="Select queues to process"
              value={selectedQueues}
              onChange={setSelectedQueues}
              style={{ width: '100%' }}
            >
              {QUEUE_OPTIONS.map((queue) => {
                const stats = getQueueStats(queue.key)
                return (
                  <Option key={queue.key} value={queue.key} disabled={stats.count === 0}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        {queue.icon}
                        <Tag color={queue.color}>{queue.label}</Tag>
                      </Space>
                      <Badge 
                        count={stats.count} 
                        style={{ backgroundColor: stats.count > 0 ? '#52c41a' : '#d9d9d9' }}
                      />
                    </div>
                    <div style={{ marginLeft: 20, marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {queue.description}
                      </Text>
                    </div>
                  </Option>
                )
              })}
            </Select>
          </Form.Item>

          <Alert
            message={`${getTotalEntitiesForQueues()} entities selected for extraction from ${selectedQueues.length} queue(s)`}
            type={getTotalEntitiesForQueues() > 0 ? 'success' : 'warning'}
            showIcon
            style={{ marginBottom: 16 }}
          />

          {selectedQueues.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Title level={5}>Selected Queues:</Title>
              <Space wrap>
                {selectedQueues.map((queueType) => {
                  const queue = QUEUE_OPTIONS.find(q => q.key === queueType)
                  const stats = getQueueStats(queueType)
                  return (
                    <Tooltip key={queueType} title={queue?.description}>
                      <Tag color={queue?.color} icon={queue?.icon}>
                        {queue?.label}: {stats.count} entities
                      </Tag>
                    </Tooltip>
                  )
                })}
              </Space>
            </div>
          )}

          {getTotalEntitiesForQueues() === 0 && (
            <Alert
              message="No entities available"
              description="Please add entities to the selected queues before starting extraction."
              type="warning"
              showIcon
              action={
                <Button size="small" type="link">
                  Add Entities
                </Button>
              }
            />
          )}
        </Form>
      </Modal>
    </>
  )
}