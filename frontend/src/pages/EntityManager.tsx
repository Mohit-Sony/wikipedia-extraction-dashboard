// src/pages/EntityManager.tsx
import React, { useState, useCallback } from 'react'
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Input, 
  Select, 
  Tag, 
  Typography,
  Row,
  Col,
  message,
  Tooltip,
  Badge
} from 'antd'
import {
  FilterOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { 
  useGetEntitiesQuery, 
  useAddToQueueMutation, 
  useBatchQueueOperationMutation 
} from '../store/api'
import {
  selectFilters,
  selectSelectedEntities,
  updateFilters,
  toggleEntitySelection,
  selectAllEntities,
  clearSelection,
  setSearch,
  setSorting,
  setPagination
} from '../store/slices/uiSlice'
import { Entity, QueueType, Priority, EntityStatus } from '../types'
import { EntityPreviewDrawer } from '../components/entities/EntityPreviewDrawer'
import { BatchOperationModal } from '../components/entities/BatchOperationModal'
import { EntityFilters } from '../components/entities/EntityFilters'

const { Title, Text } = Typography
const { Option } = Select

export const EntityManager: React.FC = () => {
  const dispatch = useDispatch()
  const filters = useSelector(selectFilters)
  const selectedEntities = useSelector(selectSelectedEntities)
  
  const [previewDrawerOpen, setPreviewDrawerOpen] = useState(false)
  const [previewEntityQid, setPreviewEntityQid] = useState<string | null>(null)
  const [batchModalOpen, setBatchModalOpen] = useState(false)
  const [filtersDrawerOpen, setFiltersDrawerOpen] = useState(false)

  const { data: entitiesData, isLoading } = useGetEntitiesQuery(filters)
  const [addToQueue] = useAddToQueueMutation()
  const [batchOperation] = useBatchQueueOperationMutation()

  const entities = entitiesData?.entities || []
  const total = entitiesData?.total || 0

  const handleSearch = useCallback((value: string) => {
    dispatch(setSearch(value))
  }, [dispatch])

  const handleTableChange = (pagination: any, sorter: any) => {
    if (sorter.field) {
      dispatch(setSorting({
        sort_by: sorter.field,
        sort_order: sorter.order === 'ascend' ? 'asc' : 'desc'
      }))
    }

    if (pagination.current !== undefined && pagination.pageSize !== undefined) {
      dispatch(setPagination({
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize
      }))
    }
  }

  const handleRowSelection = {
    selectedRowKeys: selectedEntities,
    onChange: (selectedRowKeys: React.Key[]) => {
      dispatch(selectAllEntities(selectedRowKeys as string[]))
    },
    onSelect: (record: Entity, ) => {
      dispatch(toggleEntitySelection(record.qid))
    },
    onSelectAll: (selected: boolean) => {
      if (selected) {
        dispatch(selectAllEntities(entities.map(e => e.qid)))
      } else {
        dispatch(clearSelection())
      }
    },
  }

  const handlePreview = (qid: string) => {
    setPreviewEntityQid(qid)
    setPreviewDrawerOpen(true)
  }

  const handleQuickAddToQueue = async (qid: string, queueType: QueueType) => {
    try {
      await addToQueue({
        qid,
        queue_type: queueType,
        priority: Priority.MEDIUM
      }).unwrap()
      message.success('Entity added to queue successfully')
    } catch (error) {
      message.error('Failed to add entity to queue')
    }
  }

  const handleBatchOperation = async (operation: any) => {
    try {
      const result = await batchOperation({
        operation: operation.operation,
        qids: selectedEntities,
        target_queue: operation.target_queue,
        priority: operation.priority,
        notes: operation.notes
      }).unwrap()

      message.success(`Batch operation completed: ${result.success_count} successful, ${result.error_count} errors`)
      
      if (result.error_count === 0) {
        dispatch(clearSelection())
      }
    } catch (error) {
      message.error('Batch operation failed')
    }
  }

  const getStatusColor = (status: EntityStatus) => {
    switch (status) {
      case EntityStatus.COMPLETED: return 'success'
      case EntityStatus.PROCESSING: return 'processing'
      case EntityStatus.QUEUED: return 'warning'
      case EntityStatus.FAILED: return 'error'
      case EntityStatus.REJECTED: return 'default'
      default: return 'default'
    }
  }

  const columns = [
    {
      title: 'QID',
      dataIndex: 'qid',
      key: 'qid',
      width: 120,
      render: (qid: string) => (
        <Text code copyable={{ text: qid }}>
          {qid}
        </Text>
      ),
    },
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      sorter: true,
      render: (title: string, record: Entity) => (
        <Button 
          type="link" 
          onClick={() => handlePreview(record.qid)}
          style={{ padding: 0, height: 'auto' }}
        >
          {title}
        </Button>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: EntityStatus) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: 'Links',
      dataIndex: 'num_links',
      key: 'num_links',
      width: 80,
      sorter: true,
      render: (num: number) => <Badge count={num} showZero color="#108ee9" />,
    },
    {
      title: 'Tables',
      dataIndex: 'num_tables',
      key: 'num_tables',
      width: 80,
      sorter: true,
      render: (num: number) => <Badge count={num} showZero color="#87d068" />,
    },
    {
      title: 'Images',
      dataIndex: 'num_images',
      key: 'num_images',
      width: 80,
      sorter: true,
      render: (num: number) => <Badge count={num} showZero color="#f50" />,
    },
    {
      title: 'Page Length',
      dataIndex: 'page_length',
      key: 'page_length',
      width: 110,
      sorter: true,
      render: (length: number) => (
        <Text type="secondary">{length.toLocaleString()}</Text>
      ),
    },
    {
      title: 'Depth',
      dataIndex: 'depth',
      key: 'depth',
      width: 80,
      sorter: true,
      render: (depth: number) => <Tag color="purple">{depth}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_:any, record: Entity) => (
        <Space size="small">
          <Tooltip title="Preview">
            <Button 
              size="small" 
              icon={<EyeOutlined />} 
              onClick={() => handlePreview(record.qid)}
            />
          </Tooltip>
          <Tooltip title="Add to Active Queue">
            <Button 
              size="small" 
              icon={<PlusOutlined />}
              onClick={() => handleQuickAddToQueue(record.qid, QueueType.ACTIVE)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* Page Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            Entity Manager
          </Title>
          <Text type="secondary">
            Browse and manage Wikipedia entities ({total.toLocaleString()} total)
          </Text>
        </Col>
        <Col>
          <Space>
            <Button 
              icon={<FilterOutlined />}
              onClick={() => setFiltersDrawerOpen(true)}
            >
              Advanced Filters
            </Button>
            {selectedEntities.length > 0 && (
              <Button 
                type="primary"
                onClick={() => setBatchModalOpen(true)}
              >
                Batch Actions ({selectedEntities.length})
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {/* Search and Quick Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input.Search
              placeholder="Search entities by title, QID, or description..."
              allowClear
              size="large"
              onSearch={handleSearch}
              style={{ width: '100%' }}
            />
          </Col>
          <Col>
            <Select
              placeholder="Status"
              allowClear
              style={{ width: 120 }}
              onChange={(value) => dispatch(updateFilters({ status: value ? [value] : [] }))}
            >
              {Object.values(EntityStatus).map(status => (
                <Option key={status} value={status}>{status}</Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Select
              placeholder="Type"
              allowClear
              style={{ width: 120 }}
              onChange={(value) => dispatch(updateFilters({ types: value ? [value] : [] }))}
            >
              <Option value="human">Human</Option>
              <Option value="place">Place</Option>
              <Option value="organization">Organization</Option>
              <Option value="event">Event</Option>
              <Option value="concept">Concept</Option>
            </Select>
          </Col>
          <Col>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={() => dispatch(updateFilters({}))}
            >
              Refresh
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Entity Table */}
      <Card>
        <Table
          rowSelection={handleRowSelection}
          columns={columns}
          dataSource={entities}
          rowKey="qid"
          loading={isLoading}
          pagination={{
            current: Math.floor(filters.offset / filters.limit) + 1,
            pageSize: filters.limit,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} of ${total} entities`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
          size="small"
        />
      </Card>

      {/* Entity Preview Drawer */}
      <EntityPreviewDrawer
        qid={previewEntityQid}
        open={previewDrawerOpen}
        onClose={() => setPreviewDrawerOpen(false)}
      />

      {/* Batch Operation Modal */}
      <BatchOperationModal
        open={batchModalOpen}
        selectedCount={selectedEntities.length}
        onConfirm={handleBatchOperation}
        onCancel={() => setBatchModalOpen(false)}
      />

      {/* Advanced Filters Drawer */}
      <EntityFilters
        open={filtersDrawerOpen}
        onClose={() => setFiltersDrawerOpen(false)}
      />
    </div>
  )
}