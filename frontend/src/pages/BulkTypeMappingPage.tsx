// frontend/src/pages/BulkTypeMappingPage.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import {
  Layout,
  Card,
  Button,
  Space,
  Typography,
  Input,
  Badge,
  message,
  Modal,
  Statistic,
  Progress,
  Alert
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  ClearOutlined,
  CheckOutlined,
  SearchOutlined,
  UndoOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined
} from '@ant-design/icons';
import { useGetUnmappedTypesQuery, useBulkCreateTypeMappingsMutation } from '../store/api';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;
const { confirm } = Modal;

interface UnmappedType {
  type: string;
  count: number;
  example_qids: Array<{ qid: string; title: string }>;
}

interface MappingItem {
  type: string;
  count: number;
  examples: Array<{ qid: string; title: string }>;
  originalData: UnmappedType;
}

interface DroppedItem extends MappingItem {
  targetType: string;
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

const TYPE_COLORS: Record<string, string> = {
  person: '#1890ff',
  location: '#52c41a',
  event: '#722ed1',
  dynasty: '#faad14',
  political_entity: '#f5222d',
  timeline: '#13c2c2',
  other: '#8c8c8c',
};

const ITEM_TYPE = 'TYPE_CARD';

// Draggable Type Card Component
const DraggableTypeCard: React.FC<{
  item: MappingItem;
  isAssigned?: string;
  onRemove?: () => void;
}> = ({ item, isAssigned, onRemove }) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: ITEM_TYPE,
    item: item,
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }), [item]);

  return (
    <Card
      ref={drag}
      size="small"
      style={{
        marginBottom: 8,
        cursor: 'move',
        opacity: isDragging ? 0.5 : 1,
        borderLeft: isAssigned ? `4px solid ${TYPE_COLORS[isAssigned] || '#ccc'}` : undefined,
      }}
      hoverable
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text strong style={{ fontSize: 13 }}>{item.type}</Text>
              <Badge count={item.count} style={{ backgroundColor: '#52c41a' }} />
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {item.examples.slice(0, 2).map(ex => ex.title).join(', ')}
            </Text>
          </Space>
        </div>
        {onRemove && (
          <Button
            type="text"
            size="small"
            danger
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            style={{ marginLeft: 8 }}
          >
            ×
          </Button>
        )}
      </div>
    </Card>
  );
};

// Drop Zone Column Component
const DropZoneColumn: React.FC<{
  type: string;
  items: DroppedItem[];
  onDrop: (item: MappingItem, targetType: string) => void;
  onRemove: (type: string, itemType: string) => void;
}> = ({ type, items, onDrop, onRemove }) => {
  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: ITEM_TYPE,
    drop: (item: MappingItem) => onDrop(item, type),
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
      canDrop: !!monitor.canDrop(),
    }),
  }), [onDrop, type]);

  const bgColor = isOver && canDrop ? `${TYPE_COLORS[type]}20` : '#fafafa';
  const borderColor = isOver && canDrop ? TYPE_COLORS[type] : '#d9d9d9';

  return (
    <div
      ref={drop}
      style={{
        flex: 1,
        minHeight: '100%',
        border: `2px dashed ${borderColor}`,
        borderRadius: 8,
        padding: 12,
        backgroundColor: bgColor,
        transition: 'all 0.3s ease',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          position: 'sticky',
          top: 0,
          backgroundColor: TYPE_COLORS[type],
          color: 'white',
          padding: '8px 12px',
          borderRadius: 6,
          marginBottom: 12,
          zIndex: 1,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong style={{ color: 'white', fontSize: 14 }}>
            {type.replace('_', ' ').toUpperCase()}
          </Text>
          <Badge
            count={items.length}
            style={{ backgroundColor: 'rgba(255,255,255,0.3)' }}
          />
        </div>
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {items.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: 24,
              color: '#999',
              fontSize: 12,
            }}
          >
            Drop types here
          </div>
        ) : (
          items.map((item) => (
            <DraggableTypeCard
              key={item.type}
              item={item}
              isAssigned={type}
              onRemove={() => onRemove(type, item.type)}
            />
          ))
        )}
      </div>
    </div>
  );
};

