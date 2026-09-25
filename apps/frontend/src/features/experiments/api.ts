import { httpClient } from '../../shared/api/httpClient';
import {
  Experiment,
  ExperimentCreateResponse,
  ModelLeaderboardItem,
  ModelPassport,
} from '../../types/api';

export const experimentsApi = {
  createExperiment: async (
    projectId: string,
    payload: {
      algorithms: string[];
      folds?: number;
      selection_metric?: string;
      selection_direction?: string;
      seed?: number;
      deployment_threshold?: { metric: string; min_value: number };
    }
  ): Promise<ExperimentCreateResponse> => {
    const res = await httpClient.post<ExperimentCreateResponse>(`/projects/${projectId}/experiments`, payload);
    return res.data;
  },

  getExperiment: async (projectId: string, experimentId: string): Promise<Experiment> => {
    const res = await httpClient.get<Experiment>(`/projects/${projectId}/experiments/${experimentId}`);
    return res.data;
  },

  getLeaderboard: async (projectId: string): Promise<ModelLeaderboardItem[]> => {
    const res = await httpClient.get<ModelLeaderboardItem[]>(`/projects/${projectId}/leaderboard`);
    return res.data;
  },

  getModelPassport: async (modelId: string): Promise<ModelPassport> => {
    const res = await httpClient.get<ModelPassport>(`/models/${modelId}/passport`);
    return res.data;
  },

  evaluateLockedTest: async (projectId: string, experimentId: string): Promise<Experiment> => {
    const res = await httpClient.post<Experiment>(`/projects/${projectId}/experiments/${experimentId}/evaluate-locked-test`);
    return res.data;
  },

  freezeExperiment: async (projectId: string, experimentId: string): Promise<Experiment> => {
    const res = await httpClient.post<Experiment>(`/projects/${projectId}/experiments/${experimentId}/freeze`);
    return res.data;
  },

  cancelExperiment: async (projectId: string, experimentId: string): Promise<Experiment> => {
    const res = await httpClient.post<Experiment>(`/projects/${projectId}/experiments/${experimentId}/cancel`);
    return res.data;
  },
};
