// src/components/extraction/ManualEntityEntry.tsx
import React, { useState } from 'react'
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Select, 
  Space, 
  Typography, 
  Alert, 
  Row, 
  Col,
  Divider,
  Tag,
  message,
  Modal,
  List
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  UserOutlined,
  GlobalOutlined,
  TeamOutlined,
  CalendarOutlined,
  BookOutlined
} from '@ant-design/icons'
import {
  useAddManualEntityMutation,
  useGetSearchSuggestionsQuery
} from '../../store/api'
import { Priority, ManualEntityRequest } from '../../types'
import { useDebounce } from '../../hooks/useDebounce'

const { Title, Text } = Typography
const { Option } = Select
const { TextArea } = Input

export const ManualEntityEntry: React.FC = () => {
  const [form] = Form.useForm()
  const [searchTerm, setSearchTerm] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [resultModalOpen, setResultModalOpen] = useState(false)
  const [lastResult, setLastResult] = useState<any>(null)

  const debouncedSearchTerm = useDebounce(searchTerm, 300)
  
  const { data: suggestions } = useGetSearchSuggestionsQuery(debouncedSearchTerm, {
    skip: debouncedSearchTerm.length < 2
  })

  const [addManualEntity, { isLoading: adding }] = useAddManualEntityMutation()

  const entityTypes = [
    { value: 'human', label: 'Human', icon: <UserOutlined /> },
    { value: 'place', label: 'Place', icon: <GlobalOutlined /> },
    { value: 'organization', label: 'Organization', icon: <TeamOutlined /> },
    { value: 'event', label: 'Event', icon: <CalendarOutlined /> },
    { value: 'concept', label: 'Concept', icon: <BookOutlined /> },
  ]

  const handleSubmit = async (values: any) => {
    try {
      const entityData: ManualEntityRequest = {
        qid: values.qid?.trim() || undefined,
        title: values.title.trim(),
        type: values.type,
        short_desc: values.short_desc?.trim() || undefined,
        priority: values.priority || Priority.MEDIUM,
        notes: values.notes?.trim() || undefined
      }

      const result = await addManualEntity(entityData).unwrap()
      
      setLastResult(result)
      setResultModalOpen(true)
      
      if (result.success) {
        form.resetFields()
        setSearchTerm('')
        
        if (result.was_duplicate) {
          message.warning(`Entity already exists with status: ${result.existing_status}`)
        } else {
          message.success('Entity added successfully to review queue')
        }
      } else {
        message.error(result.message)
      }
    } catch (error) {
      message.error('Failed to add entity')
    }
  }

  const handleTitleChange = (value: string) => {
    setSearchTerm(value)
    setShowSuggestions(value.length >= 2)
    form.setFieldsValue({ title: value })
  }

  const handleSuggestionSelect = (suggestion: any) => {
    form.setFieldsValue({
      title: suggestion.title,
      qid: suggestion.qid,
      type: suggestion.type
    })
    setSearchTerm(suggestion.title)
    setShowSuggestions(false)
  }

  const validateQID = (_: any, value: string) => {
    if (!value) return Promise.resolve()
    
    const qidPattern = /^Q\d+$/
    if (!qidPattern.test(value)) {
      return Promise.reject(new Error('QID must be in format Q123456'))
    }
    return Promise.resolve()
  }

  const getResultIcon = () => {
    if (!lastResult) return <InfoCircleOutlined />
    
    if (lastResult.was_duplicate) {
      return <ExclamationCircleOutlined style={{ color: '#faad14' }} />
    }
    
    return lastResult.success 
      ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
      : <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
  }

  const getResultType = () => {
    if (!lastResult) return 'info'
    
    if (lastResult.was_duplicate) return 'warning'
    return lastResult.success ? 'success' : 'error'
  }

  return (
    <>
      <Card 
        title={
          <Space>
            <PlusOutlined />
            <Title level={4} style={{ margin: 0 }}>Manual Entity Entry</Title>
          </Space>
        }
        style={{ height: 600 }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          {/* Title Input with Suggestions */}
          <Form.Item
            label="Entity Title"
            name="title"
            rules={[
              { required: true, message: 'Please enter entity title' },
              { min: 2, message: 'Title must be at least 2 characters' }
            ]}
          >
            <div style={{ position: 'relative' }}>
              <Input
                placeholder="Enter Wikipedia page title or search..."
                suffix={<SearchOutlined />}
                value={searchTerm}
                onChange={(e) => handleTitleChange(e.target.value)}
                onFocus={() => setShowSuggestions(searchTerm.length >= 2)}
              />
              
              {/* Search Suggestions Dropdown */}
              {showSuggestions && suggestions?.suggestions && suggestions.suggestions.length > 0 && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  backgroundColor: 'white',
                  border: '1px solid #d9d9d9',
                  borderRadius: '6px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                  zIndex: 1000,
                  maxHeight: 200,
                  overflowY: 'auto'
                }}>
                  {suggestions.suggestions.map((suggestion, index) => (
                    <div
                      key={`${suggestion.qid}-${index}`}
                      style={{
                        padding: '8px 12px',
                        cursor: 'pointer',
                        borderBottom: index < suggestions.suggestions.length - 1 ? '1px solid #f0f0f0' : 'none'
                      }}
                      onClick={() => handleSuggestionSelect(suggestion)}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                    >
                      <div style={{ fontWeight: 500 }}>{suggestion.title}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        <Space>
                          <span>{suggestion.qid}</span>
                          <Tag >{suggestion.type}</Tag>
                        </Space>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              {/* QID Input */}
              <Form.Item
                label="QID (Optional)"
                name="qid"
                rules={[{ validator: validateQID }]}
              >
                <Input
                  placeholder="Q123456"
                  style={{ textTransform: 'uppercase' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              {/* Entity Type */}
              <Form.Item
                label="Entity Type"
                name="type"
                rules={[{ required: true, message: 'Please select entity type' }]}
              >
                <Select placeholder="Select entity type">
                  {entityTypes.map(type => (
                    <Option key={type.value} value={type.value}>
                      <Space>
                        {type.icon}
                        {type.label}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* Short Description */}
          <Form.Item
            label="Short Description (Optional)"
            name="short_desc"
          >
            <TextArea
              rows={2}
              placeholder="Brief description of the entity..."
              showCount
              maxLength={200}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              {/* Priority */}
              <Form.Item
                label="Priority"
                name="priority"
                initialValue={Priority.MEDIUM}
              >
                <Select>
                  <Option value={Priority.HIGH}>
                    <Tag color="red">High Priority</Tag>
                  </Option>
                  <Option value={Priority.MEDIUM}>
                    <Tag color="orange">Medium Priority</Tag>
                  </Option>
                  <Option value={Priority.LOW}>
                    <Tag color="green">Low Priority</Tag>
                  </Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <div style={{ paddingTop: 30 }}>
                <Alert
                  message="Entity will be added to review queue for processing"
                  type="info"
                  showIcon
                  style={{ fontSize: 12 }}
                />
              </div>
            </Col>
          </Row>

          {/* Notes */}
          <Form.Item
            label="Notes (Optional)"
            name="notes"
          >
            <TextArea
              rows={2}
              placeholder="Additional notes or context..."
              showCount
              maxLength={500}
            />
          </Form.Item>

          <Divider />

          {/* Submit Button */}
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={adding}
              icon={<PlusOutlined />}
              size="large"
              block
            >
              Add Entity to Review Queue
            </Button>
          </Form.Item>

          {/* Help Text */}
          <Alert
            message="How to add entities manually"
            description={
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>Enter the exact Wikipedia page title</li>
                <li>QID is optional - system will find it automatically</li>
                <li>Use search suggestions for accurate titles</li>
                <li>Added entities go to review queue first</li>
                <li>Smart deduplication prevents duplicates</li>
              </ul>
            }
            type="info"
            showIcon
          />
        </Form>
      </Card>

      {/* Result Modal */}
      <Modal
        title="Entity Addition Result"
        open={resultModalOpen}
        onCancel={() => setResultModalOpen(false)}
        footer={[
          <Button key="close" type="primary" onClick={() => setResultModalOpen(false)}>
            Close
          </Button>
        ]}
      >
        {lastResult && (
          <>
            <Alert
              message={lastResult.success ? 'Success' : 'Error'}
              description={lastResult.message}
              type={getResultType()}
              showIcon
              icon={getResultIcon()}
              style={{ marginBottom: 16 }}
            />

            {lastResult.entity && (
              <div>
                <Title level={5}>Entity Details:</Title>
                <List size="small">
                  <List.Item>
                    <Text strong>Title:</Text> {lastResult.entity.title}
                  </List.Item>
                  <List.Item>
                    <Text strong>QID:</Text> {lastResult.entity.qid}
                  </List.Item>
                  <List.Item>
                    <Text strong>Type:</Text> <Tag>{lastResult.entity.type}</Tag>
                  </List.Item>
                  <List.Item>
                    <Text strong>Status:</Text> <Tag color="blue">{lastResult.entity.status}</Tag>
                  </List.Item>
                </List>
              </div>
            )}

            {lastResult.was_duplicate && (
              <Alert
                message="Duplicate Detected"
                description={`This entity already exists with status: ${lastResult.existing_status}`}
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}

            {lastResult.queue_entry && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>Queue Information:</Title>
                <List size="small">
                  <List.Item>
                    <Text strong>Queue Type:</Text> <Tag color="blue">{lastResult.queue_entry.queue_type}</Tag>
                  </List.Item>
                  <List.Item>
                    <Text strong>Priority:</Text> 
                    <Tag color={lastResult.queue_entry.priority === 1 ? 'red' : 
                               lastResult.queue_entry.priority === 2 ? 'orange' : 'green'}>
                      {lastResult.queue_entry.priority === 1 ? 'High' : 
                       lastResult.queue_entry.priority === 2 ? 'Medium' : 'Low'}
                    </Tag>
                  </List.Item>
                  <List.Item>
                    <Text strong>Added By:</Text> {lastResult.queue_entry.added_by}
                  </List.Item>
                </List>
              </div>
            )}
          </>
        )}
      </Modal>
    </>
  )
}