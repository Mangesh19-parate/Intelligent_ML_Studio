import { httpClient } from '../../shared/api/httpClient';
import { Deployment, PredictionResponse } from '../../types/api';

export const deploymentsApi = {
  getDeployments: async (projectId: string): Promise<Deployment[]> => {
    const res = await httpClient.get<Deployment[]>(`/projects/${projectId}/deployments`);
    return res.data;
  },

  createDeployment: async (
    _projectId: string,
    modelId: string
  ): Promise<Deployment> => {
    const res = await httpClient.post<Deployment>(`/models/${modelId}/deploy`);
    return res.data;
  },

  predict: async (
    deploymentId: string,
    inputData: Record<string, unknown>
  ): Promise<PredictionResponse> => {
    const res = await httpClient.post<PredictionResponse>(`/predict/${deploymentId}`, inputData);
    return res.data;
  },

  predictExplain: async (
    deploymentId: string,
    inputData: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    const res = await httpClient.post<Record<string, unknown>>(`/predict/${deploymentId}/explain`, inputData);
    return res.data;
  },

  updateStatus: async (
    deploymentId: string,
    status: string
  ): Promise<Deployment> => {
    const res = await httpClient.put<Deployment>(`/deployments/${deploymentId}/status`, { status });
    return res.data;
  },

  rollback: async (
    deploymentId: string,
    targetDeploymentId: string,
    reason?: string
  ): Promise<Deployment> => {
    const res = await httpClient.post<Deployment>(`/deployments/${deploymentId}/rollback`, {
      target_deployment_id: targetDeploymentId,
      reason,
    });
    return res.data;
  },

  getDeploymentMetrics: async (
    deploymentId: string,
    lookbackHours = 24
  ): Promise<Record<string, unknown>> => {
    const res = await httpClient.get<Record<string, unknown>>(
      `/deployments/${deploymentId}/monitoring?lookback_hours=${lookbackHours}`
    );
    return res.data;
  },

  getDeploymentLogs: async (
    deploymentId: string,
    limit = 50
  ): Promise<Record<string, unknown>[]> => {
    const res = await httpClient.get<Record<string, unknown>[]>(
      `/deployments/${deploymentId}/logs?limit=${limit}`
    );
    return res.data;
  },
};
