import axios from 'axios';

// Vite's dev server proxies /api/* to http://localhost:8000 (see vite.config.js),
// so this works in dev with zero CORS setup. In production, point this at your
// deployed API base URL via an env var instead.
const api = axios.create({ baseURL: '/api' });

export async function uploadVideo(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
  return data; // VideoUploadResponse
}

export async function analyzeVideo(videoId) {
  const { data } = await api.post(`/analyze/${videoId}`);
  return data; // AnalysisResponse
}

export async function getHistory() {
  const { data } = await api.get('/history');
  return data; // HistoryItem[]
}

export async function deleteHistoryItem(videoId) {
  const { data } = await api.delete(`/history/${videoId}`);
  return data;
}

export async function getReport(videoId) {
  const { data } = await api.get(`/report/${videoId}`);
  return data; // VideoWithAnalysis
}

export async function getStats() {
  const { data } = await api.get('/stats');
  return data; // StatsResponse
}

export async function downloadReportPdf(videoId, suggestedFilename) {
  const response = await api.get(`/report/${videoId}/pdf`, { responseType: 'blob' });
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = suggestedFilename || `TrustLens_Report_${videoId.slice(0, 8)}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default api;
