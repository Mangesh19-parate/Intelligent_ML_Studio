import React, { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { ProjectProvider } from './context/ProjectContext';
import { AppLayout } from './components/AppLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { ProjectDetail } from './pages/ProjectDetail';
import { DeploymentMonitoring } from './pages/DeploymentMonitoring';
import DataStage from './pages/DataStage';
import { DataAnalysisStage } from './pages/DataAnalysisStage';
import { FeatureEngineeringStage } from './pages/FeatureEngineeringStage';
import { MLStage } from './pages/MLStage';
import { DiagnosticsStage } from './pages/DiagnosticsStage';
import { TransformationStage } from './pages/TransformationStage';
import { ProductionStage } from './pages/ProductionStage';
import { AdminConsole } from './pages/AdminConsole';
import { NotFound } from './pages/NotFound';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <div className="w-8 h-8 border-3 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const roleName = user.role?.role_name || (typeof user.role === 'string' ? user.role : 'USER');
  if (requiredRole && roleName !== requiredRole) {
    return <Navigate to="/dashboard" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <ProjectProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />

              {/* Workspace */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/workspace"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/projects"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/projects/:id"
                element={
                  <ProtectedRoute>
                    <ProjectDetail />
                  </ProtectedRoute>
                }
              />

              {/* Data Section */}
              <Route
                path="/data"
                element={
                  <ProtectedRoute>
                    <DataStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/data/upload"
                element={
                  <ProtectedRoute>
                    <DataStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/data/datasets"
                element={
                  <ProtectedRoute>
                    <DataStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/data/profiling"
                element={
                  <ProtectedRoute>
                    <DataAnalysisStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/data/cleaning"
                element={
                  <ProtectedRoute>
                    <TransformationStage />
                  </ProtectedRoute>
                }
              />

              {/* Data Analysis Section */}
              <Route
                path="/data-analysis"
                element={
                  <ProtectedRoute>
                    <DataAnalysisStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analysis/eda"
                element={
                  <ProtectedRoute>
                    <DataAnalysisStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analysis/outliers"
                element={
                  <ProtectedRoute>
                    <DataAnalysisStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analysis/imputation"
                element={
                  <ProtectedRoute>
                    <DataAnalysisStage />
                  </ProtectedRoute>
                }
              />

              {/* Transformation Section */}
              <Route
                path="/transformations"
                element={
                  <ProtectedRoute>
                    <TransformationStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/transform"
                element={
                  <ProtectedRoute>
                    <TransformationStage />
                  </ProtectedRoute>
                }
              />

              {/* Feature Engineering & Selection Section */}
              <Route
                path="/feature-engineering"
                element={
                  <ProtectedRoute>
                    <FeatureEngineeringStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/features"
                element={
                  <ProtectedRoute>
                    <FeatureEngineeringStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analysis/feature-selection"
                element={
                  <ProtectedRoute>
                    <FeatureEngineeringStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analysis/feature-engineering"
                element={
                  <ProtectedRoute>
                    <FeatureEngineeringStage />
                  </ProtectedRoute>
                }
              />

              {/* Machine Learning & Experiments Section */}
              <Route
                path="/ml"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ml/training"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ml/experiments"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ml/evaluation"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/machine-learning"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ml/registry"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/leaderboard"
                element={
                  <ProtectedRoute>
                    <MLStage />
                  </ProtectedRoute>
                }
              />

              {/* Intelligence & Diagnostics Section */}
              <Route
                path="/diagnostics"
                element={
                  <ProtectedRoute>
                    <DiagnosticsStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/intelligence/diagnostics"
                element={
                  <ProtectedRoute>
                    <DiagnosticsStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/intelligence/recommendations"
                element={
                  <ProtectedRoute>
                    <DiagnosticsStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/intelligence/explainability"
                element={
                  <ProtectedRoute>
                    <DiagnosticsStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/explainability"
                element={
                  <ProtectedRoute>
                    <DiagnosticsStage />
                  </ProtectedRoute>
                }
              />

              {/* Production Section */}
              <Route
                path="/production"
                element={
                  <ProtectedRoute>
                    <ProductionStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/validation"
                element={
                  <ProtectedRoute>
                    <ProductionStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/production/predictions"
                element={
                  <ProtectedRoute>
                    <ProductionStage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/production/monitoring"
                element={
                  <ProtectedRoute>
                    <DeploymentMonitoring />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/monitoring"
                element={
                  <ProtectedRoute>
                    <DeploymentMonitoring />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/deployments/:id/monitoring"
                element={
                  <ProtectedRoute>
                    <DeploymentMonitoring />
                  </ProtectedRoute>
                }
              />

              {/* Admin Restricted Route */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute requiredRole="ADMIN">
                    <AdminConsole />
                  </ProtectedRoute>
                }
              />

              {/* Catch-all Branded 404 Route */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </ProjectProvider>
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;
