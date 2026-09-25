import { httpClient } from '../../shared/api/httpClient';
import { Dataset, DatasetColumn, DatasetProfile, DatasetSplit } from '../../types/api';

export const datasetsApi = {
  getDatasets: async (projectId: string): Promise<Dataset[]> => {
    const res = await httpClient.get<Dataset[]>(`/projects/${projectId}/datasets`);
    return res.data;
  },

  uploadDataset: async (projectId: string, file: File): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await httpClient.post<Dataset>(`/projects/${projectId}/datasets/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  getDatasetPreview: async (projectId: string, datasetId: string, limit: number = 50): Promise<Record<string, unknown>[]> => {
    const res = await httpClient.get<Record<string, unknown>[]>(`/projects/${projectId}/datasets/${datasetId}/preview`, {
      params: { limit },
    });
    return res.data;
  },

  getDatasetColumns: async (projectId: string, datasetId: string): Promise<DatasetColumn[]> => {
    const res = await httpClient.get<DatasetColumn[]>(`/projects/${projectId}/datasets/${datasetId}/columns`);
    return res.data;
  },

  getDatasetProfile: async (projectId: string, datasetId: string): Promise<DatasetProfile> => {
    const res = await httpClient.get<DatasetProfile>(`/projects/${projectId}/datasets/${datasetId}/profile`);
    return res.data;
  },

  createDatasetSplit: async (projectId: string, datasetId: string, testRatio: number = 0.2, seed: number = 42, stratify: boolean = true): Promise<DatasetSplit> => {
    const res = await httpClient.post<DatasetSplit>(`/projects/${projectId}/datasets/${datasetId}/splits`, {
      test_ratio: testRatio,
      seed,
      stratify,
    });
    return res.data;
  },

  getDatasetSplits: async (projectId: string, datasetId: string): Promise<DatasetSplit[]> => {
    const res = await httpClient.get<DatasetSplit[]>(`/projects/${projectId}/datasets/${datasetId}/splits`);
    return res.data;
  },
};
