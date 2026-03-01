// frontend/src/pages/TypeMappings.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Badge,
  Tabs,
  Checkbox,
  Progress
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  ExclamationCircleOutlined,
  FilterOutlined,
  AppstoreAddOutlined,
  TableOutlined,
  DragOutlined
} from '@ant-design/icons';
import BulkTypeMappingEditor from '../components/BulkTypeMappingEditor';
import BulkImportModal from '../components/BulkImportModal';

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

interface UnmappedTypesResponse {
  types: UnmappedType[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

const APPROVED_TYPES = [
  'person',
  'location',
  'event',
  'dynasty',
  'political_entity',
  'timeline',
  'other'
];

const TypeMappings: React.FC = () => {
  const navigate = useNavigate();
  const [mappings, setMappings] = useState<TypeMapping[]>([]);
  const [unmappedTypes, setUnmappedTypes] = useState<UnmappedType[]>([]);
  const [unmappedTotal, setUnmappedTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [unmappedPage, setUnmappedPage] = useState(1);
  const [unmappedPageSize, setUnmappedPageSize] = useState(60);
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [isBulkModalVisible, setIsBulkModalVisible] = useState(false);
  const [bulkMappings, setBulkMappings] = useState<any[]>([]);
  const [bulkSaving, setBulkSaving] = useState(false);
  const [selectedUnmappedTypes, setSelectedUnmappedTypes] = useState<string[]>([]);
  const [isBatchUnmappedVisible, setIsBatchUnmappedVisible] = useState(false);
  const [batchTargetType, setBatchTargetType] = useState('person');

  // Multi-select state: maps type name to target type
  const [multiSelectMappings, setMultiSelectMappings] = useState<Record<string, string>>({});
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);

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

  useEffect(() => {
    fetchUnmappedTypes(unmappedPage);
  }, [unmappedPage]);

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

  const fetchUnmappedTypes = async (page: number = unmappedPage) => {
    try {
      const offset = (page - 1) * unmappedPageSize;
      const params = new URLSearchParams({
        limit: unmappedPageSize.toString(),
        offset: offset.toString(),
        sort_by: 'count',
        sort_order: 'desc'
      });

      const response = await fetch(`http://localhost:8002/api/v1/type-mappings/unmapped?${params}`);
      if (!response.ok) throw new Error('Failed to fetch unmapped types');
      const data: UnmappedTypesResponse = await response.json();

      setUnmappedTypes(data.types);
      setUnmappedTotal(data.total);
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
    if (isMultiSelectMode) {
      // In multi-select mode, just assign the type
      setMultiSelectMappings(prev => ({
        ...prev,
        [unmappedType]: targetType
      }));
      message.success(`Assigned "${unmappedType}" to ${targetType}`);
    } else {
      // Single mode: open modal
      setNewMapping({
        ...newMapping,
        wikidata_type: unmappedType,
        mapped_type: targetType,
      });
      setIsAddModalVisible(true);
    }
  };

  const handleMultiSelectSave = async () => {
    const mappingsToSave = Object.entries(multiSelectMappings).map(([wikidataType, mappedType]) => ({
      wikidata_type: wikidataType,
      mapped_type: mappedType,
      is_approved: true,
    }));

    if (mappingsToSave.length === 0) {
      message.warning('No mappings selected');
      return;
    }

    setBulkSaving(true);

    try {
      const payload = {
        mappings: mappingsToSave,
        fail_on_error: false,
      };

      const response = await fetch('http://localhost:8002/api/v1/type-mappings/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save mappings');
      }

      const result = await response.json();

      if (result.error_count > 0) {
        message.warning(
          `Saved ${result.success_count} mappings. ${result.error_count} failed.`
        );
      } else {
        message.success(`Successfully saved ${result.success_count} type mappings`);
      }

      // Clear selections and refresh
      setMultiSelectMappings({});
      setIsMultiSelectMode(false);
      fetchMappings();
      fetchUnmappedTypes();
    } catch (error: any) {
      message.error(error.message || 'Failed to save mappings');
    } finally {
      setBulkSaving(false);
    }
  };

  const handleClearSelections = () => {
    setMultiSelectMappings({});
    message.info('Selections cleared');
  };

  const toggleMultiSelectMode = () => {
    if (isMultiSelectMode) {
      // Exiting multi-select mode - clear selections
      setMultiSelectMappings({});
    }
    setIsMultiSelectMode(!isMultiSelectMode);
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      person: 'blue',
      location: 'green',
      event: 'purple',
      dynasty: 'gold',
      political_entity: 'red',
      timeline: 'cyan',
      other: 'default',
    };
    return colors[type] || 'default';
  };

  const handleBulkSave = async () => {
    const validMappings = bulkMappings.filter((m) => m.status === 'valid');

    if (validMappings.length === 0) {
      message.error('No valid mappings to save');
      return;
    }

    setBulkSaving(true);

    try {
      const payload = {
        mappings: validMappings.map((m: any) => ({
          wikidata_type: m.wikidata_type,
          mapped_type: m.mapped_type,
          wikidata_qid: m.wikidata_qid || undefined,
          notes: m.notes || undefined,
          is_approved: true,
        })),
        fail_on_error: false,
      };

      const response = await fetch('http://localhost:8002/api/v1/type-mappings/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create bulk mappings');
      }

      const result = await response.json();

      if (result.error_count > 0) {
        message.warning(
          `Created ${result.success_count} mappings. ${result.error_count} failed.`
        );
      } else {
        message.success(`Successfully created ${result.success_count} type mappings`);
      }

      setIsBulkModalVisible(false);
      setBulkMappings([]);
      fetchMappings();
      fetchUnmappedTypes();
    } catch (error: any) {
      message.error(error.message || 'Failed to create bulk mappings');
    } finally {
      setBulkSaving(false);
    }
  };

