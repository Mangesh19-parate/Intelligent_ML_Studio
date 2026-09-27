export interface AlgorithmOption {
  id: string;
  name: string;
  tag: string;
  description: string;
}

export const REGRESSION_ALGORITHMS: AlgorithmOption[] = [
  {
    id: 'LinearRegression',
    name: 'Linear Regression',
    tag: 'Baseline',
    description: 'Ordinary Least Squares baseline without regularization.',
  },
  {
    id: 'Ridge',
    name: 'Ridge Regression',
    tag: 'L2 Regularized',
    description: 'Linear model with L2 regularization to prevent multicollinearity.',
  },
  {
    id: 'RandomForestRegressor',
    name: 'Random Forest Regressor',
    tag: 'Non-Linear Ensemble',
    description: 'Ensemble of decision trees with bootstrap aggregation.',
  },
];

export const CLASSIFICATION_ALGORITHMS: AlgorithmOption[] = [
  {
    id: 'LogisticRegression',
    name: 'Logistic Regression',
    tag: 'Baseline',
    description: 'Log-odds linear classifier baseline.',
  },
  {
    id: 'RandomForestClassifier',
    name: 'Random Forest Classifier',
    tag: 'Non-Linear Ensemble',
    description: 'Bagging ensemble of decision tree classifiers.',
  },
  {
    id: 'GradientBoostingClassifier',
    name: 'Gradient Boosting Classifier',
    tag: 'Sequential Boosting',
    description: 'Sequential boosting ensemble minimizing pseudo-residual loss.',
  },
];
