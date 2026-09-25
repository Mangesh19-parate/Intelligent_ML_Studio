import { httpClient } from '../../shared/api/httpClient';

export const diagnosticsApi = {
  getDatasetDiagnostics: async (projectId: string, datasetId: string): Promise<Record<string, unknown>> => {
    const res = await httpClient.get<Record<string, unknown>>(`/projects/${projectId}/datasets/${datasetId}/diagnostics`);
    return res.data;
  },

  getRecommendations: async (projectId: string, datasetId: string): Promise<Record<string, unknown>[]> => {
    const res = await httpClient.get<Record<string, unknown>[]>(`/projects/${projectId}/datasets/${datasetId}/recommendations`);
    return res.data;
  },

  getExplainability: async (modelId: string): Promise<Record<string, unknown>> => {
    const res = await httpClient.get<Record<string, unknown>>(`/models/${modelId}/explainability`);
    return res.data;
  },
};
