export interface DiagnosticCheck {
  id: string;
  name: string;
  category: 'LEAKAGE' | 'DISTRIBUTION' | 'MISSINGNESS' | 'STABILITY';
  status: 'PASSED' | 'WARNING' | 'FAILED';
  description: string;
  remediation?: string;
}

export interface LeakageReport {
  has_leakage: boolean;
  leaked_features: string[];
  test_partition_status: 'LOCKED' | 'CONSUMED' | 'ISOLATED';
  fold_isolation_verified: boolean;
  checks: DiagnosticCheck[];
}

export interface FitDiagnosis {
  model_id: string;
  algorithm_name: string;
  status: 'GOOD_FIT' | 'OVERFITTING' | 'UNDERFITTING' | 'UNSTABLE';
  train_score: number;
  validation_score: number;
  generalization_gap: number;
  recommendation: string;
}
