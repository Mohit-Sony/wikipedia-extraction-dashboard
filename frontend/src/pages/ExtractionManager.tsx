// src/pages/ExtractionManager.tsx
import React, { useState } from 'react'
import { Row, Col, Typography, Tabs, Button, Space, Card, Statistic } from 'antd'
import {
  RocketOutlined,
  MonitorOutlined,
  ControlOutlined,
  PlusOutlined,
  FilterOutlined,
  BarChartOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import { ExtractionMonitor } from '../components/extraction/ExtractionMonitor'
import { ExtractionControls } from '../components/extraction/ExtractionControls'
import { ManualEntityEntry } from '../components/extraction/ManualEntityEntry'
import { ReviewQueue } from '../components/queues/ReviewQueue'
import {
  useGetExtractionStatusQuery,
  useGetQueueEntitiesQuery,
  useGetDeduplicationStatsQuery
} from '../store/api'
import { QueueType, ExtractionStatus } from '../types'

const { Title, Text } = Typography
const { TabPane } = Tabs

export const ExtractionManager: React.FC = () => {
  const [activeTab, setActiveTab] = useState('monitor')

  const { data: extractionStatus, refetch: refetchStatus } = useGetExtractionStatusQuery()
  const { data: reviewQueueData } = useGetQueueEntitiesQuery({
    queue_type: QueueType.REVIEW,
    limit: 1 // Just for count
  })
  const { data: activeQueueData } = useGetQueueEntitiesQuery({
    queue_type: QueueType.ACTIVE,
    limit: 1 // Just for count
  })
  const { data: dedupStats } = useGetDeduplicationStatsQuery()

  const status = extractionStatus?.status || ExtractionStatus.IDLE
  const session = extractionStatus
  // const progress = extractionStatus?.progress

  const getStatusColor = (status: ExtractionStatus) => {
    switch (status) {
      case ExtractionStatus.RUNNING:
        return '#52c41a'
      case ExtractionStatus.PAUSED:
        return '#faad14'
      case ExtractionStatus.ERROR:
        return '#ff4d4f'
      case ExtractionStatus.COMPLETED:
        return '#1890ff'
      default:
        return '#666'
    }
  }

  return (
    <div>
      {/* Page Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }}>
            <Space>
              <RocketOutlined />
              Extraction Manager
            </Space>
          </Title>
          <Text type="secondary">
            Monitor and control Wikipedia data extraction pipeline
          </Text>
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetchStatus()}
          >
            Refresh Status
          </Button>
        </Col>
      </Row>

      {/* Quick Stats Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Extraction Status"
              value={status.toUpperCase()}
              valueStyle={{ color: getStatusColor(status), fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Review Queue"
              value={reviewQueueData?.total || 0}
              valueStyle={{ color: '#722ed1', fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Queue"
              value={activeQueueData?.total || 0}
              valueStyle={{ color: '#1890ff', fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Dedup Efficiency"
              value={dedupStats ? Math.round(dedupStats.deduplication_rate * 100) : 0}
              suffix="%"
              valueStyle={{ color: '#52c41a', fontSize: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        size="large"
        type="card"
      >
        <TabPane
          tab={
            <Space>
              <MonitorOutlined />
              Extraction Monitor
            </Space>
          }
          key="monitor"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={16}>
              <ExtractionMonitor />
            </Col>
            <Col xs={24} lg={8}>
              <ExtractionControls />
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <Space>
              <ControlOutlined />
              Extraction Controls
            </Space>
          }
          key="controls"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <ExtractionControls />
            </Col>
            <Col xs={24} lg={12}>
              <Card
                title="Current Session Info"
                style={{ height: 600 }}
              >
                {session ? (
                  <div>
                    <Title level={5}>{`Session #${session.session_id}`}</Title>

                    {session.start_time && (
                      <Text type="secondary">
                        Started: {new Date(session.start_time).toLocaleString()}
                      </Text>
                    )}

                    <Row gutter={16} style={{ marginTop: 20 }}>
                      <Col span={12}>
                        <Statistic
                          title="Extracted"
                          value={session.processed_entities ?? 0}
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="Errors"
                          value={session.failed_entities ?? 0}
                          valueStyle={{ color: '#ff4d4f' }}
                        />
                      </Col>
                    </Row>

                    {/* Show progress only when extraction is running */}
                    {session ? (
                      <div>
                        <Title level={5}>
                          {session.session_id ? `Session #${session.session_id}` : 'No Active Session'}
                        </Title>

                        {session.start_time && (
                          <Text type="secondary">
                            Started: {new Date(session.start_time).toLocaleString()}
                          </Text>
                        )}

                        <Row gutter={16} style={{ marginTop: 20 }}>
                          <Col span={12}>
                            <Statistic
                              title="Processed"
                              value={session.processed_entities ?? 0}
                              valueStyle={{ color: '#1890ff' }}
                            />
                          </Col>
                          <Col span={12}>
                            <Statistic
                              title="Failed"
                              value={session.failed_entities ?? 0}
                              valueStyle={{ color: '#ff4d4f' }}
                            />
                          </Col>
                        </Row>

                        <Row gutter={16} style={{ marginTop: 20 }}>
                          <Col span={12}>
                            <Statistic
                              title="Skipped"
                              value={session.skipped_entities ?? 0}
                              valueStyle={{ color: '#faad14' }}
                            />
                          </Col>
                          <Col span={12}>
                            <Statistic
                              title="Discovered"
                              value={session.discovered_entities ?? 0}
                              valueStyle={{ color: '#52c41a' }}
                            />
                          </Col>
                        </Row>

                        {session.status === 'running' && (
                          <div style={{ marginTop: 20 }}>
                            <Title level={5}>Current Progress</Title>

                            <Text>
                              Processing: {session.current_entity ?? '—'}
                            </Text>
                            <br />

                            <Text type="secondary">
                              Progress: {session.progress_percentage?.toFixed(2) ?? 0}% |{' '}
                              Total: {session.total_entities ?? 0} |{' '}
                              Processed: {session.processed_entities ?? 0}
                            </Text>

                            {session.estimated_completion && (
                              <>
                                <br />
                                <Text type="secondary">
                                  ETA: {new Date(session.estimated_completion).toLocaleTimeString()}
                                </Text>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <Text type="secondary">No session data available</Text>
                    )}
                  </div>
                ) : (
                  <Text type="secondary">No active session</Text>
                )}
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <Space>
              <PlusOutlined />
              Manual Entry
            </Space>
          }
          key="manual"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <ManualEntityEntry />
            </Col>
            <Col xs={24} lg={12}>
              <Card
                title="Quick Tips"
                style={{ height: 600 }}
              >
                <div>
                  <Title level={5}>How to Add Entities</Title>
                  <ul>
                    <li>Enter exact Wikipedia page titles</li>
                    <li>Use search suggestions for accuracy</li>
                    <li>QID is optional - auto-detected</li>
                    <li>Entities go to review queue first</li>
                  </ul>

                  <Title level={5}>Entity Types</Title>
                  <ul>
                    <li><strong>Human:</strong> People, biographical entries</li>
                    <li><strong>Place:</strong> Geographic locations</li>
                    <li><strong>Organization:</strong> Companies, institutions</li>
                    <li><strong>Event:</strong> Historical events, occurrences</li>
                    <li><strong>Concept:</strong> Abstract ideas, theories</li>
                  </ul>

                  <Title level={5}>Priority Guidelines</Title>
                  <ul>
                    <li><strong>High:</strong> Urgent or important entities</li>
                    <li><strong>Medium:</strong> Standard processing</li>
                    <li><strong>Low:</strong> Can wait, lower importance</li>
                  </ul>
                </div>
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane
          tab={
            <Space>
              <FilterOutlined />
              Review Queue
            </Space>
          }
          key="review"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={18}>
              <ReviewQueue />
            </Col>
            {/* <Col xs={24} lg={6}>
              <DiscoverySourceFilter
                selectedSource={discoverySourceFilter}
                onSourceSelect={setDiscoverySourceFilter}
              />
            </Col> */}
          </Row>
        </TabPane>

        <TabPane
          tab={
            <Space>
              <BarChartOutlined />
              Statistics
            </Space>
          }
          key="stats"
        >
          {/* <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="Deduplication Statistics">
                {dedupStats ? (
                  <div>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic
                          title="Total Discovered"
                          value={dedupStats.total_discovered}
                          valueStyle={{ color: '#1890ff' }}
                        />
                      </Col>
                      <Col span={12}>
                        <Statistic
                          title="Duplicates Filtered"
                          value={dedupStats.total_duplicates}
                          valueStyle={{ color: '#faad14' }}
                        />
                      </Col>
                    </Row>
                    
                    <div style={{ marginTop: 20 }}>
                      <Title level={5}>Duplicates by Status</Title>
                      <Row gutter={8}>
                        <Col span={6}>
                          <Text>Completed: {dedupStats.duplicates_by_status.completed}</Text>
                        </Col>
                        <Col span={6}>
                          <Text>Rejected: {dedupStats.duplicates_by_status.rejected}</Text>
                        </Col>
                        <Col span={6}>
                          <Text>In Queue: {dedupStats.duplicates_by_status.in_queue}</Text>
                        </Col>
                        <Col span={6}>
                          <Text>Processing: {dedupStats.duplicates_by_status.processing}</Text>
                        </Col>
                      </Row>
                    </div>

                    <div style={{ marginTop: 20 }}>
                      <Title level={5}>Discovery Sources</Title>
                      {Object.entries(dedupStats.discovery_sources).map(([source, count]) => (
                        <div key={source} style={{ marginBottom: 8 }}>
                          <Text>{source.replace('_', ' ')}: {count}</Text>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <Text type="secondary">No deduplication statistics available</Text>
                )}
              </Card>
            </Col>
            
            <Col xs={24} lg={12}>
              <Card title="Queue Statistics">
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="Review Queue"
                      value={reviewQueueData?.total || 0}
                      valueStyle={{ color: '#722ed1' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="Active Queue"
                      value={activeQueueData?.total || 0}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                </Row>

                {session && (
                  <div style={{ marginTop: 20 }}>
                    <Title level={5}>Current Session</Title>
                    <Text>Name: {session.session_name}</Text>
                    <br />
                    <Text>Status: {status}</Text>
                    <br />
                    <Text>Extracted: {session.total_extracted}</Text>
                    <br />
                    <Text>Errors: {session.total_errors}</Text>
                  </div>
                )}
              </Card>
            </Col>
          </Row> */}
        </TabPane>
      </Tabs>
    </div>
  )
}