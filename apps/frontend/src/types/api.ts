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
  is_two_factor_enabled?: boolean;
  created_at?: string;
}

export interface Project {
  id: UUID;
  project_name?: string;
  name?: string;
  target_column: string | null;
  task_type: TaskType;
  pipeline_stage: PipelineStage;
  data_quality_index: number | null;
  task_type_confidence?: string | null;
  owner_id?: UUID;
  created_at?: string;
  updated_at?: string;
  [key: string]: any;
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
  version_number?: number;
  file_path?: string;
  row_count: number;
  column_count: number;
  content_hash?: string;
  created_at?: string;
  [key: string]: any;
}

export interface DatasetColumn {
  id?: UUID;
  dataset_id?: UUID;
  column_name: string;
  data_type: 'NUMERIC' | 'CATEGORICAL' | 'DATETIME' | 'BOOLEAN' | 'TEXT' | 'MIXED' | string;
  unique_count?: number;
  missing_percentage?: number | string;
  is_target?: boolean;
  [key: string]: any;
}

export interface DatasetProfile {
  dataset_id?: UUID;
  row_count?: number;
  column_count?: number;
  missing_cells?: number;
  missing_percentage?: number;
  duplicate_rows?: number;
  data_quality_index?: number;
  column_summaries?: Record<string, any>;
  recommendations?: Recommendation[];
  [key: string]: any;
}

export type ProfileInfo = DatasetProfile;

export interface DatasetSplit {
  id: UUID;
  dataset_id?: UUID;
  split_type?: 'DEVELOPMENT' | 'LOCKED_TEST' | string;
  split_seed?: number;
  row_indices?: number[];
  development_rows?: number;
  locked_test_rows?: number;
  split_ratio?: number;
  created_at?: string;
  [key: string]: any;
}

export type SplitResponse = DatasetSplit;

export interface SubScores {
  missingness?: number | null;
  duplicate_rate?: number | null;
  outlier_prevalence?: number | null;
  type_consistency?: number | null;
}

export interface EffectiveWeights {
  missingness?: number | null;
  duplicate_rate?: number | null;
  outlier_prevalence?: number | null;
  type_consistency?: number | null;
}

export interface DataQualityIndex {
  overall_index: number;
  sub_scores: SubScores;
  effective_weights: EffectiveWeights;
}

export interface Recommendation {
  id: UUID;
  project_id?: UUID;
  finding?: string;
  evidence?: string;
  recommended_action?: string;
  risk_note?: string;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  status?: 'SUGGESTED' | 'APPLIED' | 'IGNORED' | string;
  created_at?: string;
  [key: string]: any;
}

export type RecommendationItem = Recommendation;
export type TransformationRecommendation = Recommendation;

export type TaskTypeConfidence = 'HIGH' | 'MEDIUM' | 'AMBIGUOUS' | 'LOW';

export interface TaskTypeSuggestion {
  target_column: string;
  suggested_task_type: TaskType;
  confidence: TaskTypeConfidence;
  is_ambiguous: boolean;
  unique_count?: number;
  unique_ratio?: number;
  sample_values?: (string | number)[];
}

export interface TransformationConfig {
  id?: UUID;
  project_id?: UUID;
  column_name?: string;
  missing_value_strategy?: string | null;
  encoding_strategy?: string | null;
  scaling_strategy?: string | null;
  outlier_strategy?: string | null;
  is_active?: boolean;
  [key: string]: any;
}

export type ColumnTransformationConfig = TransformationConfig;

export interface FeatureImportanceItem {
  column_name: string;
  avg_rank_score?: number;
  importance_score?: number;
  stability_score?: number;
  rank?: number;
  is_selected: boolean;
  [key: string]: any;
}

export interface FeatureImportanceResponse {
  project_id?: UUID;
  experiment_id?: UUID | null;
  features: FeatureImportanceItem[];
  selection_threshold?: number;
  total_features?: number;
  selected_count?: number;
}

export interface ExperimentCreateResponse {
  experiment_id: UUID;
  status: string;
  task_type?: string | null;
  fold_count?: number | null;
  cv_seed?: number | null;
  selection_metric?: string | null;
  selection_direction?: string | null;
  message: string;
}

export interface Experiment {
  id: UUID;
  experiment_id?: UUID;
  project_id?: UUID;
  experiment_name?: string;
  name?: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | string;
  selection_metric?: string;
  selection_direction?: 'MINIMIZE' | 'MAXIMIZE' | string;
  winning_model_id?: UUID | null;
  selected_model_id?: UUID | null;
  deployment_threshold_frozen_at_creation?: boolean;
  task_type?: string;
  fold_count?: number;
  created_at?: string;
  [key: string]: any;
}

export interface TrainedModel {
  id: UUID;
  experiment_id: UUID;
  algorithm_name: string;
  hyperparameters?: Record<string, any>;
  status: 'CANDIDATE' | 'DEPLOYABLE' | 'ARTIFACT_VERIFIED' | 'ARTIFACT_INVALID' | string;
  artifact_path?: string | null;
  artifact_checksum?: string | null;
  created_at?: string;
  [key: string]: any;
}

