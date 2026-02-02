/**
 * Document upload component with drag-and-drop
 */

import React, { useState, useCallback } from 'react';
import { Upload, File, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { documentService } from '../../services/documents';

interface UploadFile {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  documentId?: number;
}

interface DocumentUploadProps {
  onUploadComplete?: (documentId: number) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete }) => {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };

  const addFiles = (newFiles: File[]) => {
    const uploadFiles: UploadFile[] = newFiles.map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      progress: 0,
      status: 'pending' as const,
    }));

    setFiles((prev) => [...prev, ...uploadFiles]);

    // Start uploading
    uploadFiles.forEach((uploadFile) => {
      uploadFile.status = 'uploading';
      uploadDocument(uploadFile);
    });
  };

  const uploadDocument = async (uploadFile: UploadFile) => {
    try {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id ? { ...f, status: 'uploading' as const } : f
        )
      );

      const document = await documentService.upload(uploadFile.file, (progress) => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, progress } : f
          )
        );
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: 'success' as const, progress: 100, documentId: document.id }
            : f
        )
      );

      if (onUploadComplete) {
        onUploadComplete(document.id);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Upload failed';

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: 'error' as const, error: errorMessage }
            : f
        )
      );
    }
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <p className="text-lg font-medium text-gray-700 mb-2">
          Kéo thả tài liệu vào đây
        </p>
        <p className="text-sm text-gray-500 mb-4">
          hoặc
        </p>
        <label className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer">
          <input
            type="file"
            className="hidden"
            multiple
            accept=".pdf,.docx,.doc"
            onChange={handleFileSelect}
          />
          Chọn tập tin
        </label>
        <p className="text-xs text-gray-500 mt-4">
          Hỗ trợ: PDF, DOCX (tối đa 50MB)
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">
            Tài liệu đang tải ({files.length})
          </h3>
          <div className="space-y-2">
            {files.map((uploadFile) => (
              <div
                key={uploadFile.id}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg"
              >
                {/* File icon */}
                <div className="flex-shrink-0">
                  {uploadFile.status === 'success' && (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  )}
                  {uploadFile.status === 'error' && (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                  {uploadFile.status === 'uploading' && (
                    <File className="h-5 w-5 text-blue-500 animate-pulse" />
                  )}
                  {uploadFile.status === 'pending' && (
                    <File className="h-5 w-5 text-gray-400" />
                  )}
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {uploadFile.file.name}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{formatFileSize(uploadFile.file.size)}</span>
                    {uploadFile.status === 'error' && (
                      <span className="text-red-600">• {uploadFile.error}</span>
                    )}
                    {uploadFile.status === 'success' && (
                      <span className="text-green-600">• Tải lên thành công</span>
                    )}
                    {uploadFile.status === 'uploading' && (
                      <span className="text-blue-600">• Đang tải {uploadFile.progress}%</span>
                    )}
                  </div>

                  {/* Progress bar */}
                  {uploadFile.status === 'uploading' && (
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${uploadFile.progress}%` }}
                      />
                    </div>
                  )}
                </div>

                {/* Remove button */}
                <button
                  onClick={() => removeFile(uploadFile.id)}
                  className="flex-shrink-0 p-1 hover:bg-gray-100 rounded"
                  disabled={uploadFile.status === 'uploading'}
                >
                  <X className="h-4 w-4 text-gray-400" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
