import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import type { DocumentAnalytics } from '@/services/admin'

interface DocumentAnalyticsChartProps {
  data: DocumentAnalytics
}

export const DocumentAnalyticsChart = ({ data }: DocumentAnalyticsChartProps) => {
  // Format upload trends data
  const uploadTrendsData = data.upload_trends.map((item) => ({
    date: new Date(item.date).toLocaleDateString('vi-VN', { month: 'short', day: 'numeric' }),
    count: item.count,
  }))

  // Format file type distribution
  const fileTypeData = data.file_type_distribution.map((item) => ({
    type: item.file_type.toUpperCase(),
    count: item.count,
    size: (item.total_size_bytes / (1024 * 1024)).toFixed(2), // Convert to MB
  }))

  return (
    <div className="space-y-6">
      {/* Upload Trends */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Xu hướng tải lên tài liệu
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={uploadTrendsData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="count" stroke="#3b82f6" name="Số tài liệu" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* File Type Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Phân bố loại file
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={fileTypeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#10b981" name="Số lượng" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Processing Stats */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Thống kê xử lý tài liệu
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {data.processing_performance.total_processed}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Đã xử lý</div>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {data.processing_performance.avg_processing_seconds.toFixed(1)}s
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Thời gian TB</div>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {data.processing_performance.total_chunks.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Tổng chunks</div>
          </div>
          <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {data.processing_performance.avg_chunks_per_document.toFixed(0)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">Chunks/tài liệu</div>
          </div>
        </div>
      </div>

      {/* Top Uploaders */}
      {data.top_uploaders.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Top người tải lên
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Người dùng
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Số tài liệu
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Dung lượng
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {data.top_uploaders.map((uploader) => (
                  <tr key={uploader.username}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                      {uploader.username}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {uploader.upload_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {(uploader.total_size_bytes / (1024 * 1024)).toFixed(2)} MB
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
