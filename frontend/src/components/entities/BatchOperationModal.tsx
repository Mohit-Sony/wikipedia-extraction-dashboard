
// src/components/entities/BatchOperationModal.tsx
import React, { useState } from 'react'
import { Modal, Form, Select, Input, Button, Alert } from 'antd'
import { QueueType, Priority } from '../../types'

const { Option } = Select
const { TextArea } = Input
// const { Text } = Typography

interface BatchOperationModalProps {
  open: boolean
  selectedCount: number
  onConfirm: (operation: any) => void
  onCancel: () => void
}

export const BatchOperationModal: React.FC<BatchOperationModalProps> = ({
  open,
  selectedCount,
  onConfirm,
  onCancel
}) => {
  const [form] = Form.useForm()
  const [operation, setOperation] = useState<string>('move')

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      onConfirm({
        operation,
        target_queue: values.target_queue,
        priority: values.priority,
        notes: values.notes
      })
      form.resetFields()
      onCancel()
    } catch (error) {
      console.error('Form validation failed:', error)
    }
  }

  return (
    <Modal
      title="Batch Operation"
      open={open}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          Cancel
        </Button>,
        <Button key="submit" type="primary" onClick={handleSubmit}>
          Apply to {selectedCount} entities
        </Button>
      ]}
    >
      <Alert
        message={`${selectedCount} entities selected`}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Form form={form} layout="vertical">
        <Form.Item
          label="Operation"
          name="operation"
          initialValue="move"
        >
          <Select onChange={setOperation}>
            <Option value="move">Move to Queue</Option>
            <Option value="update_priority">Update Priority</Option>
            <Option value="delete">Remove from Queue</Option>
          </Select>
        </Form.Item>

        {operation === 'move' && (
          <Form.Item
            label="Target Queue"
            name="target_queue"
            rules={[{ required: true, message: 'Please select a target queue' }]}
          >
            <Select placeholder="Select queue">
              <Option value={QueueType.ACTIVE}>Active</Option>
              <Option value={QueueType.REJECTED}>Rejected</Option>
              <Option value={QueueType.ON_HOLD}>On Hold</Option>
              <Option value={QueueType.COMPLETED}>Completed</Option>
            </Select>
          </Form.Item>
        )}

        {(operation === 'move' || operation === 'update_priority') && (
          <Form.Item label="Priority" name="priority">
            <Select placeholder="Select priority">
              <Option value={Priority.HIGH}>High</Option>
              <Option value={Priority.MEDIUM}>Medium</Option>
              <Option value={Priority.LOW}>Low</Option>
            </Select>
          </Form.Item>
        )}

        <Form.Item label="Notes" name="notes">
          <TextArea 
            placeholder="Optional notes for this operation"
            rows={3}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
