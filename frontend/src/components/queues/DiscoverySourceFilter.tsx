// src/components/queues/DiscoverySourceFilter.tsx
import React from 'react'
import { 
  Card, 
  Tag, 
  Space, 
  Typography, 
  Row, 
  Col, 
  Statistic,
  Tooltip,
  Button,
  Divider
} from 'antd'
import {
  RobotOutlined,
  UserOutlined,
  SearchOutlined,
  ReloadOutlined,
  FilterOutlined,
  ClearOutlined
} from '@ant-design/icons'
import { useGetReviewQueueSourcesQuery } from '../../store/api'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const { Title, Text } = Typography

interface DiscoverySourceFilterProps {
  selectedSource?: string
  onSourceSelect: (source: string | undefined) => void
}

export const DiscoverySourceFilter: React.FC<DiscoverySourceFilterProps> = ({
  selectedSource,
  onSourceSelect
}) => {
  const { data: sourcesData, isLoading, refetch } = useGetReviewQueueSourcesQuery()

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'extraction_pipeline':
        return <RobotOutlined />
      case 'manual_entry':
        return <UserOutlined />
      case 'batch_import':
        return <SearchOutlined />
      case 'api_integration':
        return <SearchOutlined />
      default:
        return <SearchOutlined />
    }
  }

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'extraction_pipeline':
        return '#1890ff'
      case 'manual_entry':
        return '#52c41a'
      case 'batch_import':
        return '#faad14'
      case 'api_integration':
        return '#722ed1'
      default:
        return '#666'
    }
  }

  const getSourceDescription = (source: string) => {
    switch (source) {
      case 'extraction_pipeline':
        return 'Entities discovered automatically during Wikipedia extraction'
      case 'manual_entry':
        return 'Entities added manually through the dashboard'
      case 'batch_import':
        return 'Entities imported from external sources in batches'
      case 'api_integration':
        return 'Entities discovered through API integrations'
      default:
        return 'Unknown discovery source'
    }
  }

  const formatSourceName = (source: string) => {
    return source
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const totalEntities = sourcesData?.sources.reduce((sum, source) => sum + source.count, 0) || 0

  return (
    <Card 
      title={
        <Space>
          <FilterOutlined />
          <Title level={5} style={{ margin: 0 }}>Discovery Sources</Title>
        </Space>
      }
      size="small"
      extra={
        <Space>
          {selectedSource && (
            <Button 
              size="small" 
              icon={<ClearOutlined />}
              onClick={() => onSourceSelect(undefined)}
            >
              Clear Filter
            </Button>
          )}
          <Button 
            size="small" 
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            loading={isLoading}
          />
        </Space>
      }
    >
      {/* Summary Statistics */}
      <Row gutter={8} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Statistic
            title="Total Sources"
            value={sourcesData?.sources.length || 0}
            valueStyle={{ fontSize: 16 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Total Entities"
            value={totalEntities}
            valueStyle={{ fontSize: 16 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Active Filter"
            value={selectedSource ? 1 : 0}
            valueStyle={{ fontSize: 16 }}
          />
        </Col>
      </Row>

      <Divider style={{ margin: '12px 0' }} />

      {/* Source Filters */}
      <div>
        <Text strong style={{ marginBottom: 8, display: 'block' }}>
          Filter by Source:
        </Text>
        
        {sourcesData?.sources && sourcesData.sources.length > 0 ? (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {sourcesData.sources
              .sort((a, b) => b.count - a.count) // Sort by count descending
              .map(source => {
                const isSelected = selectedSource === source.source
                const percentage = totalEntities > 0 
                  ? Math.round((source.count / totalEntities) * 100) 
                  : 0

                return (
                  <Tooltip
                    key={source.source}
                    title={
                      <div>
                        <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                          {formatSourceName(source.source)}
                        </div>
                        <div style={{ marginBottom: 4 }}>
                          {getSourceDescription(source.source)}
                        </div>
                        <div style={{ fontSize: 12 }}>
                          Last discovery: {dayjs(source.last_discovery).fromNow()}
                        </div>
                      </div>
                    }
                  >
                    <div
                      style={{
                        padding: 8,
                        border: `1px solid ${isSelected ? getSourceColor(source.source) : '#d9d9d9'}`,
                        borderRadius: 6,
                        backgroundColor: isSelected ? `${getSourceColor(source.source)}10` : 'transparent',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                      onClick={() => onSourceSelect(isSelected ? undefined : source.source)}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = getSourceColor(source.source)
                          e.currentTarget.style.backgroundColor = `${getSourceColor(source.source)}05`
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = '#d9d9d9'
                          e.currentTarget.style.backgroundColor = 'transparent'
                        }
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Space>
                          <span style={{ color: getSourceColor(source.source) }}>
                            {getSourceIcon(source.source)}
                          </span>
                          <Text strong style={{ fontSize: 13 }}>
                            {formatSourceName(source.source)}
                          </Text>
                        </Space>
                        <Space>
                          <Tag 
                            color={isSelected ? getSourceColor(source.source) : 'default'}
                            style={{ margin: 0 }}
                          >
                            {source.count}
                          </Tag>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {percentage}%
                          </Text>
                        </Space>
                      </div>
                      
                      {/* Progress bar */}
                      <div style={{ marginTop: 6 }}>
                        <div 
                          style={{
                            height: 3,
                            backgroundColor: '#f0f0f0',
                            borderRadius: 2,
                            overflow: 'hidden'
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${percentage}%`,
                              backgroundColor: getSourceColor(source.source),
                              transition: 'width 0.3s ease'
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </Tooltip>
                )
              })}
          </Space>
        ) : (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Text type="secondary">
              {isLoading ? 'Loading sources...' : 'No discovery sources found'}
            </Text>
          </div>
        )}
      </div>

      {/* Filter Info */}
      {selectedSource && (
        <div style={{ marginTop: 16, padding: 8, backgroundColor: '#f5f5f5', borderRadius: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <FilterOutlined /> Filtering by: <Text strong>{formatSourceName(selectedSource)}</Text>
          </Text>
        </div>
      )}
    </Card>
  )
}