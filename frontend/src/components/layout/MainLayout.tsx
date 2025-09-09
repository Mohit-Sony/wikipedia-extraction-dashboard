// src/components/layout/MainLayout.tsx
import React from 'react'
import { Layout, Menu, Button, Badge, Tooltip, Typography, Space } from 'antd'
import {
  DashboardOutlined,
  DatabaseOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  WifiOutlined,
  DisconnectOutlined,
  BellOutlined,
} from '@ant-design/icons'
import { RocketOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { toggleSidebar, selectSidebarCollapsed } from '../../store/slices/uiSlice'
import { 
  selectWebSocketConnected, 
  selectWebSocketConnecting 
} from '../../store/slices/webSocketSlice'
import { selectNotificationCount } from '../../store/slices/notificationSlice'
import { NotificationPanel } from '../common/NotificationPanel'

const { Header, Sider, Content } = Layout
const { Title } = Typography

interface MainLayoutProps {
  children: React.ReactNode
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useDispatch()
  
  const sidebarCollapsed = useSelector(selectSidebarCollapsed)
  const wsConnected = useSelector(selectWebSocketConnected)
  const wsConnecting = useSelector(selectWebSocketConnecting)
  const notificationCount = useSelector(selectNotificationCount)

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/entities',
      icon: <DatabaseOutlined />,
      label: 'Entities',
    },
    {
      key: '/queues',
      icon: <UnorderedListOutlined />,
      label: 'Queue Manager',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
    },
    {
      key: '/system',
      icon: <SettingOutlined />,
      label: 'System Status',
    },
    // In menuItems array, add after '/queues':
    {
      key: '/extraction',
      icon: <RocketOutlined />,
      label: 'Extraction',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  const getConnectionStatus = () => {
    if (wsConnecting) {
      return { icon: <WifiOutlined spin />, color: '#faad14', text: 'Connecting...' }
    }
    if (wsConnected) {
      return { icon: <WifiOutlined />, color: '#52c41a', text: 'Connected' }
    }
    return { icon: <DisconnectOutlined />, color: '#ff4d4f', text: 'Disconnected' }
  }

  const connectionStatus = getConnectionStatus()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={sidebarCollapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          borderRight: '1px solid #f0f0f0',
        }}
        theme="light"
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0',
          marginBottom: 8
        }}>
          {!sidebarCollapsed && (
            <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
              Wiki Dashboard
            </Title>
          )}
          {sidebarCollapsed && (
            <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
              WD
            </Title>
          )}
        </div>
        
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ border: 'none' }}
        />
      </Sider>
      
      <Layout style={{ marginLeft: sidebarCollapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header style={{ 
          padding: '0 24px', 
          background: '#fff', 
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 99,
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
        }}>
          <Space>
            <Button
              type="text"
              icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => dispatch(toggleSidebar())}
              style={{
                fontSize: '16px',
                width: 40,
                height: 40,
              }}
            />
            
            <Title level={4} style={{ margin: 0 }}>
              {getPageTitle(location.pathname)}
            </Title>
          </Space>

          <Space size="large">
            {/* Connection Status */}
            <Tooltip title={`WebSocket ${connectionStatus.text}`}>
              <Space style={{ color: connectionStatus.color, fontSize: '14px' }}>
                {connectionStatus.icon}
                {!sidebarCollapsed && <span>{connectionStatus.text}</span>}
              </Space>
            </Tooltip>

            {/* Notifications */}
            <NotificationPanel>
              <Badge count={notificationCount} size="small">
                <Button 
                  type="text" 
                  icon={<BellOutlined />} 
                  style={{ fontSize: '16px' }}
                />
              </Badge>
            </NotificationPanel>
          </Space>
        </Header>
        
        <Content style={{
          margin: '24px',
          minHeight: 'calc(100vh - 112px)',
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

const getPageTitle = (pathname: string): string => {
  switch (pathname) {
    case '/dashboard':
      return 'Dashboard'
    case '/entities':
      return 'Entity Manager'
    case '/queues':
      return 'Queue Manager'
    case '/analytics':
      return 'Analytics'
    case '/system':
      return 'System Status'
    default:
      return 'Wikipedia Dashboard'
  }
}