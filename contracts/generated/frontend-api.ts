/**
 * Generated TypeScript API Interfaces from OpenAPI Contract.
 */

export interface ProjectContract {
  id: string;
  projectName: string;
  taskType: 'CLASSIFICATION' | 'REGRESSION';
  targetColumn: string;
  createdAt: string;
}

export interface ExperimentContract {
  id: string;
  projectId: string;
  status: string;
  selectionMetric: string;
  selectionDirection: 'MAXIMIZE' | 'MINIMIZE';
  winningModelId?: string;
}

export interface PredictionContract {
  modelId: string;
  features: Record<string, number | string | null>;
  prediction: number | string;
  probabilities?: Record<string, number>;
  latencyMs: number;
}
