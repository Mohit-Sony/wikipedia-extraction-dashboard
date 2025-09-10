// frontend/src/components/entities/EntityPreviewDrawer.tsx
import React, { useState } from 'react'
import {
  Drawer, Spin, Alert, Typography, Descriptions, Tag, Card, Row, Col, Space,
  Tabs, Table, Image, Collapse, List, Button, Tooltip, Badge, Divider,
  Timeline, Progress, Avatar, Empty, Statistic
} from 'antd'
import {
  InfoCircleOutlined, LinkOutlined, TableOutlined, PictureOutlined,
  BookOutlined, TagOutlined, FileTextOutlined, BranchesOutlined,
  EyeOutlined, CopyOutlined, ClockCircleOutlined,
  CodeOutlined, TeamOutlined, GlobalOutlined, UserOutlined,
  BarChartOutlined, FolderOutlined, HistoryOutlined, DatabaseOutlined,
  NodeIndexOutlined, FileSearchOutlined, TagsOutlined
} from '@ant-design/icons'
import { useGetEntityPreviewQuery } from '../../store/api'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Paragraph, Text } = Typography
const { TabPane } = Tabs
const { Panel } = Collapse

interface EntityPreviewDrawerProps {
  qid: string | null
  open: boolean
  onClose: () => void
}