export interface ModelMetric {
  id: UUID;
  model_id: UUID;
  metric_name: string;
  metric_value: number;
  context: 'CROSS_VALIDATION' | 'LOCKED_TEST' | 'HOLD_OUT' | string;
  fold_number?: number | null;
}

export interface ModelLeaderboardItem {
  id?: UUID;
  model_id: UUID;
  algorithm_name: string;
  status: string;
  is_winning_model?: boolean;
  is_selected_champion?: boolean;
  cv_score?: number;
  locked_test_score?: number | null;
  generalization_gap?: number | null;
  metrics?: Record<string, number>;
  hyperparameters?: Record<string, any>;
  created_at?: string;
  [key: string]: any;
}

export type ModelItem = ModelLeaderboardItem;

export interface Leaderboard {
  models?: ModelLeaderboardItem[];
  leaderboard?: ModelLeaderboardItem[];
  winning_model_id?: UUID | null;
  [key: string]: any;
}

export interface WorkspaceSummary {
  total_projects: number;
  active_deployments: number;
  experiments_run: number;
  total_datasets: number;
  [key: string]: any;
}

export interface DeploymentGate {
  id: UUID;
  model_id: UUID;
  locked_test_evaluated: boolean;
  schema_locked: boolean;
  artifact_verified: boolean;
  lineage_complete: boolean;
  performance_threshold_passed: 'PASS' | 'FAIL' | 'UNVERIFIABLE' | string;
  user_approved: boolean;
  approved_by?: UUID | null;
  gate_passed: boolean;
  evaluated_at: string;
}

export interface Deployment {
  id: UUID;
  model_id: UUID;
  endpoint_path: string;
  status: 'DEPLOYED' | 'PAUSED' | 'RETIRED' | 'LIVE' | string;
  deployed_by?: UUID | null;
  deployed_at: string;
  log_retention_days: number;
  [key: string]: any;
}

export interface PredictionResponse {
  prediction: any;
  probabilities?: Record<string, number> | null;
  explanation?: any;
  latency_ms: number;
  model_id?: UUID;
  [key: string]: any;
}

export interface PredictionLog {
  id: UUID;
  deployment_id: UUID;
  request_id: UUID;
  schema_hash: string;
  payload_mode: 'RAW' | 'HASHED' | string;
  input_payload?: Record<string, any> | null;
  prediction_output?: any;
  latency_ms: number;
  explanation_requested?: boolean;
  explanation_latency_ms?: number | null;
  status: 'SUCCESS' | 'VALIDATION_ERROR' | 'SYSTEM_ERROR' | string;
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
  is_selected_champion?: boolean;
  project: {
    id?: UUID;
    name?: string;
    task_type?: string;
    target_column?: string;
    [key: string]: any;
  };
  experiment?: {
    id?: UUID;
    created_at?: string;
    folds?: number;
    selection_metric?: string;
    selection_direction?: string;
    [key: string]: any;
  };
  dataset?: {
    id?: UUID;
    row_count?: number;
    column_count?: number;
    content_hash?: string;
    [key: string]: any;
  } | null;
  metrics?: Array<{
    metric_name: string;
    metric_value: number;
    context?: string;
    [key: string]: any;
  }>;
  generalization_gap?: number | null;
  governance?: {
    artifact_verified?: boolean;
    locked_test_evaluated?: boolean;
    is_deployed?: boolean;
    deployed_endpoint?: string | null;
    [key: string]: any;
  };
  [key: string]: any;
}

export interface SubsystemHealth {
  status: 'UP' | 'DOWN' | 'DEGRADED' | string;
  latency_ms: number;
  details?: Record<string, any>;
}

export interface LivenessResponse {
  status: string;
  service: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface ReadinessResponse {
  status: string;
  ready: boolean;
  service: string;
  dependencies: Record<string, SubsystemHealth>;
  timestamp: string;
}

export interface DetailedHealthResponse {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | string;
  service: string;
  api_version: string;
  code_version: string;
  uptime_seconds: number;
  dependencies: Record<string, SubsystemHealth>;
  timestamp: string;
}

export interface LoginResponse {
  requires_2fa: boolean;
  two_factor_token?: string | null;
  email_masked?: string | null;
  message?: string | null;
  access_token?: string | null;
  refresh_token?: string | null;
  token_type?: string;
  user?: User | null;
}

export interface TwoFactorSetupResponse {
  secret: string;
  otpauth_url: string;
  backup_codes: string[];
}

export interface TwoFactorConfirmRequest {
  secret: string;
  code: string;
  backup_codes?: string[];
}

export interface TwoFactorVerifyLoginRequest {
  two_factor_token: string;
  code: string;
}

export interface TwoFactorResendRequest {
  two_factor_token: string;
}

export interface TwoFactorDisableRequest {
  password: string;
  code: string;
}

export interface TwoFactorStatusResponse {
  is_two_factor_enabled: boolean;
  delivery_method?: string;
  remaining_backup_codes: number;
}