const BulkTypeMappingPage: React.FC = () => {
  const navigate = useNavigate();
  const [availableItems, setAvailableItems] = useState<MappingItem[]>([]);
  const [mappedItems, setMappedItems] = useState<Record<string, DroppedItem[]>>({
    person: [],
    location: [],
    event: [],
    dynasty: [],
    political_entity: [],
    timeline: [],
    other: [],
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [history, setHistory] = useState<Array<typeof mappedItems>>([]);

  // RTK Query hooks
  const { data: unmappedData, isLoading: loading } = useGetUnmappedTypesQuery({});
  const [bulkCreateMappings, { isLoading: saving }] = useBulkCreateTypeMappingsMutation();

  const unmappedTypes = unmappedData?.types || [];

  useEffect(() => {
    if (unmappedTypes.length > 0) {
      const items = unmappedTypes.map((ut: UnmappedType) => ({
        type: ut.type,
        count: ut.count,
        examples: ut.example_qids,
        originalData: ut,
      }));
      setAvailableItems(items);
    }
  }, [unmappedTypes]);

  const handleDrop = useCallback((item: MappingItem, targetType: string) => {
    // Check if already in this category
    const alreadyInCategory = mappedItems[targetType].some(i => i.type === item.type);
    if (alreadyInCategory) {
      message.info(`"${item.type}" is already mapped to ${targetType}`);
      return;
    }

    // Save current state to history
    setHistory(prev => [...prev, mappedItems]);

    const newMappedItems = { ...mappedItems };

    // Remove from other categories if exists (allow moving between categories)
    Object.keys(newMappedItems).forEach(key => {
      if (key !== targetType) {
        newMappedItems[key] = newMappedItems[key].filter(i => i.type !== item.type);
      }
    });

    // Add to target category
    newMappedItems[targetType] = [
      ...newMappedItems[targetType],
      { ...item, targetType }
    ];

    setMappedItems(newMappedItems);

    // Remove from available items only when first mapped
    setAvailableItems(prev => prev.filter(i => i.type !== item.type));

    message.success(`Mapped "${item.type}" to ${targetType}`);
  }, [mappedItems]);

  const handleRemove = useCallback((targetType: string, itemType: string) => {
    setHistory(prev => [...prev, mappedItems]);

    const item = mappedItems[targetType].find(i => i.type === itemType);
    if (!item) return;

    // Remove from mapped items
    const newMappedItems = { ...mappedItems };
    newMappedItems[targetType] = newMappedItems[targetType].filter(i => i.type !== itemType);
    setMappedItems(newMappedItems);

    // Add back to available items
    setAvailableItems(prev => [...prev, item]);
  }, [mappedItems]);

  const handleUndo = () => {
    if (history.length === 0) {
      message.warning('Nothing to undo');
      return;
    }

    const previousState = history[history.length - 1];
    setHistory(prev => prev.slice(0, -1));

    // Restore previous state
    setMappedItems(previousState);

    // Recalculate available items
    const allMappedTypes = new Set(
      Object.values(previousState).flat().map(item => item.type)
    );
    const available = unmappedTypes
      .filter(ut => !allMappedTypes.has(ut.type))
      .map(ut => ({
        type: ut.type,
        count: ut.count,
        examples: ut.example_qids,
        originalData: ut,
      }));
    setAvailableItems(available);

    message.success('Undone');
  };

  const handleClearAll = () => {
    confirm({
      title: 'Clear All Mappings',
      content: 'Are you sure you want to clear all mappings and start over?',
      onOk: () => {
        setHistory(prev => [...prev, mappedItems]);
        setMappedItems({
          person: [],
          location: [],
          event: [],
          dynasty: [],
          political_entity: [],
          timeline: [],
          other: [],
        });
        const items = unmappedTypes.map((ut: UnmappedType) => ({
          type: ut.type,
          count: ut.count,
          examples: ut.example_qids,
          originalData: ut,
        }));
        setAvailableItems(items);
        message.success('All mappings cleared');
      },
    });
  };

  const handleSave = async () => {
    const allMappings = Object.entries(mappedItems).flatMap(([targetType, items]) =>
      items.map(item => ({
        wikidata_type: item.type,
        mapped_type: targetType,
        is_approved: true,
      }))
    );

    if (allMappings.length === 0) {
      message.warning('No mappings to save');
      return;
    }

    confirm({
      title: `Save ${allMappings.length} Type Mappings?`,
      content: 'This will create type mappings for all items you have organized.',
      onOk: async () => {
        try {
          const result = await bulkCreateMappings({
            mappings: allMappings,
            fail_on_error: false,
          }).unwrap();

          message.success(`Successfully saved ${result.success_count} type mappings`);

          // Navigate back
          navigate('/type-mappings');
        } catch (error: any) {
          message.error(error.data?.detail || 'Failed to save mappings');
        }
      },
    });
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const filteredAvailableItems = availableItems.filter(item =>
    item.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalMapped = Object.values(mappedItems).reduce((sum, items) => sum + items.length, 0);
  const totalTypes = unmappedTypes.length;
  const progress = totalTypes > 0 ? (totalMapped / totalTypes) * 100 : 0;

  return (
    <DndProvider backend={HTML5Backend}>
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        {/* Header */}
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Space size="large">
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/type-mappings')}
              type="text"
            >
              Back
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              Bulk Type Mapping - Drag & Drop
            </Title>
          </Space>

          <Space size="large">
            <Statistic
              title="Mapped"
              value={totalMapped}
              suffix={`/ ${totalTypes}`}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              type="circle"
              percent={Math.round(progress)}
              width={50}
              strokeColor={TYPE_COLORS.person}
            />
            <Button
              icon={<UndoOutlined />}
              onClick={handleUndo}
              disabled={history.length === 0}
            >
              Undo
            </Button>
            <Button
              icon={<ClearOutlined />}
              onClick={handleClearAll}
              disabled={totalMapped === 0}
            >
              Clear All
            </Button>
            <Button
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={toggleFullscreen}
            />
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              disabled={totalMapped === 0}
              size="large"
            >
              Save {totalMapped} Mappings
            </Button>
          </Space>
        </Header>

        {/* Main Content */}
        <Layout style={{ flex: 1, overflow: 'hidden' }}>
          {/* Left Sidebar - Available Types */}
          <Sider
            width={350}
            style={{
              background: '#fff',
              borderRight: '1px solid #f0f0f0',
              overflow: 'auto',
              padding: 16,
            }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text strong style={{ fontSize: 16 }}>
                  Unmapped Types
                </Text>
                <Badge
                  count={filteredAvailableItems.length}
                  style={{ marginLeft: 8, backgroundColor: '#faad14' }}
                />
              </div>

              <Input
                placeholder="Search types..."
                prefix={<SearchOutlined />}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                allowClear
              />

              {filteredAvailableItems.length === 0 && !loading && (
                <Alert
                  message="All types mapped!"
                  description="Great job! All unmapped types have been assigned to categories."
                  type="success"
                  showIcon
                />
              )}

              <div style={{ marginTop: 8 }}>
                {filteredAvailableItems.map((item) => (
                  <DraggableTypeCard key={item.type} item={item} />
                ))}
              </div>
            </Space>
          </Sider>

          {/* Main Drop Zone Area */}
          <Content
            style={{
              padding: 16,
              overflow: 'auto',
              background: '#f5f5f5',
            }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 16,
                height: '100%',
              }}
            >
              {APPROVED_TYPES.map((type) => (
                <DropZoneColumn
                  key={type}
                  type={type}
                  items={mappedItems[type]}
                  onDrop={handleDrop}
                  onRemove={handleRemove}
                />
              ))}
            </div>
          </Content>
        </Layout>

        {/* Bottom Bar */}
        <div
          style={{
            background: '#fff',
            borderTop: '1px solid #f0f0f0',
            padding: '12px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Space>
            <Text type="secondary">
              Drag types from the left panel to the appropriate category columns
            </Text>
          </Space>
          <Space>
            <Button
              type="primary"
              size="large"
              icon={<CheckOutlined />}
              onClick={handleSave}
              loading={saving}
              disabled={totalMapped === 0}
            >
              Done - Save All
            </Button>
          </Space>
        </div>
      </Layout>
    </DndProvider>
  );
};

export default BulkTypeMappingPage;
