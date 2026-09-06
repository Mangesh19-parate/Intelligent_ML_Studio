import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/AppLayout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { ProjectDetail } from './pages/ProjectDetail';
import { DeploymentMonitoring } from './pages/DeploymentMonitoring';
import DataStage from './pages/DataStage';
import {
  AnalysisStage,
  TransformationStage,
  FeatureEngineeringStage,
  DiagnosticsStage,
  MLStage,
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
          
          {/* Stage 1: Workspace */}
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

          {/* Stage 2: Data */}
          <Route
            path="/data"
            element={
              <ProtectedRoute>
                <DataStage />
              </ProtectedRoute>
            }
          />

          {/* Stage 3: Data Analysis */}
          <Route
            path="/data-analysis"
            element={
              <ProtectedRoute>
                <AnalysisStage />
              </ProtectedRoute>
            }
          />

          {/* Stage 4: Feature Transformation */}
          <Route
            path="/transformations"
            element={
              <ProtectedRoute>
                <TransformationStage />
              </ProtectedRoute>
            }
          />

          {/* Stage 5: Feature Engineering */}
          <Route
            path="/feature-engineering"
            element={
              <ProtectedRoute>
                <FeatureEngineeringStage />
              </ProtectedRoute>
            }
          />

          {/* Stage 6: Diagnostics */}
          <Route
            path="/diagnostics"
            element={
              <ProtectedRoute>
                <DiagnosticsStage />
              </ProtectedRoute>
            }
          />

          {/* Stage 7: Machine Learning */}
          <Route
            path="/machine-learning"
            element={
              <ProtectedRoute>
                <MLStage />
              </ProtectedRoute>
            }
          />

          {/* Stage 8: Production */}
          <Route
            path="/production"
            element={
              <ProtectedRoute>
                <ProductionStage />
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
          <Route
            path="/monitoring"
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
