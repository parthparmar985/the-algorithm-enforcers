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

export const deleteVehicle = async (id) => {
  const result = await api.delete(`/vehicles/${id}`);
  return result.data;
};
