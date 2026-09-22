import { useState, useEffect } from 'react';
import { projectApi, experimentApi } from '../../../api/client';
import { Project, Experiment, RecommendationItem } from '../../../types/api';

export function useDiagnostics(initialProjectId?: string | null) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(initialProjectId || '');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string>('');
  const [currentExperiment, setCurrentExperiment] = useState<Experiment | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const loadProjects = async () => {
      try {
        setLoading(true);
        const res = await projectApi.list();
        const list = res.data || [];
        setProjects(list);
        if (!selectedProjectId && list.length > 0) {
          setSelectedProjectId(list[0].id);
        }
      } catch (err) {
        setError('Failed to load projects list.');
      } finally {
        setLoading(false);
      }
    };
    loadProjects();
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    const loadData = async () => {
      try {
        setLoading(true);
        const [projRes, recRes, expRes] = await Promise.all([
          projectApi.get(selectedProjectId),
          projectApi.getRecommendations(selectedProjectId).catch(() => ({ data: [] })),
          experimentApi.listByProject(selectedProjectId).catch(() => ({ data: [] })),
        ]);
        setCurrentProject(projRes.data);
        setRecommendations(recRes.data || []);
        const expList = expRes.data || [];
        setExperiments(expList);
        if (expList.length > 0) {
          setSelectedExperimentId(expList[0].id);
        }
      } catch (err) {
        setError('Failed to load project diagnostics.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedExperimentId) {
      setCurrentExperiment(null);
      return;
    }
    const loadExp = async () => {
      try {
        const res = await experimentApi.get(selectedExperimentId);
        setCurrentExperiment(res.data);
      } catch (err) {
        console.warn('Failed to load experiment details', err);
      }
    };
    loadExp();
  }, [selectedExperimentId]);

  return {
    projects,
    selectedProjectId,
    setSelectedProjectId,
    currentProject,
    experiments,
    selectedExperimentId,
    setSelectedExperimentId,
    currentExperiment,
    recommendations,
    loading,
    error,
  };
}
