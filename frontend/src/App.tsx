// src/App.tsx
import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Provider } from 'react-redux'
import { ConfigProvider } from 'antd'
import { store } from './store'
import { MainLayout } from './components/layout/MainLayout'
import { Dashboard } from './pages/Dashboard'
import { EntityManager } from './pages/EntityManager'
import { QueueManager } from './pages/QueueManager'
import { Analytics } from './pages/Analytics'
import { ExtractionManager } from './pages/ExtractionManager'
import { SystemStatus } from './pages/SystemStatus'
import TypeMappings from './pages/TypeMappings'
import BulkTypeMappingPage from './pages/BulkTypeMappingPage'
import { NotificationProvider } from './components/common/NotificationProvider'
import { useWebSocket } from './hooks/useWebSocket'
import './App.css'

// Ant Design theme configuration
const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
    colorBgContainer: '#ffffff',
  },
  components: {
    Layout: {
      bodyBg: '#f0f2f5',
      headerBg: '#ffffff',
      siderBg: '#ffffff',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#e6f7ff',
      itemHoverBg: '#f5f5f5',
    },
    Table: {
      headerBg: '#fafafa',
      rowHoverBg: '#fafafa',
    },
    Card: {
      actionsBg: '#fafafa',
    },
  },
}

// WebSocket wrapper component
const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useWebSocket() // Initialize WebSocket connection
  return <>{children}</>
}

const AppContent: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Full-screen routes without MainLayout */}
        <Route path="/type-mappings/bulk-drag-drop" element={<BulkTypeMappingPage />} />

        {/* Routes with MainLayout */}
        <Route path="/" element={<MainLayout><Navigate to="/dashboard" replace /></MainLayout>} />
        <Route path="/dashboard" element={<MainLayout><Dashboard /></MainLayout>} />
        <Route path="/entities" element={<MainLayout><EntityManager /></MainLayout>} />
        <Route path="/queues" element={<MainLayout><QueueManager /></MainLayout>} />
        <Route path="/analytics" element={<MainLayout><Analytics /></MainLayout>} />
        <Route path="/system" element={<MainLayout><SystemStatus /></MainLayout>} />
        <Route path="/extraction" element={<MainLayout><ExtractionManager /></MainLayout>} />
        <Route path="/type-mappings" element={<MainLayout><TypeMappings /></MainLayout>} />
        <Route path="*" element={<MainLayout><Navigate to="/dashboard" replace /></MainLayout>} />
      </Routes>
    </Router>
  )
}

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <ConfigProvider theme={theme}>
        <WebSocketProvider>
          <NotificationProvider>
            <AppContent />
          </NotificationProvider>
        </WebSocketProvider>
      </ConfigProvider>
    </Provider>
  )
}

export default App