  const handleBatchUnmappedSave = async () => {
    if (selectedUnmappedTypes.length === 0) {
      message.error('Please select at least one type to map');
      return;
    }

    setBulkSaving(true);

    try {
      const payload = {
        mappings: selectedUnmappedTypes.map((type) => ({
          wikidata_type: type,
          mapped_type: batchTargetType,
          is_approved: true,
        })),
        fail_on_error: false,
      };

      const response = await fetch('http://localhost:8002/api/v1/type-mappings/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create batch mappings');
      }

      const result = await response.json();
      message.success(`Successfully mapped ${result.success_count} types to ${batchTargetType}`);

      setIsBatchUnmappedVisible(false);
      setSelectedUnmappedTypes([]);
      fetchMappings();
      fetchUnmappedTypes();
    } catch (error: any) {
      message.error(error.message || 'Failed to create batch mappings');
    } finally {
      setBulkSaving(false);
    }
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
        <Space>
          <Button
            icon={<PlusOutlined />}
            onClick={() => setIsAddModalVisible(true)}
          >
            Add Single
          </Button>
          <Button
            icon={<AppstoreAddOutlined />}
            onClick={() => setIsBulkModalVisible(true)}
          >
            Bulk Entry (Modal)
          </Button>
          <Button
            type="primary"
            icon={<DragOutlined />}
            onClick={() => navigate('/type-mappings/bulk-drag-drop')}
            size="large"
          >
            Drag & Drop View
          </Button>
        </Space>
      </div>

