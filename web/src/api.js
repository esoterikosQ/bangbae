import axios from 'axios';

const api = axios.create({
  baseURL: '/treasury/api',
});

// 요청 시 토큰 자동 첨부
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401 응답 시 로그인 페이지로
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/treasury/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// ── 인증 ──
export const authSetup = () => api.post('/auth/setup');
export const authLogin = (code) => api.post('/auth/login', { code });

// ── 거래 ──
export const getTransactions = (year, month, categoryId) => {
  const params = { year, month };
  if (categoryId) params.category_id = categoryId;
  return api.get('/transactions', { params });
};
export const getTransaction = (id) => api.get(`/transactions/${id}`);
export const createTransaction = (data) => api.post('/transactions', data);
export const updateTransaction = (id, data) => api.put(`/transactions/${id}`, data);
export const deleteTransaction = (id) => api.delete(`/transactions/${id}`);
export const getMonthlySummary = (year, month) =>
  api.get('/transactions/summary', { params: { year, month } });

// ── 분류 ──
export const getCategories = () => api.get('/categories');
export const createCategory = (data) => api.post('/categories', data);
export const updateCategory = (id, data) => api.put(`/categories/${id}`, data);
export const deleteCategory = (id) => api.delete(`/categories/${id}`);

// ── 예산 ──
export const getBudgets = (yearMonth) =>
  api.get('/budgets', { params: { year_month: yearMonth } });
export const getBudgetComparison = (yearMonth) =>
  api.get('/budgets/compare', { params: { year_month: yearMonth } });
export const createBudget = (data) => api.post('/budgets', data);
export const updateBudget = (id, data) => api.put(`/budgets/${id}`, data);
export const deleteBudget = (id) => api.delete(`/budgets/${id}`);

// ── 영수증 ──
export const scanReceipt = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/receipts/scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
};
export const confirmReceipt = (data) => api.post('/receipts/confirm', data);
export const getReceiptItems = (transactionId) =>
  api.get(`/receipts/${transactionId}`);
