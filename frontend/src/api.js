import axios from 'axios';

export function getApiError(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map(item => item?.msg || 'Invalid input.').join(' ');
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (typeof error?.response?.data?.message === 'string') return error.response.data.message;
  if (!error?.response) return 'Unable to reach Verve Gate. Check your connection and try again.';
  if (error.response.status >= 500) return 'Verve Gate is temporarily unavailable. Please try again shortly.';
  return fallback;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
});
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('vg_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
