// src/components/entities/EntityPreviewDrawer.tsx
import React from 'react'
import { Drawer, Spin, Alert, Typography, Descriptions, Tag, Card, Row, Col, Space } from 'antd'
import { useGetEntityPreviewQuery } from '../../store/api'
// import { Entity } from '../../types'

const { Title, Paragraph, Text } = Typography

interface EntityPreviewDrawerProps {
  qid: string | null
  open: boolean
  onClose: () => void
}

export const EntityPreviewDrawer: React.FC<EntityPreviewDrawerProps> = ({ qid, open, onClose }) => {
  const { data: preview, isLoading, error } = useGetEntityPreviewQuery(qid!, {
    skip: !qid || !open
  })

  const renderContent = () => {
    if (isLoading) {
      return (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 50 }}>
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
        />
      )
    }

    if (!preview) {
      return null
    }

    return (
      <div>
        {/* Header */}
        <div style={{ padding: 24, borderBottom: '1px solid #f0f0f0', background: '#fafafa' }}>
          <Title level={3} style={{ margin: 0, marginBottom: 8 }}>
            {preview.title}
          </Title>
          <Space>
            <Tag color="blue">{preview.type}</Tag>
            <Text code>{preview.qid}</Text>
          </Space>
          {preview.content.description && (
            <Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
              {preview.content.description}
            </Paragraph>
          )}
        </div>

        {/* Content */}
        <div style={{ padding: 24 }}>
          {/* Statistics */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#1890ff' }}>
                  {preview.links.internal_count}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>Internal Links</div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#52c41a' }}>
                  {preview.metadata.num_tables}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>Tables</div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#faad14' }}>
                  {preview.metadata.num_images}
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>Images</div>
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: '#722ed1' }}>
                  {(preview.metadata.page_length / 1000).toFixed(1)}K
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>Characters</div>
              </Card>
            </Col>
          </Row>

          {/* Extract */}
          {preview.content.extract && (
            <Card title="Content Extract" style={{ marginBottom: 24 }}>
              <Paragraph>
                {preview.content.extract}
              </Paragraph>
            </Card>
          )}

          {/* Infobox */}
          {Object.keys(preview.infobox).length > 0 && (
            <Card title="Infobox Data" style={{ marginBottom: 24 }}>
              <Descriptions column={1} size="small" bordered>
                {Object.entries(preview.infobox).slice(0, 10).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key}>
                    {String(value)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          )}

          {/* Sample Links */}
          {preview.links.sample_internal.length > 0 && (
            <Card title="Sample Internal Links">
              <div style={{ maxHeight: 200, overflow: 'auto' }}>
                {preview.links.sample_internal.map((link, index) => (
                  <div key={index} style={{ padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <div style={{ fontWeight: 500 }}>{link.title}</div>
                    <Space>
                      <Text code style={{ fontSize: 12 }}>{link.qid}</Text>
                      <Tag >{link.type}</Tag>
                    </Space>
                    {link.shortDesc && (
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {link.shortDesc}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    )
  }

  return (
    <Drawer
      title="Entity Preview"
      width={600}
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      {renderContent()}
    </Drawer>
  )
}
