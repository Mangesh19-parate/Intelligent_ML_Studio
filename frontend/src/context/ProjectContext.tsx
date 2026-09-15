import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { projectApi } from '../api/client';
import { Project } from '../types/api';

interface ProjectContextType {
  projects: Project[];
  activeProject: Project | null;
  isLoading: boolean;
  error: string | null;
  selectProject: (projectId: string) => void;
  refreshProjects: () => Promise<void>;
  updateActiveProject: (updated: Partial<Project>) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await projectApi.list();
      const list = res.data || [];
      setProjects(list);

      // Restore stored active project or select first
      const storedId = localStorage.getItem('mlstudio_active_project_id');
      if (storedId) {
        const found = list.find((p: Project) => String(p.id) === storedId);
        if (found) {
          setActiveProject(found);
          return;
        }
      }
      if (list.length > 0 && !activeProject) {
        setActiveProject(list[0]);
        localStorage.setItem('mlstudio_active_project_id', String(list[0].id));
      }
    } catch (err: any) {
      console.error('Failed to fetch projects in ProjectContext', err);
      setError(err.response?.data?.detail || 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  }, [activeProject]);

  useEffect(() => {
    fetchProjects();
  }, []);

  const selectProject = useCallback(
    (projectId: string) => {
      const found = projects.find((p) => String(p.id) === projectId);
      if (found) {
        setActiveProject(found);
        localStorage.setItem('mlstudio_active_project_id', projectId);
      }
    },
    [projects]
  );

  const updateActiveProject = useCallback((updated: Partial<Project>) => {
    setActiveProject((prev) => (prev ? { ...prev, ...updated } : null));
    setProjects((prev) =>
      prev.map((p) => (p.id === activeProject?.id ? { ...p, ...updated } : p))
    );
  }, [activeProject]);

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        isLoading,
        error,
        selectProject,
        refreshProjects: fetchProjects,
        updateActiveProject,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = (): ProjectContextType => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
};
