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
  TeamOutlined,
  WarningOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import {
  useGetAllQueuesQuery,
  useGetQueueEntitiesQuery,
  useRemoveFromQueueMutation,
  useAddToQueueMutation,
  useFixInvalidCompletedMutation,
  useGetQueueTypeStatsQuery,
  useBulkApproveMappedToActiveMutation
} from '../store/api'
import { QueueType, QueueEntry, Priority } from '../types'
import { EntityPreviewDrawer } from '../components/entities/EntityPreviewDrawer'
import { ReviewQueue } from '../components/queues/ReviewQueue'


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
  const [fixInvalidCompleted, { isLoading: isFixing }] = useFixInvalidCompletedMutation()
  const { data: typeStats } = useGetQueueTypeStatsQuery(selectedQueue)
  const [bulkApproveMapped, { isLoading: isBulkApproving }] = useBulkApproveMappedToActiveMutation()

  // Update queueTypes array to include review queue:
  const queueTypes = [
    { key: QueueType.ACTIVE, label: 'Active Queue', color: '#1890ff', description: 'Ready for processing' },
    { key: QueueType.REVIEW, label: 'Review Queue', color: '#722ed1', description: 'Awaiting human review' }, // NEW
    { key: QueueType.COMPLETED, label: 'Completed', color: '#52c41a', description: 'Successfully processed' },
    { key: QueueType.FAILED, label: 'Failed', color: '#ff4d4f', description: 'Processing failed' },
    { key: QueueType.REJECTED, label: 'Rejected', color: '#faad14', description: 'Not suitable for processing' },
    { key: QueueType.ON_HOLD, label: 'On Hold', color: '#f0f0f0', description: 'Temporarily paused' },
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

  const handleFixInvalidCompleted = async () => {
    try {
      // First do a dry run to preview
      const previewResult = await fixInvalidCompleted({ dry_run: true }).unwrap()

      if (previewResult.entities.length === 0) {
        message.success('No invalid completed entities found!')
        return
      }

      // Show confirmation modal with details
      Modal.confirm({
        title: 'Fix Invalid Completed Entities',
        icon: <WarningOutlined style={{ color: '#faad14' }} />,
        width: 600,
        content: (
          <div>
            <p>Found <strong>{previewResult.entities.length}</strong> entities marked as "completed" but with no data:</p>
            <div style={{
              maxHeight: '300px',
              overflow: 'auto',
              marginTop: 16,
              padding: 12,
              background: '#fafafa',
              borderRadius: 4
            }}>
              {previewResult.entities.map((entity, idx) => (
                <div key={entity.qid} style={{ marginBottom: 8 }}>
                  <Text code>{entity.qid}</Text> - {entity.title} ({entity.type})
                </div>
              ))}
            </div>
            <p style={{ marginTop: 16 }}>
              These entities will be:
            </p>
            <ul>
              <li>Status changed: <Tag color="green">completed</Tag> → <Tag color="red">failed</Tag></li>
              <li>Moved from COMPLETED queue to FAILED queue</li>
            </ul>
          </div>
        ),
        onOk: async () => {
          try {
            const result = await fixInvalidCompleted({ dry_run: false }).unwrap()
            message.success({
              content: `Successfully fixed ${result.fixed_count} entities!`,
              icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
              duration: 5
            })
          } catch (error) {
            message.error('Failed to fix entities')
          }
        }
      })
    } catch (error) {
      message.error('Failed to check for invalid entities')
    }
  }

  const handleBulkApproveMapped = async () => {
    if (!typeStats) {
      message.error('Unable to load type statistics')
      return
    }

    if (typeStats.mapped_count === 0) {
      message.info('No entities with mapped types in this queue')
      return
    }

    // Show confirmation modal
    Modal.confirm({
      title: 'Send Mapped Entities to Active Queue',
      icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      width: 700,
      content: (
        <div>
          <p>This will move <strong>{typeStats.mapped_count}</strong> entities with mapped types to the ACTIVE queue:</p>

          <div style={{ marginTop: 16 }}>
            <Text strong>Mapped Types Breakdown:</Text>
            <div style={{
              marginTop: 8,
              padding: 12,
              background: '#f0f9ff',
              borderRadius: 4,
              border: '1px solid #91d5ff'
            }}>
              {Object.entries(typeStats.mapped_types).map(([type, count]) => (
                <div key={type} style={{ marginBottom: 4 }}>
                  <Tag color="blue">{type}</Tag>: {count} entities
                </div>
              ))}
            </div>
          </div>

          {typeStats.unmapped_count > 0 && (
            <div style={{ marginTop: 16 }}>
              <Text type="warning" strong>⚠️ {typeStats.unmapped_count} entities will be skipped (unmapped types):</Text>
              <div style={{
                marginTop: 8,
                padding: 12,
                background: '#fffbe6',
                borderRadius: 4,
                border: '1px solid #ffe58f',
                maxHeight: '150px',
                overflow: 'auto'
              }}>
                {typeStats.unmapped_types.map((type) => (
                  <Tag key={type} color="orange" style={{ marginBottom: 4 }}>
                    {type}
                  </Tag>
                ))}
              </div>
              <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
                You can map these types in the Type Mappings page before approving
              </Text>
            </div>
          )}
        </div>
      ),
      okText: `Move ${typeStats.mapped_count} Entities to Active`,
      okButtonProps: { type: 'primary' },
      onOk: async () => {
        try {
          const result = await bulkApproveMapped({
            queue_type: selectedQueue,
            priority: Priority.MEDIUM
          }).unwrap()

          const successMsg = `Successfully moved ${result.success_count} entities to ACTIVE queue!`
          const skipMsg = result.skipped_count > 0 ? ` ${result.skipped_count} skipped (unmapped types).` : ''
          const errorMsg = result.error_count > 0 ? ` ${result.error_count} errors.` : ''

          message.success({
            content: successMsg + skipMsg + errorMsg,
            icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
            duration: 6
          })
        } catch (error) {
          message.error('Failed to bulk approve mapped entities')
        }
      }
    })
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
          <Space>
            {/* Show bulk approve mapped button for queues that can have unmapped types */}
            {(selectedQueue === QueueType.FAILED ||
              selectedQueue === QueueType.REVIEW ||
              selectedQueue === QueueType.REJECTED) &&
              typeStats && typeStats.mapped_count > 0 && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleBulkApproveMapped}
                loading={isBulkApproving}
                style={{ background: '#52c41a', borderColor: '#52c41a' }}
              >
                Send Mapped to Active ({typeStats.mapped_count})
              </Button>
            )}
            <Button
              danger
              icon={<WarningOutlined />}
              onClick={handleFixInvalidCompleted}
              loading={isFixing}
            >
              Fix Invalid Completed
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => message.info('Batch operations available in Entity Manager')}
            >
              Batch Operations
            </Button>
          </Space>
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
            {/* Show type mapping stats for relevant queues */}
            {typeStats && typeStats.total > 0 && (
              <>
                <Tag color="green">
                  {typeStats.mapped_count} Mapped
                </Tag>
                {typeStats.unmapped_count > 0 && (
                  <Tag color="orange">
                    {typeStats.unmapped_count} Unmapped
                  </Tag>
                )}
              </>
            )}
          </Space>
        }
        loading={queueLoading}
      >
{/* // Add conditional rendering for review queue: */}
        {selectedQueue === QueueType.REVIEW ? (
          <ReviewQueue />
          // <h1>simple</h1>
        ) : (<>
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
        </>)}


      </Card>



      <EntityPreviewDrawer
        qid={previewEntityQid}
        open={previewDrawerOpen}
        onClose={() => setPreviewDrawerOpen(false)}
      />
    </div>
  )
}
