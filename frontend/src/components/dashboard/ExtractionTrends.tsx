
// src/components/dashboard/ExtractionTrends.tsx
import React from 'react'
import { Card, Typography, Spin } from 'antd'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrademarkCircleTwoTone } from '@ant-design/icons'
import { useGetExtractionTrendsQuery } from '../../store/api'

const { Title  } = Typography

export const ExtractionTrends: React.FC = () => {
  const { data, isLoading } = useGetExtractionTrendsQuery({ days: 14 })

  if (isLoading) {
    return (
      <Card title="Extraction Trends" style={{ height: 400 }}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  const chartData = data?.extractions?.map((item: any) => ({
    date: new Date(item.date).toLocaleDateString(),
    extractions: item.count,
    errors: data.errors?.find((e: any) => e.date === item.date)?.count || 0
  })) || []

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrademarkCircleTwoTone />
          <Title level={4} style={{ margin: 0 }}>Extraction Trends (14 days)</Title>
        </div>
      }
      style={{ height: 400 }}
    >
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line 
            type="monotone" 
            dataKey="extractions" 
            stroke="#1890ff" 
            strokeWidth={2}
            name="Successful Extractions"
          />
          <Line 
            type="monotone" 
            dataKey="errors" 
            stroke="#ff4d4f" 
            strokeWidth={2}
            name="Errors"
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
