// src/components/queues/ReviewQueue.tsx
import React, { useState } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Row,
  Col,
  Select,
  Input,
  Tooltip,
  Modal,
  message,
  Alert,
  Badge,
  Statistic,
  Divider
} from 'antd'
import {
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  FilterOutlined,
  ReloadOutlined,
  UserOutlined,
  GlobalOutlined,
  TeamOutlined,
  CalendarOutlined,
  BookOutlined,
  RobotOutlined,
  SearchOutlined
} from '@ant-design/icons'
import {
  useGetQueueEntitiesQuery,
  useGetReviewQueueSourcesQuery,
  useBulkApproveReviewMutation,
  useBulkRejectReviewMutation,
  useGetDeduplicationStatsQuery
} from '../../store/api'
import { QueueType, Priority, QueueEntry } from '../../types'
import { EntityPreviewDrawer } from '../entities/EntityPreviewDrawer'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography
const { Option } = Select
const { confirm } = Modal

export const ReviewQueue: React.FC = () => {
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [previewDrawerOpen, setPreviewDrawerOpen] = useState(false)
  const [previewEntityQid, setPreviewEntityQid] = useState<string | null>(null)
  const [discoverySourceFilter, setDiscoverySourceFilter] = useState<string | undefined>()
  const [searchTerm, setSearchTerm] = useState('')
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 })

  const {
    data: reviewData,
    isLoading,
    refetch
  } = useGetQueueEntitiesQuery({
    queue_type: QueueType.REVIEW,
    limit: pagination.pageSize,
    offset: (pagination.current - 1) * pagination.pageSize,
    discovery_source: discoverySourceFilter
  })

  const { data: sourcesData } = useGetReviewQueueSourcesQuery()
  const { data: dedupStats } = useGetDeduplicationStatsQuery()

  const [bulkApprove, { isLoading: approving }] = useBulkApproveReviewMutation()
  const [bulkReject, { isLoading: rejecting }] = useBulkRejectReviewMutation()

  const hasSelected = selectedRowKeys.length > 0

  const handleBulkApprove = () => {
    confirm({
      title: 'Approve Selected Entities',
      content: `Are you sure you want to approve ${selectedRowKeys.length} entities and move them to the active queue?`,
      onOk: async () => {
        try {
          const result = await bulkApprove({
            operation: 'approve',
            qids: selectedRowKeys as string[],
            target_queue: QueueType.ACTIVE,
            priority: Priority.MEDIUM
          }).unwrap()

          message.success(`${result.success_count} entities approved successfully`)
          if (result.error_count > 0) {
            message.warning(`${result.error_count} entities failed to approve`)
          }

          setSelectedRowKeys([])
          refetch()
        } catch (error) {
          message.error('Failed to approve entities')
        }
      }
    })
  }

  const handleBulkReject = () => {
    confirm({
      title: 'Reject Selected Entities',
      content: `Are you sure you want to reject ${selectedRowKeys.length} entities? They will be moved to the rejected queue.`,
      okText: 'Yes, Reject',
      okType: 'danger',
      onOk: async () => {
        try {
          const result = await bulkReject({
            operation: 'reject',
            qids: selectedRowKeys as string[],
            target_queue: QueueType.REJECTED
          }).unwrap()

          message.success(`${result.success_count} entities rejected successfully`)
          if (result.error_count > 0) {
            message.warning(`${result.error_count} entities failed to reject`)
          }

          setSelectedRowKeys([])
          refetch()
        } catch (error) {
          message.error('Failed to reject entities')
        }
      }
    })
  }

  const handleSingleApprove = (qid: string) => {
    confirm({
      title: 'Approve Entity',
      content: 'Move this entity to the active queue for processing?',
      onOk: async () => {
        try {
          await bulkApprove({
            operation: 'approve',
            qids: [qid],
            target_queue: QueueType.ACTIVE,
            priority: Priority.MEDIUM
          }).unwrap()
          message.success('Entity approved')
          refetch()
        } catch (error) {
          message.error('Failed to approve entity')
        }
      }
    })
  }

  const handleSingleReject = (qid: string) => {
    confirm({
      title: 'Reject Entity',
      content: 'Move this entity to the rejected queue?',
      okText: 'Yes, Reject',
      okType: 'danger',
      onOk: async () => {
        try {
          await bulkReject({
            operation: 'reject',
            qids: [qid],
            target_queue: QueueType.REJECTED
          }).unwrap()
          message.success('Entity rejected')
          refetch()
        } catch (error) {
          message.error('Failed to reject entity')
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
      case 'event':
        return <CalendarOutlined />
      case 'concept':
        return <BookOutlined />
      default:
        return <BookOutlined />
    }
  }

  const getDiscoverySourceIcon = (source: string) => {
    switch (source) {
      case 'extraction_pipeline':
        return <RobotOutlined />
      case 'manual_entry':
        return <UserOutlined />
      default:
        return <SearchOutlined />
    }
  }

  const filteredData = reviewData?.entries.filter(entry =>
    !searchTerm ||
    entry.entity.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.entity.qid.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  const columns = [
    {
      title: 'Entity',
      key: 'entity',
      render: (_: any, record: QueueEntry) => (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {getTypeIcon(record.entity.type)}
            <Button
              type="link"
              onClick={() => {
                setPreviewEntityQid(record.qid)
                setPreviewDrawerOpen(true)
              }}
              style={{ padding: 0, height: 'auto', fontWeight: 500 }}
            >
              {record.entity.title}
            </Button>
          </div>
          <div style={{ marginTop: 4 }}>
            <Space size="small">
              <Text code style={{ fontSize: 11 }}>{record.qid}</Text>
              <Tag color="blue">{record.entity.type}</Tag>
            </Space>
          </div>
          {record.entity.short_desc && (
            <div style={{ marginTop: 4, maxWidth: 300 }}>
              <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
                {record.entity.short_desc}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Discovery',
      key: 'discovery',
      width: 150,
      render: (_: any, record: QueueEntry) => (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
            {getDiscoverySourceIcon(record.discovery_source || 'unknown')}
            <Text style={{ fontSize: 12 }}>
              {record.discovery_source?.replace('_', ' ') || 'Unknown'}
            </Text>
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>
              by {record.discovered_by || record.added_by}
            </Text>
          </div>
          <div>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {dayjs(record.added_date).fromNow()}
            </Text>
          </div>
        </div>
      ),
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: number) => {
        const colors = { 1: 'red', 2: 'orange', 3: 'green' }
        const labels = { 1: 'High', 2: 'Medium', 3: 'Low' }
        return <Tag color={colors[priority as keyof typeof colors]}>{labels[priority as keyof typeof labels]}</Tag>
      },
    },
    {
      title: 'Metrics',
      key: 'metrics',
      width: 120,
      render: (_: any, record: QueueEntry) => (
        <div>
          <div style={{ fontSize: 12, color: '#666' }}>
            Links: {record.entity.num_links}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            Length: {(record.entity.page_length / 1000).toFixed(1)}K
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            Depth: {record.entity.depth}
          </div>
        </div>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      fixed: 'right' as const,
      render: (_: any, record: QueueEntry) => (
        <Space size="small">
          <Tooltip title="Preview">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                setPreviewEntityQid(record.qid)
                setPreviewDrawerOpen(true)
              }}
            />
          </Tooltip>
          <Tooltip title="Approve">
            <Button
              size="small"
              type="primary"
              icon={<CheckOutlined />}
              onClick={() => handleSingleApprove(record.qid)}
            />
          </Tooltip>
          <Tooltip title="Reject">
            <Button
              size="small"
              danger
              icon={<CloseOutlined />}
              onClick={() => handleSingleReject(record.qid)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: setSelectedRowKeys,
  }

  return (
    <>
      <Card
        title={
          <Space>
            <FilterOutlined />
            <Title level={4} style={{ margin: 0 }}>Review Queue</Title>
            <Badge count={reviewData?.total || 0} />
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            loading={isLoading}
          >
            Refresh
          </Button>
        }
      >
        {/* Deduplication Stats */}
        {dedupStats && (
          <Alert
            message={
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="Total Discovered"
                    value={dedupStats.total_discovered}
                    valueStyle={{ fontSize: 16 }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Duplicates Filtered"
                    value={dedupStats.total_duplicates}
                    valueStyle={{ fontSize: 16, color: '#faad14' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Efficiency Rate"
                    value={Math.round(dedupStats.deduplication_rate * 100)}
                    suffix="%"
                    valueStyle={{ fontSize: 16, color: '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="For Review"
                    value={reviewData?.total || 0}
                    valueStyle={{ fontSize: 16, color: '#1890ff' }}
                  />
                </Col>
              </Row>
            }
            type="info"
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Filters and Search */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Input
              placeholder="Search by title or QID..."
              prefix={<SearchOutlined />}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              allowClear
            />
          </Col>
          <Col span={8}>
            <Select
              placeholder="Filter by discovery source"
              value={discoverySourceFilter}
              onChange={setDiscoverySourceFilter}
              allowClear
              style={{ width: '100%' }}
            >
              {sourcesData?.sources.map(source => (
                <Option key={source.source} value={source.source}>
                  <Space>
                    {getDiscoverySourceIcon(source.source)}
                    {source.source.replace('_', ' ')} ({source.count})
                  </Space>
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={8}>
            <Space>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={handleBulkApprove}
                disabled={!hasSelected}
                loading={approving}
              >
                Approve ({selectedRowKeys.length})
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
                onClick={handleBulkReject}
                disabled={!hasSelected}
                loading={rejecting}
              >
                Reject ({selectedRowKeys.length})
              </Button>
            </Space>
          </Col>
        </Row>

        <Divider />

        {/* Review Table */}
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={filteredData}
          rowKey="qid"
          loading={isLoading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: reviewData?.total || 0,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} entities`,
            onChange: (page, pageSize) =>
              setPagination({ current: page, pageSize: pageSize || 20 })
          }}
          scroll={{ x: 1000 }}
          size="small"
        />

        {/* Discovery Sources Summary */}
        {sourcesData?.sources && sourcesData.sources.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Title level={5}>Discovery Sources:</Title>
            <Space wrap>
              {sourcesData.sources.map(source => (
                <Tag
                  key={source.source || 'unknown'}
                  icon={getDiscoverySourceIcon(source.source)}
                  color={discoverySourceFilter === source.source ? 'blue' : 'default'}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setDiscoverySourceFilter(
                    discoverySourceFilter === source.source ? undefined : source.source
                  )}
                >
                  {source.source?.replace('_', ' ') || 'Unknown'}: {source.count}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {filteredData.length === 0 && !isLoading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">
              {searchTerm || discoverySourceFilter
                ? 'No entities match your filters'
                : 'No entities in review queue'
              }
            </Text>
          </div>
        )}
      </Card>

      {/* Entity Preview Drawer */}
      <EntityPreviewDrawer
        qid={previewEntityQid}
        open={previewDrawerOpen}
        onClose={() => setPreviewDrawerOpen(false)}
      />
    </>
  )
}