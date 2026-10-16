import { httpClient } from '../../shared/api/httpClient';
import { TransformationConfig } from '../../types/api';

export interface TransformationPayload {
  scaling_strategy?: string | null;
  encoding_strategy?: string | null;
  missing_value_strategy?: string | null;
  outlier_strategy?: string | null;
  is_active?: boolean;
}

export interface TransformationPreviewResponse {
  column: string;
  original_sample: any[];
  transformed_sample: any[];
  strategy_applied: string;
}

export const transformationsApi = {
  getTransformationRecipes: async (projectId: string): Promise<TransformationConfig[]> => {
    const res = await httpClient.get<TransformationConfig[]>(
      `/projects/${projectId}/transformations`
    );
    return res.data;
  },

  updateColumnTransformation: async (
    projectId: string,
    column: string,
    payload: TransformationPayload
  ): Promise<TransformationConfig> => {
    const res = await httpClient.put<TransformationConfig>(
      `/projects/${projectId}/transformations/${column}`,
      payload
    );
    return res.data;
  },

  previewTransformation: async (
    projectId: string,
    payload: { column: string; sample_size?: number }
  ): Promise<TransformationPreviewResponse> => {
    const res = await httpClient.post<TransformationPreviewResponse>(
      `/projects/${projectId}/transformations/preview`,
      payload
    );
    return res.data;
  },
};
