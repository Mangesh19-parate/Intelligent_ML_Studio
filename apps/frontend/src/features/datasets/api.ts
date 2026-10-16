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
    const res = await httpClient.post<Dataset>(`/projects/${projectId}/datasets`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  getDatasetPreview: async (
    _projectId: string,
    datasetId: string,
    limit: number = 50
  ): Promise<Record<string, unknown>[]> => {
    const res = await httpClient.get<{ preview_rows: Record<string, unknown>[] }>(
      `/datasets/${datasetId}/preview?limit=${limit}`
    );
    return res.data?.preview_rows || [];
  },

  getDatasetColumns: async (_projectId: string, datasetId: string): Promise<DatasetColumn[]> => {
    const res = await httpClient.get<DatasetColumn[]>(`/datasets/${datasetId}/columns`);
    return res.data;
  },

  getDatasetProfile: async (projectId: string, _datasetId?: string): Promise<DatasetProfile> => {
    const res = await httpClient.get<DatasetProfile>(`/projects/${projectId}/dataset/profile`);
    return res.data;
  },

  createDatasetSplit: async (
    projectId: string,
    _datasetId: string,
    testRatio: number = 0.2,
    seed: number = 42,
    stratify: boolean = true
  ): Promise<DatasetSplit> => {
    const res = await httpClient.post<DatasetSplit>(`/projects/${projectId}/dataset/split`, {
      test_size: testRatio,
      random_seed: seed,
      stratified: stratify,
    });
    return res.data;
  },

  getDatasetSplits: async (_projectId: string, datasetId: string): Promise<DatasetSplit[]> => {
    const res = await httpClient.get<DatasetSplit[]>(`/datasets/${datasetId}/splits`);
    return res.data;
  },
};
