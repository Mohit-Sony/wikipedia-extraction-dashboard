
// src/components/dashboard/TypeDistribution.tsx
import React from 'react'
import { Card, Typography } from 'antd'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { BarChartOutlined } from '@ant-design/icons'
import { TypeStats } from '../../types'

const { Title } = Typography

interface TypeDistributionProps {
  typeStats: TypeStats[]
}

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#722ed1', '#eb2f96', '#13c2c2']

export const TypeDistribution: React.FC<TypeDistributionProps> = ({ typeStats }) => {
  const data = typeStats.map((stat, index) => ({
    name: stat.type,
    value: stat.count,
    color: COLORS[index % COLORS.length]
  }))

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BarChartOutlined />
          <Title level={4} style={{ margin: 0 }}>Entity Types</Title>
        </div>
      }
      style={{ height: 400 }}
    >
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip 
            formatter={(value: number) => [value, 'Count']}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  )
}
