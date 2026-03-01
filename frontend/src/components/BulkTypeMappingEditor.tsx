// frontend/src/components/BulkTypeMappingEditor.tsx
import React, { useState } from 'react';
import {
  Table,
  Button,
  Input,
  Select,
  Space,
  Typography,
  Popconfirm,
  Tag,
  Tooltip
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;
const { Option } = Select;

interface MappingRow {
  key: string;
  wikidata_type: string;
  mapped_type: string;
  wikidata_qid?: string;
  notes?: string;
  status: 'valid' | 'invalid' | 'empty';
  error?: string;
}

interface BulkTypeMappingEditorProps {
  approvedTypes: string[];
  onMappingsChange: (mappings: MappingRow[]) => void;
  getTypeColor: (type: string) => string;
}

const BulkTypeMappingEditor: React.FC<BulkTypeMappingEditorProps> = ({
  approvedTypes,
  onMappingsChange,
  getTypeColor,
}) => {
  const [mappings, setMappings] = useState<MappingRow[]>([
    {
      key: '1',
      wikidata_type: '',
      mapped_type: 'person',
      wikidata_qid: '',
      notes: '',
      status: 'empty',
    },
  ]);

  const validateRow = (row: MappingRow): MappingRow => {
    if (!row.wikidata_type || row.wikidata_type.trim() === '') {
      return { ...row, status: 'empty', error: undefined };
    }

    if (!approvedTypes.includes(row.mapped_type)) {
      return { ...row, status: 'invalid', error: 'Invalid mapped type' };
    }

    return { ...row, status: 'valid', error: undefined };
  };

  const updateMapping = (key: string, field: keyof MappingRow, value: any) => {
    const newMappings = mappings.map((mapping) => {
      if (mapping.key === key) {
        const updated = { ...mapping, [field]: value };
        return validateRow(updated);
      }
      return mapping;
    });
    setMappings(newMappings);
    onMappingsChange(newMappings);
  };

  const addRow = () => {
    const newKey = String(Date.now());
    const newMappings = [
      ...mappings,
      {
        key: newKey,
        wikidata_type: '',
        mapped_type: 'person',
        wikidata_qid: '',
        notes: '',
        status: 'empty' as const,
      },
    ];
    setMappings(newMappings);
    onMappingsChange(newMappings);
  };

  const deleteRow = (key: string) => {
    const newMappings = mappings.filter((mapping) => mapping.key !== key);
    setMappings(newMappings);
    onMappingsChange(newMappings);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'valid':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'invalid':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  const columns: ColumnsType<MappingRow> = [
    {
      title: 'Status',
      key: 'status',
      width: 60,
      render: (_, record) => (
        <Tooltip title={record.error || (record.status === 'valid' ? 'Valid' : '')}>
          {getStatusIcon(record.status)}
        </Tooltip>
      ),
    },
    {
      title: <Text strong>Wikidata Type *</Text>,
      dataIndex: 'wikidata_type',
      key: 'wikidata_type',
      width: 200,
      render: (text: string, record: MappingRow) => (
        <Input
          placeholder="e.g., human, mega city"
          value={text}
          onChange={(e) => updateMapping(record.key, 'wikidata_type', e.target.value)}
          status={record.status === 'invalid' ? 'error' : undefined}
        />
      ),
    },
    {
      title: <Text strong>Map To *</Text>,
      dataIndex: 'mapped_type',
      key: 'mapped_type',
      width: 180,
      render: (text: string, record: MappingRow) => (
        <Select
          value={text}
          onChange={(value) => updateMapping(record.key, 'mapped_type', value)}
          style={{ width: '100%' }}
        >
          {approvedTypes.map((type) => (
            <Option key={type} value={type}>
              <Tag color={getTypeColor(type)}>{type}</Tag>
            </Option>
          ))}
        </Select>
      ),
    },
    {
      title: 'Wikidata QID',
      dataIndex: 'wikidata_qid',
      key: 'wikidata_qid',
      width: 150,
      render: (text: string, record: MappingRow) => (
        <Input
          placeholder="e.g., Q5"
          value={text}
          onChange={(e) => updateMapping(record.key, 'wikidata_qid', e.target.value)}
        />
      ),
    },
    {
      title: 'Notes',
      dataIndex: 'notes',
      key: 'notes',
      render: (text: string, record: MappingRow) => (
        <Input
          placeholder="Optional notes"
          value={text}
          onChange={(e) => updateMapping(record.key, 'notes', e.target.value)}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <Popconfirm
          title="Delete this row?"
          onConfirm={() => deleteRow(record.key)}
          okText="Yes"
          cancelText="No"
        >
          <Button type="text" danger icon={<DeleteOutlined />} size="small" />
        </Popconfirm>
      ),
    },
  ];

  const validCount = mappings.filter((m) => m.status === 'valid').length;
  const invalidCount = mappings.filter((m) => m.status === 'invalid').length;

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Text>
              Total: {mappings.length} | Valid: <Text type="success">{validCount}</Text> | Invalid:{' '}
              <Text type="danger">{invalidCount}</Text>
            </Text>
          </Space>
          <Button type="dashed" icon={<PlusOutlined />} onClick={addRow}>
            Add Row
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={mappings}
          pagination={false}
          scroll={{ y: 400 }}
          size="small"
        />

        <Button type="dashed" block icon={<PlusOutlined />} onClick={addRow}>
          Add Another Row
        </Button>
      </Space>
    </div>
  );
};

export default BulkTypeMappingEditor;