export const EntityPreviewDrawer: React.FC<EntityPreviewDrawerProps> = ({ qid, open, onClose }) => {
  const [activeTab, setActiveTab] = useState("overview")
  const { data: preview, isLoading, error } = useGetEntityPreviewQuery(qid!, {
    skip: !qid || !open
  })

  // Utility functions with proper null checks
  const getTypeIcon = (type?: string | null) => {
    if (!type) return <InfoCircleOutlined />
    
    switch (type.toLowerCase()) {
      case 'person':
      case 'human':
        return <UserOutlined />
      case 'place':
      case 'location':
      case 'country':
        return <GlobalOutlined />
      case 'organization':
      case 'company':
        return <TeamOutlined />
      case 'concept':
      case 'theory':
        return <FileSearchOutlined />
      case 'event':
        return <ClockCircleOutlined />
      default:
        return <InfoCircleOutlined />
    }
  }

  const getQueueStatusColor = (status?: string | null) => {
    if (!status) return 'default'
    
    const colors: Record<string, string> = {
      'active': 'processing',
      'completed': 'success',
      'failed': 'error',
      'rejected': 'default',
      'review': 'warning',
      'on_hold': 'orange',
      'processing': 'blue'
    }
    return colors[status] || 'default'
  }

  const getPriorityColor = (priority?: number | null) => {
    if (!priority) return '#d9d9d9'
    
    switch (priority) {
      case 1: return '#ff4d4f' // High - Red
      case 2: return '#faad14' // Medium - Orange  
      case 3: return '#52c41a' // Low - Green
      default: return '#d9d9d9' // Unknown - Gray
    }
  }

  const getPriorityText = (priority?: number | null) => {
    if (!priority) return 'Unknown'
    
    switch (priority) {
      case 1: return 'High'
      case 2: return 'Medium'
      case 3: return 'Low'
      default: return 'Unknown'
    }
  }

  const copyToClipboard = (text?: string | null) => {
    if (text) {
      navigator.clipboard.writeText(text)
    }
  }

  const safeFormatDate = (dateString?: string | null) => {
    if (!dateString) return 'Unknown'
    try {
      return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
    } catch {
      return 'Invalid date'
    }
  }

  const safeFromNow = (dateString?: string | null) => {
    if (!dateString) return 'Unknown'
    try {
      return dayjs(dateString).fromNow()
    } catch {
      return 'Unknown'
    }
  }

  // Tab rendering functions
  const renderOverviewTab = () => {
    if (!preview) return <Empty description="No data available" />

    return (
      <div>
        {/* Header Section */}
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <div style={{ textAlign: 'center' }}>
                {preview.images && preview.images.length > 0 ? (
                  <Image
                    width={100}
                    height={100}
                    src={preview.images[0]?.url || ''}
                    alt={preview.images[0]?.alt || 'Entity image'}
                    style={{ objectFit: 'cover', borderRadius: 8 }}
                    placeholder={
                      <div style={{
                        width: 100,
                        height: 100,
                        background: '#f5f5f5',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: 8
                      }}>
                        {getTypeIcon(preview.type)}
                      </div>
                    }
                  />
                ) : (
                  <Avatar
                    size={100}
                    icon={getTypeIcon(preview.type)}
                    style={{ backgroundColor: '#f5f5f5', color: '#1890ff' }}
                  />
                )}
              </div>
            </Col>
            <Col span={20}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <Title level={4} style={{ margin: 0, marginBottom: 8 }}>
                    {preview.title || 'Untitled'}
                    <Tooltip title="Copy QID">
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(preview.qid)}
                        style={{ marginLeft: 8 }}
                      />
                    </Tooltip>
                  </Title>
                  <Space wrap style={{ marginBottom: 12 }}>
                    <Tag color="blue" icon={getTypeIcon(preview.type)}>
                      {preview.type || 'Unknown'}
                    </Tag>
                    <Tag color="purple">{preview.qid || 'No QID'}</Tag>
                    <Tag color="green">
                      Depth: {preview.extraction_info?.depth ?? 0}
                    </Tag>
                    {preview.relationships?.queue_status?.queue_type && (
                      <Tag color={getQueueStatusColor(preview.relationships.queue_status.queue_type)}>
                        {preview.relationships.queue_status.queue_type}
                      </Tag>
                    )}
                    {preview.relationships?.queue_status?.priority && (
                      <Tag color={getPriorityColor(preview.relationships.queue_status.priority)}>
                        {getPriorityText(preview.relationships.queue_status.priority)} Priority
                      </Tag>
                    )}
                  </Space>
                  <Paragraph style={{ marginBottom: 12 }}>
                    {preview.content?.description || 'No description available'}
                  </Paragraph>
                  <Space wrap>
                    <Text type="secondary">
                      <ClockCircleOutlined /> Extracted {safeFromNow(preview.extraction_info?.timestamp)}
                    </Text>
                    {preview.extraction_info?.parent_qid && (
                      <Text type="secondary">
                        <BranchesOutlined /> Discovered by
                        <Text code style={{ marginLeft: 4 }}>
                          {preview.extraction_info.parent_qid}
                        </Text>
                      </Text>
                    )}
                    <Text type="secondary">
                      <DatabaseOutlined /> {preview.extraction_info?.extraction_time || 0}s processing
                    </Text>
                  </Space>
                </div>
              </div>
            </Col>
          </Row>
        </Card>

        {/* Statistics Grid */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title="Internal Links"
                value={preview.links?.internal_count || 0}
                valueStyle={{ color: '#1890ff' }}
                prefix={<LinkOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title="Tables"
                value={preview.metadata?.num_tables || 0}
                valueStyle={{ color: '#52c41a' }}
                prefix={<TableOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title="Images"
                value={preview.metadata?.num_images || 0}
                valueStyle={{ color: '#faad14' }}
                prefix={<PictureOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title="Page Size"
                value={Math.round((preview.metadata?.page_length || 0) / 1000)}
                suffix="K chars"
                valueStyle={{ color: '#722ed1' }}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* Content Extract */}
        <Card title="Content Extract" style={{ marginBottom: 16 }}>
          <Paragraph ellipsis={{ rows: 6, expandable: true, symbol: 'Show more' }}>
            {preview.content?.extract || 'No content extract available'}
          </Paragraph>
        </Card>

        {/* Quick Links Preview */}
        <Card
          title="Top Related Entities"
          extra={
            <Space>
              <Text type="secondary">{preview.links?.internal_count || 0} total</Text>
              <Button size="small" onClick={() => setActiveTab('links')}>
                View All
              </Button>
            </Space>
          }
        >
          <List
            dataSource={preview.links?.internal_links?.slice(0, 5) || []}
            renderItem={(link) => (
              <List.Item>
                <List.Item.Meta
                  avatar={<Avatar size="small" icon={getTypeIcon(link?.type)} />}
                  title={
                    <Space>
                      <Text strong>{link?.title || 'Untitled'}</Text>
                      <Text code style={{ fontSize: 10 }}>{link?.qid || 'No QID'}</Text>
                      <Tag color="blue">{link?.type || 'Unknown'}</Tag>
                    </Space>
                  }
                  description={link?.shortDesc || 'No description'}
                />
              </List.Item>
            )}
            locale={{ emptyText: 'No links available' }}
          />
        </Card>
      </div>
    )
  }

  const renderContentTab = () => {
    if (!preview) return <Empty description="No data available" />

    return (
      <div>
        <Card title="Full Content Extract" style={{ marginBottom: 16 }}>
          <Paragraph>
            {preview.content?.extract || 'No content extract available'}
          </Paragraph>
        </Card>

        {preview.content?.wikitext_preview && (
          <Card title="Wikitext Preview" style={{ marginBottom: 16 }}>
            <pre style={{
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 4,
              fontSize: 12,
              maxHeight: 300,
              overflow: 'auto',
              whiteSpace: 'pre-wrap'
            }}>
              {preview.content.wikitext_preview}
            </pre>
          </Card>
        )}

        <Card title={`Content Chunks (${preview.metadata?.num_chunks || 0} total)`}>
          {preview.content_chunks && preview.content_chunks.length > 0 ? (
            <Collapse ghost>
              {preview.content_chunks.map((chunk, index) => (
                <Panel
                  header={
                    <Space>
                      <Text strong>{chunk?.section || 'Untitled Section'}</Text>
                      <Text type="secondary">Paragraph {chunk?.paragraph || 0}</Text>
                      {chunk?.has_references && (
                        <Badge count="refs" style={{ backgroundColor: '#52c41a' }} />
                      )}
                    </Space>
                  }
                  key={index}
                >
                  <Paragraph>{chunk?.text_preview || 'No preview available'}...</Paragraph>
                </Panel>
              ))}
            </Collapse>
          ) : (
            <Empty description="No content chunks available" />
          )}
        </Card>
      </div>
    )
  }

  const renderInfoboxTab = () => {
    if (!preview) return <Empty description="No data available" />

    const infoboxEntries = preview.infobox ? Object.entries(preview.infobox) : []

    return (
      <Card title={`Infobox Data (${infoboxEntries.length} fields)`}>
        {infoboxEntries.length > 0 ? (
          <Descriptions column={1} size="small" bordered>
            {infoboxEntries.map(([key, value]) => (
              <Descriptions.Item key={key} label={<strong>{key}</strong>}>
                <Text copyable={{ text: String(value || '') }}>
                  {String(value || '')}
                </Text>
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : (
          <Empty description="No infobox data available" />
        )}
      </Card>
    )
  }

  const renderLinksTab = () => {
    if (!preview) return <Empty description="No data available" />

    return (
      <div>
        {/* Link Type Distribution */}
        {preview.links?.top_link_types && preview.links.top_link_types.length > 0 && (
          <Card title="Link Type Analysis" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              {preview.links.top_link_types.map((typeInfo, index) => (
                <Col span={6} key={index}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Statistic
                      title={typeInfo?.type || 'Unknown'}
                      value={typeInfo?.count || 0}
                      valueStyle={{ fontSize: 18, color: '#1890ff' }}
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        )}

        {/* Internal Links */}
        <Card title={`Internal Links (${preview.links?.internal_count || 0})`} style={{ marginBottom: 16 }}>
          <List
            dataSource={preview.links?.internal_links || []}
            renderItem={(link) => (
              <List.Item
                actions={[
                  <Button type="link" size="small" icon={<EyeOutlined />} key="view">
                    View
                  </Button>,
                  <Button
                    type="link"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyToClipboard(link?.qid)}
                    key="copy"
                  >
                    Copy QID
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<Avatar size="small" icon={getTypeIcon(link?.type)} />}
                  title={
                    <Space>
                      <Text strong>{link?.title || 'Untitled'}</Text>
                      <Text code style={{ fontSize: 10 }}>{link?.qid || 'No QID'}</Text>
                      <Tag color="blue">{link?.type || 'Unknown'}</Tag>
                    </Space>
                  }
                  description={link?.shortDesc || 'No description'}
                />
              </List.Item>
            )}
            pagination={{
              pageSize: 10,
              size: 'small',
              showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} links`
            }}
            locale={{ emptyText: 'No internal links available' }}
          />
        </Card>

        {/* External Links */}
        {preview.links?.external_links && preview.links.external_links.length > 0 && (
          <Card title={`External Links (${preview.links?.external_count || 0})`}>
            <List
              dataSource={preview.links.external_links}
              renderItem={(link) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      size="small"
                      icon={<LinkOutlined />}
                      href={link?.url || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      key="visit"
                    >
                      Visit
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={link?.title || 'Untitled'}
                    description={
                      <Text copyable={{ text: link?.url || '' }} ellipsis>
                        {link?.url || 'No URL'}
                      </Text>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: 'No external links available' }}
            />
          </Card>
        )}
      </div>
    )
  }

  const renderTablesTab = () => {
    if (!preview) return <Empty description="No data available" />

    return (
      <div>
        {preview.tables && preview.tables.length > 0 ? (
          preview.tables.map((table) => (
            <Card
              key={table?.index || 0}
              title={table?.caption || 'Untitled Table'}
              extra={
                <Space>
                  <Text type="secondary">
                    {table?.total_rows || 0} rows × {table?.total_columns || 0} columns
                  </Text>
                  <Button size="small" icon={<CopyOutlined />}>
                    Copy Data
                  </Button>
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Table
                dataSource={(table?.sample_rows || []).map((row, i) => ({
                  key: i,
                  ...(row || []).reduce((acc: any, cell: string, j: number) => ({
                    ...acc,
                    [`col${j}`]: cell || ''
                  }), {})
                }))}
                columns={(table?.headers || []).map((header, i) => ({
                  title: header || `Column ${i + 1}`,
                  dataIndex: `col${i}`,
                  key: `col${i}`,
                  width: 150,
                  ellipsis: true
                }))}
                size="small"
                pagination={false}
                scroll={{ x: true }}
                footer={() => (
                  <Text type="secondary">
                    Showing first {Math.min(3, table?.total_rows || 0)} rows of {table?.total_rows || 0} total rows
                  </Text>
                )}
              />
            </Card>
          ))
        ) : (
          <Empty
            description="No table data available"
            image={<TableOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
          />
        )}
      </div>
    )
  }

  const renderImagesTab = () => {
    if (!preview) return <Empty description="No data available" />

    return (
      <div>
        {preview.images && preview.images.length > 0 ? (
          <Row gutter={16}>
            {preview.images.map((image) => (
              <Col key={image?.index || 0} span={12} style={{ marginBottom: 16 }}>
                <Card
                  cover={
                    <Image
                      src={image?.url || ''}
                      alt={image?.alt || 'Entity image'}
                      style={{ height: 200, objectFit: 'cover' }}
                      placeholder={
                        <div style={{
                          height: 200,
                          background: '#f5f5f5',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          <PictureOutlined style={{ fontSize: 24, color: '#ccc' }} />
                        </div>
                      }
                    />
                  }
                  size="small"
                  actions={[
                    <Tooltip title="Copy image URL" key="copy">
                      <Button
                        type="text"
                        icon={<CopyOutlined />}
                        onClick={() => copyToClipboard(image?.url)}
                      />
                    </Tooltip>,
                    <Tooltip title="Open in new tab" key="open">
                      <Button
                        type="text"
                        icon={<LinkOutlined />}
                        onClick={() => image?.url && window.open(image.url, '_blank')}
                      />
                    </Tooltip>
                  ]}
                >
                  <Card.Meta
                    title={`Image ${(image?.index || 0) + 1}`}
                    description={
                      <div>
                        <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}>
                          {image?.caption || 'No caption'}
                        </Paragraph>
                        <Text code style={{ fontSize: 10 }}>
                          {image?.filename || 'No filename'}
                        </Text>
                      </div>
                    }
                  />
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty
            description="No images available"
            image={<PictureOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
          />
        )}
      </div>
    )
  }

  const renderMetadataTab = () => {
    if (!preview) return <Empty description="No data available" />

    return (
      <div>
        <Card title="Page Information" style={{ marginBottom: 16 }}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Page Length">
              <Text copyable={{ text: String(preview.metadata?.page_length || 0) }}>
                {(preview.metadata?.page_length || 0).toLocaleString()} characters
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Last Modified">
              {safeFormatDate(preview.metadata?.last_modified)}
            </Descriptions.Item>
            <Descriptions.Item label="Revision ID">
              <Text copyable={{ text: preview.metadata?.revision_id || '' }}>
                {preview.metadata?.revision_id || 'Unknown'}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Page ID">
              <Text copyable={{ text: preview.metadata?.page_id || '' }}>
                {preview.metadata?.page_id || 'Unknown'}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Content Chunks">
              {preview.metadata?.num_chunks || 0}
            </Descriptions.Item>
            <Descriptions.Item label="References">
              {preview.metadata?.num_references || 0}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="Extraction Information" style={{ marginBottom: 16 }}>
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Extraction Time">
              {safeFormatDate(preview.extraction_info?.timestamp)}
            </Descriptions.Item>
            <Descriptions.Item label="Processing Duration">
              {preview.extraction_info?.extraction_time || 0}s
            </Descriptions.Item>
            <Descriptions.Item label="Extractor Version">
              <Tag color="blue">{preview.extraction_info?.extractor_version || 'Unknown'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Discovery Depth">
              <Badge count={preview.extraction_info?.depth || 0} color="green" />
            </Descriptions.Item>
            <Descriptions.Item label="Parent Entity">
              {preview.extraction_info?.parent_qid ? (
                <Text code copyable={{ text: preview.extraction_info.parent_qid }}>
                  {preview.extraction_info.parent_qid}
                </Text>
              ) : (
                <Text type="secondary">Initial seed</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Queue Status">
              <Space>
                <Tag color={getQueueStatusColor(preview.relationships?.queue_status?.queue_type)}>
                  {preview.relationships?.queue_status?.queue_type || 'None'}
                </Tag>
                {preview.relationships?.queue_status?.priority && (
                  <Tag color={getPriorityColor(preview.relationships.queue_status.priority)}>
                    {getPriorityText(preview.relationships.queue_status.priority)}
                  </Tag>
                )}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title="Entity Relationships" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Statistic
                  title="Child Entities"
                  value={preview.relationships?.children_count || 0}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<NodeIndexOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Statistic
                  title="Same Depth"
                  value={preview.relationships?.same_depth_count || 0}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<TeamOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Statistic
                  title="Discovery Depth"
                  value={preview.extraction_info?.depth || 0}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<BranchesOutlined />}
                />
              </Card>
            </Col>
          </Row>
        </Card>

        {preview.categories && preview.categories.length > 0 && (
          <Card title={`Categories (${preview.metadata?.num_categories || 0})`}>
            <Space wrap>
              {preview.categories.map((category, index) => (
                <Tag
                  key={index}
                  color="purple"
                  style={{ marginBottom: 8 }}
                >
                  {category || 'Unknown Category'}
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        {preview.relationships?.queue_status?.notes && (
          <Card title="Queue Notes" style={{ marginTop: 16 }}>
            <Text italic>{preview.relationships.queue_status.notes}</Text>
          </Card>
        )}
      </div>
    )
  }

  const renderContent = () => {
    if (isLoading) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
          <Spin size="large" />
        </div>
      )
    }

    if (error) {
      return (
        <Alert
          message="Error Loading Preview"
          description="Could not load entity preview. Please try again."
          type="error"
          showIcon
          action={
            <Button size="small" onClick={() => window.location.reload()}>
              Retry
            </Button>
          }
        />
      )
    }

    if (!preview) {
      return (
        <Empty
          description="No entity data found"
          image={<DatabaseOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        />
      )
    }

    return (
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        tabBarExtraContent={
          <Space>
            <Text type="secondary">
              Last updated: {safeFromNow(preview.extraction_info?.timestamp)}
            </Text>
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={() => copyToClipboard(preview.qid)}
            >
              Copy QID
            </Button>
          </Space>
        }
      >
        <TabPane
          tab={<span><InfoCircleOutlined />Overview</span>}
          key="overview"
        >
          {renderOverviewTab()}
        </TabPane>

        <TabPane
          tab={<span><FileTextOutlined />Content</span>}
          key="content"
        >
          {renderContentTab()}
        </TabPane>

        <TabPane
          tab={
            <span>
              <BookOutlined />
              Infobox
              <Badge
                count={preview.infobox ? Object.keys(preview.infobox).length : 0}
                style={{ backgroundColor: '#52c41a', marginLeft: 4 }}
              />
            </span>
          }
          key="infobox"
        >
          {renderInfoboxTab()}
        </TabPane>

        <TabPane
          tab={
            <span>
              <LinkOutlined />
              Links
              <Badge
                count={(preview.links?.internal_count || 0) + (preview.links?.external_count || 0)}
                style={{ backgroundColor: '#1890ff', marginLeft: 4 }}
              />
            </span>
          }
          key="links"
        >
          {renderLinksTab()}
        </TabPane>

        <TabPane
          tab={
            <span>
              <TableOutlined />
              Tables
              <Badge
                count={preview.tables?.length || 0}
                style={{ backgroundColor: '#52c41a', marginLeft: 4 }}
              />
            </span>
          }
          key="tables"
        >
          {renderTablesTab()}
        </TabPane>

        <TabPane
          tab={
            <span>
              <PictureOutlined />
              Images
              <Badge
                count={preview.images?.length || 0}
                style={{ backgroundColor: '#faad14', marginLeft: 4 }}
              />
            </span>
          }
          key="images"
        >
          {renderImagesTab()}
        </TabPane>

        <TabPane
          tab={<span><HistoryOutlined />Metadata</span>}
          key="metadata"
        >
          {renderMetadataTab()}
        </TabPane>
      </Tabs>
    )
  }

  return (
    <Drawer
      title={
        <Space>
          <InfoCircleOutlined />
          <span>Entity Details</span>
          {preview && (
            <Space>
              <Badge count={preview.type || 'Unknown'} color="blue" />
              <Text type="secondary" style={{ fontSize: 12 }}>
                ({preview.qid || 'No QID'})
              </Text>
            </Space>
          )}
        </Space>
      }
      width="90%"
      open={open}
      onClose={onClose}
      destroyOnClose
      style={{
        paddingBottom: 0
      }}
      bodyStyle={{
        paddingBottom: 0
      }}
    >
      {renderContent()}
    </Drawer>
  )
}