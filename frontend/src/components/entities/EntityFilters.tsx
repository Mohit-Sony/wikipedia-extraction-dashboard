
// src/components/entities/EntityFilters.tsx
import React from 'react'
import { Drawer, Form, Input, Select, Button, Space, Typography, Divider } from 'antd'
import { useSelector, useDispatch } from 'react-redux'
import { selectFilters, updateFilters, resetFilters } from '../../store/slices/uiSlice'
import { EntityStatus, QueueType } from '../../types'

const { Option } = Select
const { Title } = Typography

interface EntityFiltersProps {
  open: boolean
  onClose: () => void
}

export const EntityFilters: React.FC<EntityFiltersProps> = ({ open, onClose }) => {
  const dispatch = useDispatch()
  const filters = useSelector(selectFilters)
  const [form] = Form.useForm()

  const handleApplyFilters = async () => {
    try {
      const values = await form.validateFields()
      dispatch(updateFilters(values))
      onClose()
    } catch (error) {
      console.error('Filter validation failed:', error)
    }
  }

  const handleResetFilters = () => {
    form.resetFields()
    dispatch(resetFilters())
  }

  return (
    <Drawer
      title="Advanced Filters"
      width={400}
      open={open}
      onClose={onClose}
      footer={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Button onClick={handleResetFilters}>
            Reset All
          </Button>
          <Space>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="primary" onClick={handleApplyFilters}>
              Apply Filters
            </Button>
          </Space>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={filters}
      >
        <Title level={5}>Basic Filters</Title>
        
        <Form.Item label="Search" name="search">
          <Input placeholder="Search titles, QIDs, descriptions..." />
        </Form.Item>

        <Form.Item label="Entity Types" name="types">
          <Select mode="multiple" placeholder="Select types">
            <Option value="human">Human</Option>
            <Option value="place">Place</Option>
            <Option value="organization">Organization</Option>
            <Option value="event">Event</Option>
            <Option value="concept">Concept</Option>
          </Select>
        </Form.Item>

        <Form.Item label="Status" name="status">
          <Select mode="multiple" placeholder="Select statuses">
            {Object.values(EntityStatus).map(status => (
              <Option key={status} value={status}>{status}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item label="Queue Type" name="queue_type">
          <Select mode="multiple" placeholder="Select queue types">
            {Object.values(QueueType).map(type => (
              <Option key={type} value={type}>{type.replace('_', ' ')}</Option>
            ))}
          </Select>
        </Form.Item>

        <Divider />

        <Title level={5}>Numeric Filters</Title>

        <Form.Item label="Number of Links">
          <Input.Group compact>
            <Form.Item name="links_min" style={{ width: '50%', marginBottom: 0 }}>
              <Input placeholder="Min" type="number" />
            </Form.Item>
            <Form.Item name="links_max" style={{ width: '50%', marginBottom: 0 }}>
              <Input placeholder="Max" type="number" />
            </Form.Item>
          </Input.Group>
        </Form.Item>

        <Form.Item label="Page Length">
          <Input.Group compact>
            <Form.Item name="page_length_min" style={{ width: '50%', marginBottom: 0 }}>
              <Input placeholder="Min characters" type="number" />
            </Form.Item>
            <Form.Item name="page_length_max" style={{ width: '50%', marginBottom: 0 }}>
              <Input placeholder="Max characters" type="number" />
            </Form.Item>
          </Input.Group>
        </Form.Item>

        <Form.Item label="Extraction Depth">
          <Input.Group compact>
            <Form.Item name="depth_min" style={{ width: '50%', marginBottom: 0 }}>
              <Input placeholder="Min depth" type="number" />
            </Form.Item>
            <Form.Item name="depth_max" style={{ width: '50%', marginBottom: 0 }}>
              <Input placeholder="Max depth" type="number" />
            </Form.Item>
          </Input.Group>
        </Form.Item>

        <Form.Item label="Parent QID" name="parent_qid">
          <Input placeholder="Filter by parent entity QID" />
        </Form.Item>
      </Form>
    </Drawer>
  )
}