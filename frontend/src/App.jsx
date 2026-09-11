import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
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
import {
  AnalysisStage,
  TransformationStage,
  ProductionStage,
} from './pages/StagePlaceholders';
import { AdminConsole } from './pages/AdminConsole';

const ProtectedRoute = ({ children, requiredRole }) => {
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

  const roleName = user.role?.role_name || (typeof user.role === 'string' ? user.role : 'VIEWER');
  if (requiredRole && roleName !== requiredRole) {
    return <Navigate to="/dashboard" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

export default function App() {
  return (
    <AuthProvider>
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
          <Route
            path="/analysis/feature-engineering"
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
            path="/transformations"
            element={
              <ProtectedRoute>
                <TransformationStage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/feature-engineering"
            element={
              <ProtectedRoute>
                <FeatureEngineeringStage />
              </ProtectedRoute>
            }
          />

          {/* Intelligence Section */}
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
                <MLStage />
              </ProtectedRoute>
            }
          />

          {/* Machine Learning Section */}
          <Route
            path="/machine-learning"
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

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
