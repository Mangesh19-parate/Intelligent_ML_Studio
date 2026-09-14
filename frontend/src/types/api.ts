/**
 * Authoritative TypeScript API types for Intelligent ML Studio.
 * Synchronized with backend FastAPI schemas and database models.
 */

export type UUID = string;

export type TaskType = 'REGRESSION' | 'CLASSIFICATION' | 'UNSET';
export type PipelineStage = 'INGESTION' | 'PROFILED' | 'SPLIT' | 'TRANSFORMED' | 'FEATURE_SELECTED' | 'EXPERIMENTATION' | 'DEPLOYED';

export type UserRole = 'ADMIN' | 'USER';

export interface User {
  id: UUID;
  email: string;
  full_name: string;
  role: {
    id: UUID;
    role_name: UserRole;
    permissions?: Array<{ id: UUID; permission_key: string }>;
  };
  permissions?: string[];
  is_active: boolean;
  created_at?: string;
}

export interface Project {
  id: UUID;
  project_name: string;
  target_column: string | null;
  task_type: TaskType;
  pipeline_stage: PipelineStage;
  data_quality_index: number | null;
  owner_id: UUID;
  created_at: string;
  updated_at: string;
}

export interface ProjectSnapshot {
  project: Project;
  dataset?: Dataset | null;
  split?: DatasetSplit | null;
  transformations?: TransformationConfig[];
  experiments?: Experiment[];
  deployments?: Deployment[];
}

export interface Dataset {
  id: UUID;
  project_id: UUID;
  version_number: number;
  file_path: string;
  row_count: number;
  column_count: number;
  content_hash: string;
  created_at: string;
}

export interface DatasetColumn {
  id: UUID;
  dataset_id: UUID;
  column_name: string;
  data_type: 'NUMERIC' | 'CATEGORICAL' | 'DATETIME' | 'BOOLEAN' | 'TEXT';
  is_target: boolean;
}

export interface DatasetProfile {
  dataset_id: UUID;
  row_count: number;
  column_count: number;
  missing_cells: number;
  missing_percentage: number;
  duplicate_rows: number;
  data_quality_index: number;
  column_summaries: Record<string, any>;
  recommendations?: Recommendation[];
}

export interface DatasetSplit {
  id: UUID;
  dataset_id: UUID;
  split_type: 'DEVELOPMENT' | 'LOCKED_TEST';
  split_seed: number;
  row_indices: number[];
  created_at: string;
}

export interface Recommendation {
  id: UUID;
  project_id: UUID;
  finding: string;
  evidence: string;
  recommended_action: string;
  risk_note: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'SUGGESTED' | 'APPLIED' | 'IGNORED';
  created_at: string;
}

export interface TransformationConfig {
  id?: UUID;
  project_id: UUID;
  column_name: string;
  missing_value_strategy?: string | null;
  encoding_strategy?: string | null;
  scaling_strategy?: string | null;
  outlier_strategy?: string | null;
  is_active: boolean;
}

export interface FeatureImportanceResponse {
  features: Array<{
    feature_name: string;
    importance_score: number;
    stability_score?: number;
    rank: number;
    is_selected: boolean;
  }>;
  selection_threshold: number;
  total_features: number;
  selected_count: number;
}

export interface Experiment {
  id: UUID;
  project_id: UUID;
  experiment_name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  selection_metric: string;
  selection_direction: 'MINIMIZE' | 'MAXIMIZE';
  winning_model_id?: UUID | null;
  deployment_threshold_frozen_at_creation?: boolean;
  created_at: string;
}

export interface TrainedModel {
  id: UUID;
  experiment_id: UUID;
  algorithm_name: string;
  hyperparameters: Record<string, any>;
  status: 'CANDIDATE' | 'DEPLOYABLE' | 'ARTIFACT_VERIFIED' | 'ARTIFACT_INVALID';
  artifact_path?: string | null;
  artifact_checksum?: string | null;
  created_at: string;
}

export interface ModelMetric {
  id: UUID;
  model_id: UUID;
  metric_name: string;
  metric_value: number;
  context: 'CROSS_VALIDATION' | 'LOCKED_TEST' | 'HOLD_OUT';
  fold_number?: number | null;
}

export interface ModelLeaderboardItem {
  model_id: UUID;
  algorithm_name: string;
  status: string;
  is_winning_model: boolean;
  cv_score: number;
  locked_test_score?: number | null;
  generalization_gap?: number | null;
  metrics: Record<string, number>;
  hyperparameters?: Record<string, any>;
  created_at: string;
}

export interface DeploymentGate {
  id: UUID;
  model_id: UUID;
  locked_test_evaluated: boolean;
  schema_locked: boolean;
  artifact_verified: boolean;
  lineage_complete: boolean;
  performance_threshold_passed: 'PASS' | 'FAIL' | 'UNVERIFIABLE';
  user_approved: boolean;
  approved_by?: UUID | null;
  gate_passed: boolean;
  evaluated_at: string;
}

export interface Deployment {
  id: UUID;
  model_id: UUID;
  endpoint_path: string;
  status: 'DEPLOYED' | 'PAUSED' | 'RETIRED' | 'LIVE';
  deployed_by?: UUID | null;
  deployed_at: string;
  log_retention_days: number;
}

export interface PredictionResponse {
  prediction: any;
  probabilities?: Record<string, number> | null;
  explanation?: Record<string, number> | null;
  latency_ms: number;
  model_id: UUID;
}

export interface PredictionLog {
  id: UUID;
  deployment_id: UUID;
  request_id: UUID;
  schema_hash: string;
  payload_mode: 'RAW' | 'HASHED';
  input_payload?: Record<string, any> | null;
  prediction_output?: any;
  latency_ms: number;
  explanation_requested: boolean;
  explanation_latency_ms?: number | null;
  status: 'SUCCESS' | 'VALIDATION_ERROR' | 'SYSTEM_ERROR';
  requested_at: string;
}

export interface AuditLogRecord {
  id: UUID;
  event_type: string;
  user_id?: UUID | null;
  resource_type?: string | null;
  resource_id?: UUID | null;
  details?: Record<string, any> | null;
  ip_address?: string | null;
  created_at: string;
}

export interface DurableTask {
  task_id: UUID;
  task_type: string;
  experiment_id?: UUID | null;
  project_id?: UUID | null;
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'TIMED_OUT' | 'CANCELLED';
  idempotency_key?: string | null;
  retry_count: number;
  max_retries: number;
  timeout_seconds: number;
  queued_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  failure_reason?: string | null;
}

export interface ModelPassport {
  model_id: UUID;
  algorithm_name: string;
  status: string;
  is_selected_champion: boolean;
  project: {
    id: UUID;
    name: string;
    task_type: string;
  };
  experiment: {
    id: UUID;
    created_at: string;
    folds: number;
    selection_metric: string;
    selection_direction: string;
  };
  dataset?: {
    id: UUID;
    row_count: number;
    column_count: number;
    content_hash: string;
  } | null;
  metrics: Array<{
    metric_name: string;
    metric_value: number;
    context: string;
  }>;
  generalization_gap?: number | null;
  governance: {
    artifact_verified: boolean;
    locked_test_evaluated: boolean;
    is_deployed: boolean;
    deployed_endpoint?: string | null;
  };
}
