import { httpClient } from '../../shared/api/httpClient';
import { FeatureImportanceResponse } from '../../types/api';

export const featureSelectionApi = {
  getFeatureImportance: async (projectId: string, datasetId: string): Promise<FeatureImportanceResponse> => {
    const res = await httpClient.get<FeatureImportanceResponse>(`/projects/${projectId}/features/importance`, {
      params: { dataset_id: datasetId },
    });
    return res.data;
  },

  calculateFeatureImportance: async (projectId: string, datasetId: string, method?: string): Promise<FeatureImportanceResponse> => {
    const res = await httpClient.post<FeatureImportanceResponse>(`/projects/${projectId}/features/importance`, {
      dataset_id: datasetId,
      method: method || 'MUTUAL_INFO',
    });
    return res.data;
  },
};
