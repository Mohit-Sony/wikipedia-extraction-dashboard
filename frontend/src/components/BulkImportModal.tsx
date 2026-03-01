// frontend/src/components/BulkImportModal.tsx
import React, { useState } from 'react';
import {
  Tabs,
  Upload,
  Button,
  Input,
  Space,
  Typography,
  Alert,
  Table,
  Tag,
  message,
  Card,
  Divider
} from 'antd';
import {
  UploadOutlined,
  DownloadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;
const { TabPane } = Tabs;

interface ParsedMapping {
  wikidata_type: string;
  mapped_type: string;
  wikidata_qid?: string;
  notes?: string;
  status: 'valid' | 'invalid';
  error?: string;
}

interface BulkImportModalProps {
  approvedTypes: string[];
  onImport: (mappings: ParsedMapping[]) => void;
  getTypeColor: (type: string) => string;
}

const BulkImportModal: React.FC<BulkImportModalProps> = ({
  approvedTypes,
  onImport,
  getTypeColor,
}) => {
  const [textInput, setTextInput] = useState('');
  const [parsedMappings, setParsedMappings] = useState<ParsedMapping[]>([]);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const downloadTemplate = () => {
    const csv = `wikidata_type,mapped_type,wikidata_qid,notes
human,person,Q5,Example mapping for humans
mega city,location,Q1549591,Large urban areas
battle,event,,Military conflicts
kingdom,political_entity,,Historical kingdoms`;

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'type_mapping_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
    message.success('Template downloaded');
  };

  const validateMapping = (mapping: Partial<ParsedMapping>): ParsedMapping => {
    const errors: string[] = [];

    if (!mapping.wikidata_type || mapping.wikidata_type.trim() === '') {
      errors.push('Wikidata type is required');
    }

    if (!mapping.mapped_type || mapping.mapped_type.trim() === '') {
      errors.push('Mapped type is required');
    } else if (!approvedTypes.includes(mapping.mapped_type)) {
      errors.push(`Invalid mapped type. Must be one of: ${approvedTypes.join(', ')}`);
    }

    return {
      wikidata_type: mapping.wikidata_type || '',
      mapped_type: mapping.mapped_type || 'person',
      wikidata_qid: mapping.wikidata_qid,
      notes: mapping.notes,
      status: errors.length > 0 ? 'invalid' : 'valid',
      error: errors.length > 0 ? errors.join('; ') : undefined,
    };
  };

  const parseTextInput = (text: string): ParsedMapping[] => {
    const lines = text.split('\n').filter((line) => line.trim() !== '');
    const mappings: ParsedMapping[] = [];

    for (const line of lines) {
      // Try different formats
      if (line.includes('->')) {
        // Format: type -> mapped_type
        const [wikidata_type, mapped_type] = line.split('->').map((s) => s.trim());
        mappings.push(validateMapping({ wikidata_type, mapped_type }));
      } else if (line.includes(',') || line.includes('\t')) {
        // Format: CSV or TSV
        const separator = line.includes('\t') ? '\t' : ',';
        const parts = line.split(separator).map((s) => s.trim());

        if (parts.length >= 2) {
          mappings.push(
            validateMapping({
              wikidata_type: parts[0],
              mapped_type: parts[1],
              wikidata_qid: parts[2] || undefined,
              notes: parts[3] || undefined,
            })
          );
        }
      } else {
        // Single word - assume it's a wikidata type that needs mapping
        mappings.push(
          validateMapping({
            wikidata_type: line.trim(),
            mapped_type: 'person',
          })
        );
      }
    }

    return mappings;
  };

  const handleTextParse = () => {
    const mappings = parseTextInput(textInput);
    setParsedMappings(mappings);
    message.success(`Parsed ${mappings.length} mappings`);
  };

  const handleFileUpload = (file: File) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n').filter((line) => line.trim() !== '');
      const mappings: ParsedMapping[] = [];

      // Skip header if it looks like CSV header
      let startIndex = 0;
      if (lines[0].toLowerCase().includes('wikidata_type')) {
        startIndex = 1;
      }

      for (let i = startIndex; i < lines.length; i++) {
        const line = lines[i];
        const separator = line.includes('\t') ? '\t' : ',';
        const parts = line.split(separator).map((s) => s.trim().replace(/^"|"$/g, ''));

        if (parts.length >= 2) {
          mappings.push(
            validateMapping({
              wikidata_type: parts[0],
              mapped_type: parts[1],
              wikidata_qid: parts[2] || undefined,
              notes: parts[3] || undefined,
            })
          );
        }
      }

      setParsedMappings(mappings);
      message.success(`Imported ${mappings.length} mappings from file`);
    };

    reader.readAsText(file);
    return false; // Prevent auto upload
  };

  const handleImport = () => {
    const validMappings = parsedMappings.filter((m) => m.status === 'valid');
    if (validMappings.length === 0) {
      message.error('No valid mappings to import');
      return;
    }
    onImport(validMappings);
  };

  const columns = [
    {
      title: 'Status',
      key: 'status',
      width: 60,
      render: (_: any, record: ParsedMapping) =>
        record.status === 'valid' ? (
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        ) : (
          <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
        ),
    },
    {
      title: 'Wikidata Type',
      dataIndex: 'wikidata_type',
      key: 'wikidata_type',
    },
    {
      title: 'Mapped Type',
      dataIndex: 'mapped_type',
      key: 'mapped_type',
      render: (type: string) => <Tag color={getTypeColor(type)}>{type}</Tag>,
    },
    {
      title: 'QID',
      dataIndex: 'wikidata_qid',
      key: 'wikidata_qid',
      render: (text: string) => text || <Text type="secondary">-</Text>,
    },
    {
      title: 'Notes',
      dataIndex: 'notes',
      key: 'notes',
      render: (text: string) => text || <Text type="secondary">-</Text>,
    },
    {
      title: 'Error',
      dataIndex: 'error',
      key: 'error',
      render: (text: string) => text && <Text type="danger">{text}</Text>,
    },
  ];

  const validCount = parsedMappings.filter((m) => m.status === 'valid').length;
  const invalidCount = parsedMappings.filter((m) => m.status === 'invalid').length;

  return (
    <div>
      <Tabs defaultActiveKey="csv">
        <TabPane tab="CSV/TSV Import" key="csv">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Alert
              message="Import type mappings from CSV or TSV files"
              description={
                <div>
                  <Paragraph>
                    Expected format: <Text code>wikidata_type,mapped_type,wikidata_qid,notes</Text>
                  </Paragraph>
                  <Paragraph>Example: <Text code>human,person,Q5,Human beings</Text></Paragraph>
                </div>
              }
              type="info"
            />

            <Button icon={<DownloadOutlined />} onClick={downloadTemplate}>
              Download Template CSV
            </Button>

            <Upload
              beforeUpload={handleFileUpload}
              fileList={fileList}
              onChange={({ fileList }) => setFileList(fileList)}
              accept=".csv,.tsv,.txt"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>Select CSV/TSV File</Button>
            </Upload>
          </Space>
        </TabPane>

        <TabPane tab="Paste Text" key="text">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Alert
              message="Paste type mappings in various formats"
              description={
                <div>
                  <Paragraph>Supported formats:</Paragraph>
                  <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                    <li><Text code>type -&gt; mapped_type</Text> (simple)</li>
                    <li><Text code>type, mapped_type, qid, notes</Text> (CSV)</li>
                    <li>Tab-separated values (from Excel/Sheets)</li>
                    <li>One type per line (defaults to "person")</li>
                  </ul>
                </div>
              }
              type="info"
            />

            <TextArea
              rows={10}
              placeholder={`Example formats:
human -> person
mega city -> location
battle, event, , Military conflicts
kingdom	political_entity	Q417175	Historical states`}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
            />

            <Button type="primary" icon={<FileTextOutlined />} onClick={handleTextParse}>
              Parse Text
            </Button>
          </Space>
        </TabPane>
      </Tabs>

      {parsedMappings.length > 0 && (
        <>
          <Divider />
          <Card
            title={
              <Space>
                <Text>Preview</Text>
                <Tag color="success">{validCount} Valid</Tag>
                <Tag color="error">{invalidCount} Invalid</Tag>
              </Space>
            }
            extra={
              <Button
                type="primary"
                onClick={handleImport}
                disabled={validCount === 0}
              >
                Import {validCount} Valid Mapping{validCount !== 1 ? 's' : ''}
              </Button>
            }
          >
            <Table
              columns={columns}
              dataSource={parsedMappings}
              rowKey={(record, index) => `${record.wikidata_type}-${index}`}
              pagination={false}
              scroll={{ y: 300 }}
              size="small"
            />
          </Card>
        </>
      )}
    </div>
  );
};

export default BulkImportModal;
