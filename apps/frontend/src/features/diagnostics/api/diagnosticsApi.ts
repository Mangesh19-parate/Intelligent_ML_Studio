import { projectApi, experimentApi, modelApi } from '../../../api/client';
import { RecommendationItem } from '../../../types/api';

export const diagnosticsApi = {
  getRecommendations: async (projectId: string): Promise<RecommendationItem[]> => {
    const res = await projectApi.getRecommendations(projectId);
    return res.data || [];
  },

  getExperimentDiagnostics: async (experimentId: string) => {
    const res = await experimentApi.get(experimentId);
    return res.data;
  },

  getModelPassport: async (modelId: string) => {
    const res = await modelApi.getPassport(modelId);
    return res.data;
  },
};
