/**
 * Document API service
 */

import axios from 'axios';
import { Document, DocumentListResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const documentService = {
  /**
   * Upload a document
   */
  upload: async (file: File, onProgress?: (progress: number) => void): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Document>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });

    return response.data;
  },

  /**
   * Get all documents
   */
  getAll: async (skip = 0, limit = 100, status?: string): Promise<DocumentListResponse> => {
    const params: any = { skip, limit };
    if (status) {
      params.status_filter = status;
    }

    const response = await api.get<DocumentListResponse>('/documents/', { params });
    return response.data;
  },

  /**
   * Get a single document by ID
   */
  getById: async (id: number): Promise<Document> => {
    const response = await api.get<Document>(`/documents/${id}`);
    return response.data;
  },

  /**
   * Update document metadata
   */
  update: async (id: number, data: Partial<Document>): Promise<Document> => {
    const response = await api.patch<Document>(`/documents/${id}`, data);
    return response.data;
  },

  /**
   * Delete a document
   */
  delete: async (id: number): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },

  /**
   * Reprocess a document
   */
  reprocess: async (id: number): Promise<Document> => {
    const response = await api.post<Document>(`/documents/${id}/reprocess`);
    return response.data;
  },
};
