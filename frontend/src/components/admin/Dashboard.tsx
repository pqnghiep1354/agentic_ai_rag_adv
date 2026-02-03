import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Users,
  FileText,
  MessageSquare,
  Activity,
  Clock,
  TrendingUp,
  Database,
  Zap,
} from 'lucide-react'
import { adminService } from '@/services/admin'
import { StatsCard } from './StatsCard'
import { DocumentAnalyticsChart } from './DocumentAnalyticsChart'
import { QueryPerformanceChart } from './QueryPerformanceChart'
import { RecentActivityTable } from './RecentActivityTable'

export const Dashboard = () => {
  const [timeRange, setTimeRange] = useState(30)

  // Fetch dashboard data
  const { data: dashboardData, isLoading: isDashboardLoading } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: () => adminService.getDashboardStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: docAnalytics, isLoading: isDocAnalyticsLoading } = useQuery({
    queryKey: ['admin', 'document-analytics', timeRange],
    queryFn: () => adminService.getDocumentAnalytics(timeRange),
  })

  const { data: queryAnalytics, isLoading: isQueryAnalyticsLoading } = useQuery({
    queryKey: ['admin', 'query-analytics', timeRange],
    queryFn: () => adminService.getQueryAnalytics(timeRange),
  })

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  if (isDashboardLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Đang tải dữ liệu...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Quản Trị Hệ Thống
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Tổng quan và phân tích hiệu suất
          </p>
        </div>

        {/* Time range selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">Khoảng thời gian:</span>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="input py-2"
          >
            <option value={7}>7 ngày</option>
            <option value={30}>30 ngày</option>
            <option value={90}>90 ngày</option>
          </select>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Tổng người dùng"
          value={dashboardData?.overview.total_users || 0}
          icon={<Users className="h-6 w-6" />}
          color="blue"
        />
        <StatsCard
          title="Tài liệu"
          value={dashboardData?.overview.total_documents || 0}
          icon={<FileText className="h-6 w-6" />}
          color="green"
          subtitle={`${formatBytes(dashboardData?.overview.total_storage_bytes || 0)}`}
        />
        <StatsCard
          title="Cuộc hội thoại"
          value={dashboardData?.overview.total_conversations || 0}
          icon={<MessageSquare className="h-6 w-6" />}
          color="purple"
        />
        <StatsCard
          title="Tin nhắn"
          value={dashboardData?.overview.total_messages || 0}
          icon={<Activity className="h-6 w-6" />}
          color="orange"
        />
      </div>

      {/* Active Users */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Người dùng hoạt động
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {dashboardData?.active_users.last_24h || 0}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">24 giờ qua</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {dashboardData?.active_users.last_7d || 0}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">7 ngày qua</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">
              {dashboardData?.active_users.last_30d || 0}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">30 ngày qua</div>
          </div>
        </div>
      </div>

      {/* Query Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Hiệu suất truy vấn (7 ngày)
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Tổng truy vấn</span>
              <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {dashboardData?.query_metrics.total_queries_7d || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Thời gian xử lý TB</span>
              <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {(dashboardData?.query_metrics.avg_processing_time || 0).toFixed(2)}s
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Tokens sử dụng</span>
              <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {(dashboardData?.query_metrics.total_tokens_7d || 0).toLocaleString()}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Điểm retrieval TB</span>
              <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {((dashboardData?.query_metrics.avg_retrieval_score || 0) * 100).toFixed(1)}%
              </span>
            </div>
            {dashboardData?.query_metrics.avg_feedback_rating && (
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Đánh giá TB</span>
                <span className="text-2xl font-bold text-yellow-600">
                  {dashboardData.query_metrics.avg_feedback_rating.toFixed(1)}/5 ⭐
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Trạng thái tài liệu
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">✅ Hoàn thành</span>
              <span className="text-2xl font-bold text-green-600">
                {dashboardData?.documents.by_status.completed || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">⏳ Đang xử lý</span>
              <span className="text-2xl font-bold text-blue-600">
                {dashboardData?.documents.by_status.processing || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">⏸️ Chờ xử lý</span>
              <span className="text-2xl font-bold text-yellow-600">
                {dashboardData?.documents.by_status.pending || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">❌ Lỗi</span>
              <span className="text-2xl font-bold text-red-600">
                {dashboardData?.documents.by_status.failed || 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      {!isDocAnalyticsLoading && docAnalytics && (
        <DocumentAnalyticsChart data={docAnalytics} />
      )}

      {!isQueryAnalyticsLoading && queryAnalytics && (
        <QueryPerformanceChart data={queryAnalytics} />
      )}

      {/* Recent Activity */}
      {dashboardData?.recent_activity && (
        <RecentActivityTable activities={dashboardData.recent_activity} />
      )}
    </div>
  )
}
