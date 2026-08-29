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
  const result = await api.post(`/video/${cameraId}/process`, null, {
    params: { file_path: filePath }
  });
  return result.data;
};
