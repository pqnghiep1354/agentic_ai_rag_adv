import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const BASE_URL = `${API_URL}/api/v1/chat`

// Add auth token to requests
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const exportService = {
  // Export conversation to PDF
  async exportToPDF(conversationId: number): Promise<Blob> {
    const response = await axios.post(
      `${BASE_URL}/export/pdf`,
      { conversation_id: conversationId },
      {
        responseType: 'blob',
      }
    )
    return response.data
  },

  // Export conversation to Excel
  async exportToExcel(conversationId: number): Promise<Blob> {
    const response = await axios.post(
      `${BASE_URL}/export/excel`,
      { conversation_id: conversationId },
      {
        responseType: 'blob',
      }
    )
    return response.data
  },

  // Helper to trigger download
  downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },
}
