// frontend/src/pages/TypeMappings.tsx
import React, { useState } from 'react';
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
  Badge,
  Tabs,
  Checkbox
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  ExclamationCircleOutlined,
  AppstoreAddOutlined,
  TableOutlined,
  DragOutlined
} from '@ant-design/icons';
import BulkTypeMappingEditor from '../components/BulkTypeMappingEditor';
import BulkImportModal from '../components/BulkImportModal';
import {
  useGetTypeMappingsQuery,
  useCreateTypeMappingMutation,
  useDeleteTypeMappingMutation,
  useGetUnmappedTypesQuery,
  useBulkCreateTypeMappingsMutation
} from '../store/api';

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

// interface UnmappedType {
//   type: string;
//   count: number;
//   example_qids: Array<{ qid: string; title: string }>;
// }

// interface UnmappedTypesResponse {
//   types: UnmappedType[];
//   total: number;
//   limit: number;
//   offset: number;
//   has_more: boolean;
// }

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
  const [unmappedPage, setUnmappedPage] = useState(1);
  const unmappedPageSize = 60;
  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [isBulkModalVisible, setIsBulkModalVisible] = useState(false);
  const [bulkMappings, setBulkMappings] = useState<any[]>([]);
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

  // RTK Query hooks
  const { data: mappings = [], isLoading: loading } = useGetTypeMappingsQuery({});
  const { data: unmappedData } = useGetUnmappedTypesQuery({
    limit: unmappedPageSize,
    offset: (unmappedPage - 1) * unmappedPageSize,
    sort_by: 'count',
    sort_order: 'desc',
  });
  const [createMapping] = useCreateTypeMappingMutation();
  const [deleteMapping] = useDeleteTypeMappingMutation();
  const [bulkCreateMappings, { isLoading: bulkSaving }] = useBulkCreateTypeMappingsMutation();

  const unmappedTypes = unmappedData?.types || [];
  const unmappedTotal = unmappedData?.total || 0;

  const handleCreateMapping = async () => {
    try {
      await createMapping(newMapping).unwrap();
      message.success('Type mapping created successfully');
      setIsAddModalVisible(false);
      setNewMapping({
        wikidata_type: '',
        mapped_type: 'person',
        wikidata_qid: '',
        is_approved: true,
        notes: '',
      });
    } catch (error: any) {
      message.error(error.data?.detail || 'Failed to create mapping');
    }
  };

  const handleDeleteMapping = async (id: number) => {
    confirm({
      title: 'Delete Type Mapping',
      icon: <ExclamationCircleOutlined />,
      content: 'Are you sure you want to delete this type mapping?',
      onOk: async () => {
        try {
          await deleteMapping(id).unwrap();
          message.success('Type mapping deleted successfully');
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

    try {
      const result = await bulkCreateMappings({
        mappings: mappingsToSave,
        fail_on_error: false,
      }).unwrap();

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
    } catch (error: any) {
      message.error(error.data?.detail || 'Failed to save mappings');
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

    try {
      const result = await bulkCreateMappings({
        mappings: validMappings.map((m: any) => ({
          wikidata_type: m.wikidata_type,
          mapped_type: m.mapped_type,
          wikidata_qid: m.wikidata_qid || undefined,
          notes: m.notes || undefined,
          is_approved: true,
        })),
        fail_on_error: false,
      }).unwrap();

      if (result.error_count > 0) {
        message.warning(
          `Created ${result.success_count} mappings. ${result.error_count} failed.`
        );
      } else {
        message.success(`Successfully created ${result.success_count} type mappings`);
      }

      setIsBulkModalVisible(false);
      setBulkMappings([]);
    } catch (error: any) {
      message.error(error.data?.detail || 'Failed to create bulk mappings');
    }
  };

  const handleBatchUnmappedSave = async () => {
    if (selectedUnmappedTypes.length === 0) {
      message.error('Please select at least one type to map');
      return;
    }

    try {
      const result = await bulkCreateMappings({
        mappings: selectedUnmappedTypes.map((type) => ({
          wikidata_type: type,
          mapped_type: batchTargetType,
          is_approved: true,
        })),
        fail_on_error: false,
      }).unwrap();

      message.success(`Successfully mapped ${result.success_count} types to ${batchTargetType}`);

      setIsBatchUnmappedVisible(false);
      setSelectedUnmappedTypes([]);
    } catch (error: any) {
      message.error(error.data?.detail || 'Failed to create batch mappings');
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
          onClick={() => handleDeleteMapping(record.id)}
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
        onOk={handleCreateMapping}
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
