import { httpClient } from '../../shared/api/httpClient';
import { TransformationConfig } from '../../types/api';

export const transformationsApi = {
  getTransformationRecipes: async (projectId: string): Promise<TransformationConfig[]> => {
    const res = await httpClient.get<TransformationConfig[]>(`/projects/${projectId}/transformations`);
    return res.data;
  },

  applyTransformation: async (
    projectId: string,
    datasetId: string,
    transformationType: string,
    parameters: Record<string, unknown>
  ): Promise<TransformationConfig> => {
    const res = await httpClient.post<TransformationConfig>(`/projects/${projectId}/transformations`, {
      dataset_id: datasetId,
      transformation_type: transformationType,
      parameters,
    });
    return res.data;
  },

  rollbackTransformation: async (projectId: string, stepId: string): Promise<void> => {
    await httpClient.post(`/projects/${projectId}/transformations/${stepId}/rollback`);
  },
};
