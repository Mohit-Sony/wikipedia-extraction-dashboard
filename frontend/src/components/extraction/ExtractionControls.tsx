// src/components/extraction/ExtractionControls.tsx
import React, { useState } from 'react'
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
  message
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  SettingOutlined,
  RocketOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import {
  useGetExtractionStatusQuery,
  useGetExtractionConfigQuery,
  useConfigureExtractionMutation,
  useStartExtractionMutation,
  usePauseExtractionMutation,
  useResumeExtractionMutation,
  useCancelExtractionMutation,
  useGetQueueEntitiesQuery
} from '../../store/api'
import { ExtractionStatus, QueueType, ExtractionConfig } from '../../types'

const { Title, Text } = Typography
const { Option } = Select

export const ExtractionControls: React.FC = () => {
  const [form] = Form.useForm()
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [startModalOpen, setStartModalOpen] = useState(false)
  const [selectedEntities, setSelectedEntities] = useState<string[]>([])
  const [sessionName, setSessionName] = useState('')

  const { data: statusData } = useGetExtractionStatusQuery()
  const { data: configData } = useGetExtractionConfigQuery()
  const { data: activeQueueData } = useGetQueueEntitiesQuery({ 
    queue_type: QueueType.ACTIVE,
    limit: 100 
  })

  const [configureExtraction, { isLoading: configuring }] = useConfigureExtractionMutation()
  const [startExtraction, { isLoading: starting }] = useStartExtractionMutation()
  const [pauseExtraction, { isLoading: pausing }] = usePauseExtractionMutation()
  const [resumeExtraction, { isLoading: resuming }] = useResumeExtractionMutation()
  const [cancelExtraction, { isLoading: cancelling }] = useCancelExtractionMutation()

  const status = statusData?.status || ExtractionStatus.IDLE
  const session = statusData?.current_session

  const canStart = status === ExtractionStatus.IDLE && selectedEntities.length > 0
  const canPause = status === ExtractionStatus.RUNNING
  const canResume = status === ExtractionStatus.PAUSED
  const canCancel = [ExtractionStatus.RUNNING, ExtractionStatus.PAUSED].includes(status)

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

    try {
      const result = await startExtraction({
        entities: selectedEntities,
        session_name: sessionName,
        config: configData
      }).unwrap()
      
      message.success(`Extraction started - Session ID: ${result.session_id}`)
      setStartModalOpen(false)
      setSelectedEntities([])
      setSessionName('')
    } catch (error) {
      message.error('Failed to start extraction')
    }
  }

  const handlePause = async () => {
    try {
      await pauseExtraction().unwrap()
      message.success('Extraction paused')
    } catch (error) {
      message.error('Failed to pause extraction')
    }
  }

  const handleResume = async () => {
    try {
      await resumeExtraction().unwrap()
      message.success('Extraction resumed')
    } catch (error) {
      message.error('Failed to resume extraction')
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
        } catch (error) {
          message.error('Failed to cancel extraction')
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
            >
              Configure
            </Button>
          </Space>
        }
      >
        {/* Current Session Info */}
        {session && (
          <Alert
            message={`Active Session: ${session.session_name}`}
            description={`Started: ${new Date(session.start_time).toLocaleString()} | 
                         Extracted: ${session.total_extracted} | 
                         Errors: ${session.total_errors}`}
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
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                {activeQueueData?.total || 0}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Active Queue</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                {session?.total_extracted || 0}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Extracted</div>
            </div>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                {session?.total_errors || 0}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>Errors</div>
            </div>
          </Col>
        </Row>

        {/* Current Config Display */}
        {configData && (
          <>
            <Divider />
            <div>
              <Text strong>Current Configuration:</Text>
              <div style={{ marginTop: 8 }}>
                <Row gutter={[16, 8]}>
                  <Col span={12}>
                    <Text type="secondary">Max Depth: {configData.max_depth}</Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary">Batch Size: {configData.batch_size}</Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary">Workers: {configData.max_workers}</Text>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary">
                      Dedup: {configData.enable_deduplication ? 'Enabled' : 'Disabled'}
                    </Text>
                  </Col>
                </Row>
              </div>
            </div>
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
          initialValues={configData}
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
                label="Auto Save Interval"
                name="auto_save_interval"
                rules={[{ required: true, type: 'number', min: 1, max: 100 }]}
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Retry Attempts"
                name="retry_attempts"
                rules={[{ required: true, type: 'number', min: 1, max: 10 }]}
              >
                <InputNumber min={1} max={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Retry Delay (seconds)"
            name="retry_delay"
            rules={[{ required: true, type: 'number', min: 0.5, max: 30 }]}
          >
            <InputNumber min={0.5} max={30} step={0.5} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="Enable Smart Deduplication"
            name="enable_deduplication"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Alert
            message="Configuration Tips"
            description={
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>Higher batch size = faster processing but more memory usage</li>
                <li>More workers = parallel processing but higher API load</li>
                <li>Smart deduplication prevents processing already-known entities</li>
                <li>Increase retry delay if you encounter rate limiting</li>
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

          <Form.Item label="Select Entities to Extract" required>
            <Select
              mode="multiple"
              placeholder="Select entities from active queue"
              value={selectedEntities}
              onChange={setSelectedEntities}
              style={{ width: '100%' }}
              showSearch
              filterOption={(input, option) =>
                option?.children?.toString().toLowerCase().includes(input.toLowerCase()) || false
              }
            >
              {activeQueueData?.entries.map((entry) => (
                <Option key={entry.qid} value={entry.qid}>
                  {entry.entity.title} ({entry.qid})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Alert
            message={`${selectedEntities.length} entities selected for extraction`}
            type={selectedEntities.length > 0 ? 'success' : 'warning'}
            showIcon
          />
        </Form>
      </Modal>
    </>
  )
}