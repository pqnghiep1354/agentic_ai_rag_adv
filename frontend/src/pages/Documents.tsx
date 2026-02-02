/**
 * Documents page - Upload and manage documents
 */

import React, { useState } from 'react';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { DocumentList } from '../components/documents/DocumentList';
import { FileText } from 'lucide-react';

export const Documents: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    // Trigger refresh of document list
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <FileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">
            Quản Lý Tài Liệu
          </h1>
        </div>
        <p className="text-gray-600">
          Tải lên và quản lý các văn bản luật môi trường Việt Nam
        </p>
      </div>

      {/* Upload section */}
      <div className="mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Tải Lên Tài Liệu Mới
          </h2>
          <DocumentUpload onUploadComplete={handleUploadComplete} />
        </div>
      </div>

      {/* Document list section */}
      <div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Tài Liệu Đã Tải Lên
          </h2>
          <DocumentList refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </div>
  );
};
