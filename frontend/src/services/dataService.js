import api from './api';

export const searchVehicles = async (params) => {
  const result = await api.get('/search/vehicles', { params });
  return result.data;
};

export const searchDetections = async (params) => {
  const result = await api.get('/search/detections', { params });
  return result.data;
};

export const getAnalyticsSummary = async () => {
  const result = await api.get('/analytics/summary');
  return result.data;
};
