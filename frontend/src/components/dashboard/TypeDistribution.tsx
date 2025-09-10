import React, { useState } from 'react'
import { Card, Typography, Button } from 'antd'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { BarChartOutlined } from '@ant-design/icons'
import { TypeStats } from '../../types'

const { Title } = Typography

interface TypeDistributionProps {
  typeStats: TypeStats[]
}

const COLORS = [
  '#1890ff', '#52c41a', '#faad14', '#722ed1', '#eb2f96',
  '#13c2c2', '#ff7875', '#a0d911', '#722ed1', '#ffc53d'
]

export const TypeDistribution: React.FC<TypeDistributionProps> = ({ typeStats }) => {
  const [showAll, setShowAll] = useState(false)

  // sort by count (descending)
  const sortedData = [...typeStats].sort((a, b) => b.count - a.count)

  let displayData
  if (showAll) {
    // show all as-is
    displayData = sortedData.map((stat, index) => ({
      name: stat.type,
      value: stat.count,
      color: COLORS[index % COLORS.length],
    }))
  } else {
    // take top 30
    const top30 = sortedData.slice(0, 30)
    const others = sortedData.slice(30)

    const aggregated = {
      name: 'Others',
      value: others.reduce((sum, s) => sum + s.count, 0),
      color: '#d9d9d9', // grey for "Others"
    }

    displayData = [
      ...top30.map((stat, index) => ({
        name: stat.type,
        value: stat.count,
        color: COLORS[index % COLORS.length],
      })),
      ...(others.length ? [aggregated] : []),
    ]
  }

  return (
    <Card
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BarChartOutlined />
          <Title level={4} style={{ margin: 0 }}>
            Entity Types {showAll ? '' : '(Top 30 + Others)'}
          </Title>
        </div>
      }
      style={{ height: 750 }}
      extra={
        <Button type="link" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show Top 30' : 'Show All'}
        </Button>
      }
    >
      <ResponsiveContainer width="100%" height={600}>
        <PieChart>
          <Pie
            data={displayData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={120}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(1)}%)`
            }
          >
            {displayData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number, name: string) => [`${value}`, name]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  )
}