      {/* Unmapped Types Section */}
      {unmappedTotal > 0 && (
        <Card
          title={
            <Space>
              <ExclamationCircleOutlined style={{ color: '#faad14' }} />
              <span>Unmapped Types in Review Queue ({unmappedTotal})</span>
              {isMultiSelectMode && Object.keys(multiSelectMappings).length > 0 && (
                <Badge
                  count={Object.keys(multiSelectMappings).length}
                  style={{ backgroundColor: '#52c41a' }}
                  title={`${Object.keys(multiSelectMappings).length} types selected`}
                />
              )}
            </Space>
          }
          extra={
            <Space>
              <Button
                type={isMultiSelectMode ? 'primary' : 'default'}
                onClick={toggleMultiSelectMode}
              >
                {isMultiSelectMode ? 'Exit Multi-Select' : 'Multi-Select Mode'}
              </Button>
              {isMultiSelectMode && Object.keys(multiSelectMappings).length > 0 && (
                <>
                  <Button onClick={handleClearSelections}>
                    Clear Selections
                  </Button>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={handleMultiSelectSave}
                    loading={bulkSaving}
                  >
                    Save {Object.keys(multiSelectMappings).length} Mappings
                  </Button>
                </>
              )}
              {!isMultiSelectMode && (
                <Button
                  icon={<TableOutlined />}
                  onClick={() => setIsBatchUnmappedVisible(true)}
                >
                  Batch Map Selected
                </Button>
              )}
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          {isMultiSelectMode ? (
            <Alert
              message="Multi-Select Mode Active"
              description="Click the type buttons (→ person, → location, etc.) to assign each unmapped type. Selected items will be highlighted. Click 'Save Mappings' when done to save all at once."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Alert
              message="These types are currently in the review queue but not mapped to any standard type. Map them to enable type-based filtering."
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
          <Row gutter={[16, 16]}>
            {unmappedTypes.map((unmapped) => {
              const isSelected = unmapped.type in multiSelectMappings;
              const assignedType = multiSelectMappings[unmapped.type];
              const borderColor = isSelected ? getTypeColor(assignedType) : undefined;

              return (
                <Col xs={24} sm={12} lg={8} key={unmapped.type}>
                  <Card
                    size="small"
                    style={{
                      borderLeft: isSelected ? `4px solid ${borderColor}` : undefined,
                      backgroundColor: isSelected ? `${borderColor}10` : undefined,
                      transition: 'all 0.3s ease',
                    }}
                  >
                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        <Text strong>{unmapped.type}</Text>
                        <Badge count={unmapped.count} style={{ backgroundColor: '#52c41a' }} />
                        {isSelected && (
                          <Tag color={getTypeColor(assignedType)} style={{ marginLeft: 'auto' }}>
                            → {assignedType}
                          </Tag>
                        )}
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
                          type={isSelected && assignedType === type ? 'primary' : 'default'}
                          onClick={() => quickMapUnmappedType(unmapped.type, type)}
                        >
                          → {type}
                        </Button>
                      ))}
                      {isSelected && (
                        <Button
                          size="small"
                          danger
                          onClick={() => {
                            const newMappings = { ...multiSelectMappings };
                            delete newMappings[unmapped.type];
                            setMultiSelectMappings(newMappings);
                          }}
                        >
                          ✕
                        </Button>
                      )}
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
          {unmappedTotal > unmappedPageSize && (
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Space>
                <Button
                  onClick={() => setUnmappedPage(unmappedPage - 1)}
                  disabled={unmappedPage === 1}
                >
                  Previous
                </Button>
                <Text>
                  Page {unmappedPage} of {Math.ceil(unmappedTotal / unmappedPageSize)}
                  {' '}(Showing {unmappedTypes.length} of {unmappedTotal})
                </Text>
                <Button
                  onClick={() => setUnmappedPage(unmappedPage + 1)}
                  disabled={unmappedPage >= Math.ceil(unmappedTotal / unmappedPageSize)}
                >
                  Next
                </Button>
              </Space>
            </div>
          )}
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

      {/* Bulk Entry Modal */}
      <Modal
        title="Bulk Type Mapping Entry"
        open={isBulkModalVisible}
        onOk={handleBulkSave}
        onCancel={() => {
          setIsBulkModalVisible(false);
          setBulkMappings([]);
        }}
        width={1200}
        okText={`Save ${bulkMappings.filter((m) => m.status === 'valid').length} Valid Mappings`}
        okButtonProps={{
          icon: <SaveOutlined />,
          loading: bulkSaving,
          disabled: bulkMappings.filter((m) => m.status === 'valid').length === 0
        }}
        cancelButtonProps={{ disabled: bulkSaving }}
      >
        <Tabs defaultActiveKey="grid">
          <Tabs.TabPane tab="Grid Editor" key="grid">
            <BulkTypeMappingEditor
              approvedTypes={APPROVED_TYPES}
              onMappingsChange={setBulkMappings}
              getTypeColor={getTypeColor}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="Import CSV/Text" key="import">
            <BulkImportModal
              approvedTypes={APPROVED_TYPES}
              onImport={setBulkMappings}
              getTypeColor={getTypeColor}
            />
          </Tabs.TabPane>
        </Tabs>
      </Modal>

      {/* Batch Map Unmapped Types Modal */}
      <Modal
        title="Batch Map Unmapped Types"
        open={isBatchUnmappedVisible}
        onOk={handleBatchUnmappedSave}
        onCancel={() => {
          setIsBatchUnmappedVisible(false);
          setSelectedUnmappedTypes([]);
        }}
        okText={`Map ${selectedUnmappedTypes.length} Types to ${batchTargetType}`}
        okButtonProps={{
          loading: bulkSaving,
          disabled: selectedUnmappedTypes.length === 0
        }}
        cancelButtonProps={{ disabled: bulkSaving }}
        width={700}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Alert
            message="Select multiple unmapped types and map them all to the same standard type"
            type="info"
            showIcon
          />

          <div>
            <Text strong>Map selected types to:</Text>
            <Select
              value={batchTargetType}
              onChange={setBatchTargetType}
              style={{ width: '100%', marginTop: 8 }}
            >
              {APPROVED_TYPES.map((type) => (
                <Option key={type} value={type}>
                  <Tag color={getTypeColor(type)}>{type}</Tag>
                </Option>
              ))}
            </Select>
          </div>

          <Divider />

          <div>
            <Text strong>Select types to map ({selectedUnmappedTypes.length} selected):</Text>
            <div style={{ marginTop: 12, maxHeight: 400, overflowY: 'auto' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {unmappedTypes.map((unmapped) => (
                  <Card
                    key={unmapped.type}
                    size="small"
                    style={{
                      backgroundColor: selectedUnmappedTypes.includes(unmapped.type)
                        ? '#e6f7ff'
                        : undefined,
                    }}
                  >
                    <Checkbox
                      checked={selectedUnmappedTypes.includes(unmapped.type)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedUnmappedTypes([...selectedUnmappedTypes, unmapped.type]);
                        } else {
                          setSelectedUnmappedTypes(
                            selectedUnmappedTypes.filter((t) => t !== unmapped.type)
                          );
                        }
                      }}
                    >
                      <Space>
                        <Text strong>{unmapped.type}</Text>
                        <Badge count={unmapped.count} style={{ backgroundColor: '#52c41a' }} />
                      </Space>
                    </Checkbox>
                    <div style={{ marginTop: 8, paddingLeft: 24 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Examples: {unmapped.example_qids.slice(0, 2).map((ex) => ex.title).join(', ')}
                      </Text>
                    </div>
                  </Card>
                ))}
              </Space>
            </div>
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default TypeMappings;
