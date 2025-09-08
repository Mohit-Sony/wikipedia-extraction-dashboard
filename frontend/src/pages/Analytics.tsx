
// src/pages/Analytics.tsx
import React, { useState } from 'react'
import { Row, Col, Card, Typography, Select, Spin, Empty, Statistic, Progress } from 'antd'
import { 
  BarChartOutlined, 
  LineChartOutlined, 
  PieChartOutlined,
  TrophyOutlined,
  FundOutlined
} from '@ant-design/icons'
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts'
import {
  useGetExtractionTrendsQuery,
  useGetTypeAnalysisQuery,
  useGetDepthAnalysisQuery,
  useGetContentQualityMetricsQuery,
  useGetTopEntitiesQuery,
  useGetUserDecisionPatternsQuery
} from '../store/api'

const { Title, Text } = Typography
const { Option } = Select

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#722ed1', '#eb2f96', '#13c2c2', '#f5222d', '#fa8c16']

export const Analytics: React.FC = () => {
  const [topEntitiesMetric, setTopEntitiesMetric] = useState('num_links')
  const [trendDays, setTrendDays] = useState(30)

  const { data: extractionTrends, isLoading: trendsLoading } = useGetExtractionTrendsQuery({ days: trendDays })
  const { data: typeAnalysis, isLoading: typeLoading } = useGetTypeAnalysisQuery()
  const { data: depthAnalysis, isLoading: depthLoading } = useGetDepthAnalysisQuery()
  const { data: contentQuality, isLoading: qualityLoading } = useGetContentQualityMetricsQuery()
  const { data: topEntities, isLoading: topLoading } = useGetTopEntitiesQuery({
    metric: topEntitiesMetric,
    limit: 10
  })
  const { data: userDecisions, isLoading: decisionsLoading } = useGetUserDecisionPatternsQuery({ days: 30 })

  const renderChart = (title: string, loading: boolean, children: React.ReactNode, extra?: React.ReactNode) => (
    <Card 
      title={title} 
      extra={extra}
      style={{ height: 420 }}
      bodyStyle={{ padding: '20px 24px' }}
    >
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 320 }}>
          <Spin size="large" />
        </div>
      ) : (
        children
      )}
    </Card>
  )

  const formatTrendData = () => {
    if (!extractionTrends?.extractions) return []
    
    return extractionTrends.extractions.map((item: any) => ({
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      extractions: item.count,
      errors: extractionTrends.errors?.find((e: any) => e.date === item.date)?.count || 0
    }))
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            Analytics Dashboard
          </Title>
          <Text type="secondary">
            Comprehensive insights into your Wikipedia extraction pipeline
          </Text>
        </Col>
      </Row>

      {/* Key Metrics Overview */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Success Rate"
              value={typeAnalysis?.type_analysis ? 
                (typeAnalysis.type_analysis.reduce((acc: number, item: any) => acc + item.success_rate, 0) / typeAnalysis.type_analysis.length).toFixed(1)
                : 0
              }
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Links per Entity"
              value={typeAnalysis?.type_analysis ? 
                (typeAnalysis.type_analysis.reduce((acc: number, item: any) => acc + item.avg_links, 0) / typeAnalysis.type_analysis.length).toFixed(1)
                : 0
              }
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Page Length"
              value={typeAnalysis?.type_analysis ? 
                Math.round(typeAnalysis.type_analysis.reduce((acc: number, item: any) => acc + item.avg_page_length, 0) / typeAnalysis.type_analysis.length)
                : 0
              }
              suffix="chars"
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Entity Types"
              value={typeAnalysis?.type_analysis?.length || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Extraction Trends */}
        <Col xs={24} lg={12}>
          {renderChart(
            "Extraction Trends",
            trendsLoading,
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={formatTrendData()}>
                <defs>
                  <linearGradient id="colorExtractions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1890ff" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#1890ff" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area 
                  type="monotone" 
                  dataKey="extractions" 
                  stroke="#1890ff" 
                  fillOpacity={1} 
                  fill="url(#colorExtractions)"
                  name="Successful Extractions"
                />
                <Line 
                  type="monotone" 
                  dataKey="errors" 
                  stroke="#ff4d4f" 
                  strokeWidth={2}
                  name="Errors"
                />
              </AreaChart>
            </ResponsiveContainer>,
            <Select
              value={trendDays}
              onChange={setTrendDays}
              style={{ width: 100 }}
            >
              <Option value={7}>7 days</Option>
              <Option value={14}>14 days</Option>
              <Option value={30}>30 days</Option>
            </Select>
          )}
        </Col>

        {/* Entity Types Distribution */}
        <Col xs={24} lg={12}>
          {renderChart(
            "Entity Types Distribution",
            typeLoading,
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={typeAnalysis?.type_analysis || []}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  dataKey="total_count"
                  nameKey="type"
                  label={({ type, percent }) => `${type} (${(percent * 100).toFixed(0)}%)`}
                >
                  {(typeAnalysis?.type_analysis || []).map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number, name: string) => [value, `${name} entities`]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Col>

        {/* Depth Analysis */}
        <Col xs={24} lg={12}>
          {renderChart(
            "Extraction Depth Distribution",
            depthLoading,
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={depthAnalysis?.depth_analysis || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="depth" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#1890ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Col>

        {/* Content Quality Metrics */}
        <Col xs={24} lg={12}>
          {renderChart(
            "Content Quality Breakdown",
            qualityLoading,
            contentQuality ? (
              <div style={{ padding: 20 }}>
                <div style={{ marginBottom: 20 }}>
                  <Text strong>Entities with Tables</Text>
                  <Progress 
                    percent={contentQuality.content_richness?.table_percentage || 0} 
                    strokeColor="#52c41a"
                    style={{ marginTop: 8 }}
                  />
                </div>
                <div style={{ marginBottom: 20 }}>
                  <Text strong>Entities with Images</Text>
                  <Progress 
                    percent={contentQuality.content_richness?.image_percentage || 0} 
                    strokeColor="#1890ff"
                    style={{ marginTop: 8 }}
                  />
                </div>
                <div style={{ marginBottom: 20 }}>
                  <Text strong>Well Structured Entities</Text>
                  <Progress 
                    percent={contentQuality.content_richness?.structure_percentage || 0} 
                    strokeColor="#722ed1"
                    style={{ marginTop: 8 }}
                  />
                </div>
                <Row gutter={16} style={{ marginTop: 24 }}>
                  <Col span={8}>
                    <Statistic
                      title="With Tables"
                      value={contentQuality.content_richness?.entities_with_tables || 0}
                      valueStyle={{ fontSize: 18, color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="With Images"
                      value={contentQuality.content_richness?.entities_with_images || 0}
                      valueStyle={{ fontSize: 18, color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Well Structured"
                      value={contentQuality.content_richness?.well_structured_entities || 0}
                      valueStyle={{ fontSize: 18, color: '#722ed1' }}
                    />
                  </Col>
                </Row>
              </div>
            ) : (
              <Empty description="No content quality data available" />
            )
          )}
        </Col>

        {/* Top Entities */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <TrophyOutlined />
                <span>Top Performing Entities</span>
              </div>
            }
            extra={
              <Select
                value={topEntitiesMetric}
                onChange={setTopEntitiesMetric}
                style={{ width: 140 }}
              >
                <Option value="num_links">By Links</Option>
                <Option value="page_length">By Page Length</Option>
                <Option value="num_tables">By Tables</Option>
                <Option value="num_images">By Images</Option>
              </Select>
            }
            style={{ height: 420 }}
          >
            {topLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 50 }}>
                <Spin />
              </div>
            ) : (
              <div style={{ maxHeight: 320, overflow: 'auto' }}>
                {topEntities?.top_entities?.map((entity: any, index: number) => (
                  <div key={entity.qid} style={{ 
                    padding: '12px 0', 
                    borderBottom: index < topEntities.top_entities.length - 1 ? '1px solid #f5f5f5' : 'none',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, fontSize: 14 }}>{entity.title}</div>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                        {entity.type} • {entity.qid}
                      </div>
                    </div>
                    <div style={{ 
                      fontSize: 18, 
                      fontWeight: 'bold', 
                      color: COLORS[index % COLORS.length],
                      minWidth: 60,
                      textAlign: 'right'
                    }}>
                      {typeof entity[topEntitiesMetric] === 'number' && topEntitiesMetric === 'page_length' 
                        ? `${(entity[topEntitiesMetric] / 1000).toFixed(1)}K`
                        : entity[topEntitiesMetric]
                      }
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>

        {/* User Decision Patterns */}
        <Col xs={24} lg={12}>
          {renderChart(
            "User Decision Patterns (30 days)",
            decisionsLoading,
            userDecisions ? (
              <div>
                <Row gutter={16} style={{ marginBottom: 20 }}>
                  <Col span={12}>
                    <Card size="small">
                      <Statistic
                        title="Most Approved Type"
                        value={userDecisions.most_approved_types?.[0]?.type || 'N/A'}
                        valueStyle={{ fontSize: 16, color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card size="small">
                      <Statistic
                        title="Most Rejected Type"
                        value={userDecisions.most_rejected_types?.[0]?.type || 'N/A'}
                        valueStyle={{ fontSize: 16, color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                </Row>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={userDecisions.decision_types || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="type" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#faad14" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <Empty description="No decision pattern data available" />
            )
          )}
        </Col>
      </Row>
    </div>
  )
}