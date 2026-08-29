import api from './api';

export const getCameras = async () => {
  const result = await api.get('/cameras/');
  return result.data;
};

export const createCamera = async (data) => {
  const result = await api.post('/cameras/', data);
  return result.data;
};

export const updateCamera = async (id, data) => {
  const result = await api.put(`/cameras/${id}`, data);
  return result.data;
};

export const deleteCamera = async (id) => {
  const result = await api.delete(`/cameras/${id}`);
  return result.data;
};
