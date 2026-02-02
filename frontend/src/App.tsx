import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChatPage from './pages/Chat'
import DocumentsPage from './pages/Documents'
import AdminPage from './pages/Admin'
import Layout from './components/Layout'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
