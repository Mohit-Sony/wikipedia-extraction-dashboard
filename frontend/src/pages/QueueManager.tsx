// src/pages/QueueManager.tsx
import React, { useState } from 'react'
import { Row, Col, Card, List, Button, Tag, Typography, Space, Dropdown, Menu, Modal, message } from 'antd'
import { 
  UnorderedListOutlined, 
  MoreOutlined, 
  EyeOutlined, 
  DeleteOutlined,
  ArrowRightOutlined,
  PlusOutlined,
  UserOutlined,
  GlobalOutlined,
  TeamOutlined
} from '@ant-design/icons'
import { 
  useGetAllQueuesQuery, 
  useGetQueueEntitiesQuery, 
  useRemoveFromQueueMutation,
  useAddToQueueMutation 
} from '../store/api'
import { QueueType, QueueEntry, Priority } from '../types'
import { EntityPreviewDrawer } from '../components/entities/EntityPreviewDrawer'

const { Title, Text } = Typography
const { confirm } = Modal

export const QueueManager: React.FC = () => {
  const [selectedQueue, setSelectedQueue] = useState<QueueType>(QueueType.ACTIVE)
  const [previewDrawerOpen, setPreviewDrawerOpen] = useState(false)
  const [previewEntityQid, setPreviewEntityQid] = useState<string | null>(null)

  const { data: allQueues, isLoading: queuesLoading } = useGetAllQueuesQuery()
  const { data: queueData, isLoading: queueLoading } = useGetQueueEntitiesQuery({
    queue_type: selectedQueue,
    limit: 50
  })
  const [removeFromQueue] = useRemoveFromQueueMutation()
  const [addToQueue] = useAddToQueueMutation()

  const queueTypes = [
    { key: QueueType.ACTIVE, label: 'Active Queue', color: '#1890ff', description: 'Ready for processing' },
    { key: QueueType.ON_HOLD, label: 'On Hold', color: '#722ed1', description: 'Temporarily paused' },
    { key: QueueType.REJECTED, label: 'Rejected', color: '#faad14', description: 'Not suitable for processing' },
    { key: QueueType.COMPLETED, label: 'Completed', color: '#52c41a', description: 'Successfully processed' },
    { key: QueueType.FAILED, label: 'Failed', color: '#ff4d4f', description: 'Processing failed' },
  ]

  const handlePreview = (qid: string) => {
    setPreviewEntityQid(qid)
    setPreviewDrawerOpen(true)
  }

  const handleRemoveFromQueue = async (entryId: number) => {
    try {
      await removeFromQueue(entryId).unwrap()
      message.success('Entity removed from queue')
    } catch (error) {
      message.error('Failed to remove entity from queue')
    }
  }

  const handleMoveToQueue = async (qid: string, targetQueue: QueueType) => {
    try {
      await addToQueue({
        qid,
        queue_type: targetQueue,
        priority: Priority.MEDIUM
      }).unwrap()
      message.success(`Entity moved to ${targetQueue} queue`)
    } catch (error) {
      message.error('Failed to move entity')
    }
  }

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
        return <UnorderedListOutlined />
    }
  }

  const getEntityActions = (entry: QueueEntry) => (
    <Menu>
      <Menu.Item 
        key="preview" 
        icon={<EyeOutlined />}
        onClick={() => handlePreview(entry.qid)}
      >
        Preview Entity
      </Menu.Item>
      <Menu.SubMenu key="move" title="Move to Queue" icon={<ArrowRightOutlined />}>
        {queueTypes
          .filter(q => q.key !== selectedQueue)
          .map(queue => (
            <Menu.Item 
              key={queue.key}
              onClick={() => handleMoveToQueue(entry.qid, queue.key)}
            >
              {queue.label}
            </Menu.Item>
          ))
        }
      </Menu.SubMenu>
      <Menu.Divider />
      <Menu.Item 
        key="remove" 
        icon={<DeleteOutlined />}
        danger
        onClick={() => {
          confirm({
            title: 'Remove from Queue',
            content: 'Are you sure you want to remove this entity from the queue?',
            onOk: () => handleRemoveFromQueue(entry.id)
          })
        }}
      >
        Remove from Queue
      </Menu.Item>
    </Menu>
  )

  const renderQueueCard = (queueType: any) => {
    const count = allQueues?.[queueType.key]?.count || 0
    const isSelected = selectedQueue === queueType.key

    return (
      <Card
        key={queueType.key}
        size="small"
        hoverable
        style={{
          cursor: 'pointer',
          border: isSelected ? `2px solid ${queueType.color}` : '1px solid #f0f0f0',
          backgroundColor: isSelected ? '#fafafa' : 'white',
          transition: 'all 0.3s ease'
        }}
        onClick={() => setSelectedQueue(queueType.key)}
      >
        <div style={{ textAlign: 'center' }}>
          <div style={{ 
            fontSize: 32, 
            fontWeight: 'bold', 
            color: queueType.color,
            marginBottom: 8 
          }}>
            {count}
          </div>
          <div style={{ 
            fontSize: 16, 
            fontWeight: 500,
            marginBottom: 4 
          }}>
            {queueType.label}
          </div>
          <div style={{ 
            fontSize: 12, 
            color: '#666',
            lineHeight: 1.3 
          }}>
            {queueType.description}
          </div>
        </div>
      </Card>
    )
  }

  const getPriorityColor = (priority: number) => {
    switch (priority) {
      case Priority.HIGH:
        return 'error'
      case Priority.MEDIUM:
        return 'warning'
      case Priority.LOW:
        return 'default'
      default:
        return 'default'
    }
  }

  const getPriorityText = (priority: number) => {
    switch (priority) {
      case Priority.HIGH:
        return 'High'
      case Priority.MEDIUM:
        return 'Medium'
      case Priority.LOW:
        return 'Low'
      default:
        return 'Medium'
    }
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            Queue Manager
          </Title>
          <Text type="secondary">
            Manage entity processing queues and workflow
          </Text>
        </Col>
        <Col>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => message.info('Batch operations available in Entity Manager')}
          >
            Batch Operations
          </Button>
        </Col>
      </Row>

      {/* Queue Overview Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {queueTypes.map(renderQueueCard)}
      </Row>

      {/* Selected Queue Content */}
      <Card 
        title={
          <Space>
            <UnorderedListOutlined style={{ color: queueTypes.find(q => q.key === selectedQueue)?.color }} />
            <span>{queueTypes.find(q => q.key === selectedQueue)?.label}</span>
            <Tag color={queueTypes.find(q => q.key === selectedQueue)?.color}>
              {queueData?.total || 0} entities
            </Tag>
          </Space>
        }
        loading={queueLoading}
      >
        {queueData?.entries?.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
            <UnorderedListOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <div style={{ fontSize: 16 }}>No entities in this queue</div>
            <div style={{ fontSize: 14, marginTop: 8 }}>
              Entities will appear here when added to the {selectedQueue} queue
            </div>
          </div>
        ) : (
          <List
            dataSource={queueData?.entries || []}
            renderItem={(entry: QueueEntry) => (
              <List.Item
                style={{ 
                  padding: '16px 0',
                  borderBottom: '1px solid #f0f0f0' 
                }}
                actions={[
                  <Dropdown 
                    key="actions"
                    overlay={getEntityActions(entry)} 
                    trigger={['click']}
                    placement="bottomRight"
                  >
                    <Button type="text" icon={<MoreOutlined />} />
                  </Dropdown>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <div style={{ 
                      width: 40, 
                      height: 40, 
                      borderRadius: '50%', 
                      backgroundColor: '#f0f2f5',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#1890ff',
                      fontSize: 16
                    }}>
                      {getTypeIcon(entry.entity.type)}
                    </div>
                  }
                  title={
                    <Space size="large">
                      <Button 
                        type="link" 
                        onClick={() => handlePreview(entry.qid)}
                        style={{ padding: 0, height: 'auto', fontSize: 16, fontWeight: 500 }}
                      >
                        {entry.entity.title}
                      </Button>
                      <Text code style={{ fontSize: 12 }}>{entry.qid}</Text>
                    </Space>
                  }
                  description={
                    <div style={{ marginTop: 8 }}>
                      <Space wrap>
                        <Tag color="blue">{entry.entity.type}</Tag>
                        <Tag color={getPriorityColor(entry.priority)}>
                          {getPriorityText(entry.priority)} Priority
                        </Tag>
                        <Text type="secondary">{entry.entity.num_links} links</Text>
                        <Text type="secondary">
                          {(entry.entity.page_length / 1000).toFixed(1)}K chars
                        </Text>
                        <Text type="secondary">
                          Added {new Date(entry.added_date).toLocaleDateString()}
                        </Text>
                      </Space>
                      {entry.notes && (
                        <div style={{ marginTop: 8 }}>
                          <Text type="secondary" style={{ fontStyle: 'italic' }}>
                            Note: {entry.notes}
                          </Text>
                        </div>
                      )}
                      {entry.entity.short_desc && (
                        <div style={{ marginTop: 8, maxWidth: 600 }}>
                          <Text type="secondary" ellipsis>
                            {entry.entity.short_desc}
                          </Text>
                        </div>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
            pagination={{
              total: queueData?.total || 0,
              pageSize: 50,
              showSizeChanger: false,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `${range[0]}-${range[1]} of ${total} entities`,
            }}
          />
        )}
      </Card>

      <EntityPreviewDrawer
        qid={previewEntityQid}
        open={previewDrawerOpen}
        onClose={() => setPreviewDrawerOpen(false)}
      />
    </div>
  )
}
