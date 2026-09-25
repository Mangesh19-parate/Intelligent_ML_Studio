import { httpClient } from '../../shared/api/httpClient';
import { Project, ProjectSnapshot } from '../../types/api';

export const projectsApi = {
  getProjects: async (skip: number = 0, limit: number = 100): Promise<Project[]> => {
    const res = await httpClient.get<Project[]>('/projects', {
      params: { skip, limit },
    });
    return res.data;
  },

  getProject: async (projectId: string): Promise<Project> => {
    const res = await httpClient.get<Project>(`/projects/${projectId}`);
    return res.data;
  },

  getProjectSnapshot: async (projectId: string): Promise<ProjectSnapshot> => {
    const res = await httpClient.get<ProjectSnapshot>(`/projects/${projectId}/snapshot`);
    return res.data;
  },

  createProject: async (projectName: string, taskType?: string, targetColumn?: string): Promise<Project> => {
    const res = await httpClient.post<Project>('/projects', {
      project_name: projectName,
      task_type: taskType,
      target_column: targetColumn,
    });
    return res.data;
  },

  updateProject: async (projectId: string, payload: Partial<Project>): Promise<Project> => {
    const res = await httpClient.patch<Project>(`/projects/${projectId}`, payload);
    return res.data;
  },

  deleteProject: async (projectId: string): Promise<void> => {
    await httpClient.delete(`/projects/${projectId}`);
  },

  transitionPipelineStage: async (projectId: string, targetStage: string): Promise<Project> => {
    const res = await httpClient.post<Project>(`/projects/${projectId}/transition`, {
      target_stage: targetStage,
    });
    return res.data;
  },
};
