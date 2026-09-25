import { httpClient } from '../../shared/api/httpClient';
import { Deployment, PredictionResponse } from '../../types/api';

export const deploymentsApi = {
  getDeployments: async (projectId: string): Promise<Deployment[]> => {
    const res = await httpClient.get<Deployment[]>(`/projects/${projectId}/deployments`);
    return res.data;
  },

  createDeployment: async (
    projectId: string,
    modelId: string,
    payload: {
      deployment_name: string;
      target_environment: 'STAGING' | 'PRODUCTION';
    }
  ): Promise<Deployment> => {
    const res = await httpClient.post<Deployment>(`/projects/${projectId}/models/${modelId}/deployments`, payload);
    return res.data;
  },

  predict: async (deploymentId: string, inputData: Record<string, unknown>[]): Promise<PredictionResponse> => {
    const res = await httpClient.post<PredictionResponse>(`/deployments/${deploymentId}/predict`, {
      instances: inputData,
    });
    return res.data;
  },

  getDeploymentMetrics: async (deploymentId: string): Promise<Record<string, unknown>> => {
    const res = await httpClient.get<Record<string, unknown>>(`/deployments/${deploymentId}/metrics`);
    return res.data;
  },
};
