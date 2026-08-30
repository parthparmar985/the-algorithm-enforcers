import api from './api';

export const uploadVideo = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const result = await api.post('/video/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return result.data;
};

export const startProcessing = async (cameraId, filePath) => {
  const response = await api.post(`/video/${cameraId}/process?file_path=${encodeURIComponent(filePath)}`);
  return response.data;
};

export const startLiveInference = async (cameraId) => {
  const response = await api.post(`/video/${cameraId}/start-live`);
  return response.data;
};
