/**
 * Document list component with status tracking
 */

import React, { useEffect, useState } from 'react';
import {
  FileText,
  Trash2,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { documentService } from '../../services/documents';
import { Document, DocumentStatus } from '../../types';

interface DocumentListProps {
  refreshTrigger?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ refreshTrigger }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  useEffect(() => {
    fetchDocuments();
  }, [selectedStatus, refreshTrigger]);

  // Auto-refresh for processing documents
  useEffect(() => {
    const hasProcessing = documents.some(
      (doc) => doc.status === 'pending' || doc.status === 'processing'
    );

    if (hasProcessing) {
      const interval = setInterval(() => {
        fetchDocuments();
      }, 3000); // Refresh every 3 seconds

      return () => clearInterval(interval);
    }
  }, [documents]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await documentService.getAll(0, 100, selectedStatus);
      setDocuments(response.documents);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Không thể tải danh sách tài liệu');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Bạn có chắc muốn xóa tài liệu này?')) {
      return;
    }

    try {
      await documentService.delete(id);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
    } catch (err: any) {
      alert('Xóa thất bại: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleReprocess = async (id: number) => {
    try {
      await documentService.reprocess(id);
      await fetchDocuments();
    } catch (err: any) {
      alert('Xử lý lại thất bại: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <CheckCircle2 className="h-3 w-3" />
            Hoàn thành
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <Loader2 className="h-3 w-3 animate-spin" />
            Đang xử lý
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            <Clock className="h-3 w-3" />
            Chờ xử lý
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <AlertCircle className="h-3 w-3" />
            Thất bại
          </span>
        );
      default:
        return null;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Đang tải...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={fetchDocuments}
          className="mt-2 text-red-600 hover:text-red-700 font-medium text-sm"
        >
          Thử lại
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-gray-700">Lọc:</label>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Tất cả</option>
          <option value="pending">Chờ xử lý</option>
          <option value="processing">Đang xử lý</option>
          <option value="completed">Hoàn thành</option>
          <option value="failed">Thất bại</option>
        </select>

        <span className="text-sm text-gray-500">
          {documents.length} tài liệu
        </span>
      </div>

      {/* Document list */}
      {documents.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">Chưa có tài liệu nào</p>
          <p className="text-sm text-gray-500 mt-1">
            Tải lên tài liệu đầu tiên để bắt đầu
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {documents.map((document) => (
            <div
              key={document.id}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <FileText className="h-6 w-6 text-blue-600" />
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-medium text-gray-900 truncate">
                        {document.title || document.filename}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {document.filename}
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      {getStatusBadge(document.status)}
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                    {document.file_size && (
                      <span>{formatFileSize(document.file_size)}</span>
                    )}
                    {document.page_count && (
                      <span>{document.page_count} trang</span>
                    )}
                    {document.chunk_count && (
                      <span>{document.chunk_count} chunks</span>
                    )}
                    {document.created_at && (
                      <span>Tải lên: {formatDate(document.created_at)}</span>
                    )}
                  </div>

                  {/* Processing info */}
                  {document.status === 'completed' && document.processing_time && (
                    <div className="mt-2 text-xs text-green-600">
                      Xử lý hoàn thành trong {document.processing_time.toFixed(1)}s
                    </div>
                  )}

                  {document.status === 'failed' && document.processing_error && (
                    <div className="mt-2 text-xs text-red-600">
                      Lỗi: {document.processing_error}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-3 flex items-center gap-2">
                    {document.status === 'failed' && (
                      <button
                        onClick={() => handleReprocess(document.id)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded-md hover:bg-blue-100"
                      >
                        <RefreshCw className="h-3 w-3" />
                        Xử lý lại
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(document.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded-md hover:bg-red-100"
                    >
                      <Trash2 className="h-3 w-3" />
                      Xóa
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
