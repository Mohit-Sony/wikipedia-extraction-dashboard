// frontend/src/pages/TypeMappings.tsx
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Input,
  Select,
  Modal,
  message,
  Alert,
  Row,
  Col,
  Divider,
  Tooltip,
  Badge
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  ExclamationCircleOutlined,
  FilterOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { confirm } = Modal;

interface TypeMapping {
  id: number;
  wikidata_type: string;
  wikidata_qid?: string;
  mapped_type: string;
  is_approved: boolean;
  confidence: number;
  source: string;
  created_by: string;
  notes?: string;
}

interface UnmappedType {
  type: string;
  count: number;
  example_qids: Array<{ qid: string; title: string }>;
}

const APPROVED_TYPES = [
  'person',
  'location',
  'event',
  'dynasty',
  'political_entity',
  'timeline'
];

const TypeMappings: React.FC = () => {
  const [mappings, setMappings] = useState<TypeMapping[]>([]);
  const [unmappedTypes, setUnmappedTypes] = useState<UnmappedType[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);

  const [newMapping, setNewMapping] = useState({
    wikidata_type: '',
    mapped_type: 'person',
    wikidata_qid: '',
    is_approved: true,
    notes: '',
  });

  useEffect(() => {
    fetchMappings();
    fetchUnmappedTypes();
  }, []);

  const fetchMappings = async () => {
    try {
      const response = await fetch('http://localhost:8002/api/v1/type-mappings');
      if (!response.ok) throw new Error('Failed to fetch mappings');
      const data = await response.json();
      setMappings(data);
    } catch (error) {
      message.error('Failed to fetch type mappings');
    } finally {
      setLoading(false);
    }
  };

  const fetchUnmappedTypes = async () => {
    try {
      const response = await fetch('http://localhost:8002/api/v1/type-mappings/unmapped');
      if (!response.ok) throw new Error('Failed to fetch unmapped types');
      const data = await response.json();
      setUnmappedTypes(data);
    } catch (error) {
      console.error('Failed to fetch unmapped types:', error);
    }
  };

  const createMapping = async () => {
    try {
      const response = await fetch('http://localhost:8002/api/v1/type-mappings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newMapping),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create mapping');
      }

      message.success('Type mapping created successfully');
      setIsAddModalVisible(false);
      setNewMapping({
        wikidata_type: '',
        mapped_type: 'person',
        wikidata_qid: '',
        is_approved: true,
        notes: '',
      });

      fetchMappings();
      fetchUnmappedTypes();
    } catch (error: any) {
      message.error(error.message || 'Failed to create mapping');
    }
  };

  const deleteMapping = async (id: number) => {
    confirm({
      title: 'Delete Type Mapping',
      icon: <ExclamationCircleOutlined />,
      content: 'Are you sure you want to delete this type mapping?',
      onOk: async () => {
        try {
          const response = await fetch(`http://localhost:8002/api/v1/type-mappings/${id}`, {
            method: 'DELETE',
          });

          if (!response.ok) throw new Error('Failed to delete mapping');

          message.success('Type mapping deleted successfully');
          fetchMappings();
          fetchUnmappedTypes();
        } catch (error) {
          message.error('Failed to delete mapping');
        }
      },
    });
  };

  const quickMapUnmappedType = (unmappedType: string, targetType: string) => {
    setNewMapping({
      ...newMapping,
      wikidata_type: unmappedType,
      mapped_type: targetType,
    });
    setIsAddModalVisible(true);
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      person: 'blue',
      location: 'green',
      event: 'purple',
      dynasty: 'gold',
      political_entity: 'red',
      timeline: 'cyan',
    };
    return colors[type] || 'default';
  };

  const columns = [
    {
      title: 'Wikidata Type',
      dataIndex: 'wikidata_type',
      key: 'wikidata_type',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: 'Wikidata QID',
      dataIndex: 'wikidata_qid',
      key: 'wikidata_qid',
      render: (text: string) => text ? <Text code>{text}</Text> : <Text type="secondary">-</Text>,
    },
    {
      title: 'Mapped To',
      dataIndex: 'mapped_type',
      key: 'mapped_type',
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{type}</Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_approved',
      key: 'is_approved',
      render: (approved: boolean) => (
        approved ?
          <Tag color="success">Approved</Tag> :
          <Tag color="default">Pending</Tag>
      ),
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      render: (source: string) => <Tag>{source}</Tag>,
    },
    {
      title: 'Notes',
      dataIndex: 'notes',
      key: 'notes',
      ellipsis: true,
      render: (text: string) => text || <Text type="secondary">-</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, record: TypeMapping) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => deleteMapping(record.id)}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>Type Mapping Management</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsAddModalVisible(true)}
        >
          Add Type Mapping
        </Button>
      </div>

      {/* Unmapped Types Section */}
      {unmappedTypes.length > 0 && (
        <Card
          title={
            <Space>
              <ExclamationCircleOutlined style={{ color: '#faad14' }} />
              <span>Unmapped Types in Review Queue ({unmappedTypes.length})</span>
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Alert
            message="These types are currently in the review queue but not mapped to any standard type. Map them to enable type-based filtering."
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Row gutter={[16, 16]}>
            {unmappedTypes.map((unmapped) => (
              <Col xs={24} sm={12} lg={8} key={unmapped.type}>
                <Card size="small">
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <Text strong>{unmapped.type}</Text>
                      <Badge count={unmapped.count} style={{ backgroundColor: '#52c41a' }} />
                    </Space>
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>Examples:</Text>
                    <ul style={{ margin: '4px 0', paddingLeft: 20, fontSize: 12 }}>
                      {unmapped.example_qids.slice(0, 2).map((ex) => (
                        <li key={ex.qid} style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {ex.title}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {APPROVED_TYPES.map((type) => (
                      <Button
                        key={type}
                        size="small"
                        onClick={() => quickMapUnmappedType(unmapped.type, type)}
                      >
                        → {type}
                      </Button>
                    ))}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* Existing Mappings Table */}
      <Card title={`Existing Type Mappings (${mappings.length})`}>
        <Table
          columns={columns}
          dataSource={mappings}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          locale={{
            emptyText: 'No type mappings created yet. Add your first mapping above.',
          }}
        />
      </Card>

      {/* Type Legend */}
      <Card title="Approved Standard Types" style={{ marginTop: 24 }}>
        <Space wrap>
          {APPROVED_TYPES.map((type) => (
            <Tag key={type} color={getTypeColor(type)} style={{ fontSize: 14, padding: '4px 12px' }}>
              {type}
            </Tag>
          ))}
        </Space>
        <Divider />
        <Text type="secondary">
          Only entities mapped to these types will be approved when using type-based filtering
          in the review queue.
        </Text>
      </Card>

      {/* Add Mapping Modal */}
      <Modal
        title="Create New Type Mapping"
        open={isAddModalVisible}
        onOk={createMapping}
        onCancel={() => {
          setIsAddModalVisible(false);
          setNewMapping({
            wikidata_type: '',
            mapped_type: 'person',
            wikidata_qid: '',
            is_approved: true,
            notes: '',
          });
        }}
        okText="Create Mapping"
        okButtonProps={{ icon: <SaveOutlined /> }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text>Wikidata/Wikipedia Type *</Text>
            <Input
              placeholder="e.g., human, mega city, battle"
              value={newMapping.wikidata_type}
              onChange={(e) =>
                setNewMapping({ ...newMapping, wikidata_type: e.target.value })
              }
              style={{ marginTop: 4 }}
            />
          </div>

          <div>
            <Text>Map To Standard Type *</Text>
            <Select
              value={newMapping.mapped_type}
              onChange={(value) =>
                setNewMapping({ ...newMapping, mapped_type: value })
              }
              style={{ width: '100%', marginTop: 4 }}
            >
              {APPROVED_TYPES.map((type) => (
                <Option key={type} value={type}>
                  <Tag color={getTypeColor(type)}>{type}</Tag>
                </Option>
              ))}
            </Select>
          </div>

          <div>
            <Text>Wikidata QID (Optional)</Text>
            <Input
              placeholder="e.g., Q5"
              value={newMapping.wikidata_qid}
              onChange={(e) =>
                setNewMapping({ ...newMapping, wikidata_qid: e.target.value })
              }
              style={{ marginTop: 4 }}
            />
          </div>

          <div>
            <Text>Notes (Optional)</Text>
            <TextArea
              placeholder="Additional notes about this mapping"
              value={newMapping.notes}
              onChange={(e) =>
                setNewMapping({ ...newMapping, notes: e.target.value })
              }
              rows={3}
              style={{ marginTop: 4 }}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default TypeMappings;
