import React, { ReactNode } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AppLayout } from '../components/AppLayout';

import { LandingPage } from '../pages/LandingPage';
import { Login } from '../pages/Login';
import { LegalCenter } from '../pages/legal/LegalCenter';
import { PrivacyPolicy } from '../pages/legal/PrivacyPolicy';
import { TermsOfService } from '../pages/legal/TermsOfService';
import { Dashboard } from '../pages/Dashboard';
import { ProjectDetail } from '../pages/ProjectDetail';
import DataStage from '../pages/DataStage';
import { DataAnalysisStage } from '../pages/DataAnalysisStage';
import { TransformationStage } from '../pages/TransformationStage';
import { FeatureEngineeringStage } from '../pages/FeatureEngineeringStage';
import { MLStage } from '../pages/MLStage';
import { DiagnosticsStage } from '../pages/DiagnosticsStage';
import { ProductionStage } from '../pages/ProductionStage';
import { DeploymentMonitoring } from '../pages/DeploymentMonitoring';
import { AdminConsole } from '../pages/AdminConsole';
import { NotFound } from '../pages/NotFound';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
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

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Landing & Authentication */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/landing" element={<Navigate to="/" replace />} />
      <Route path="/welcome" element={<Navigate to="/" replace />} />
      <Route path="/login" element={<Login />} />

      {/* Legal & Compliance */}
      <Route path="/legal" element={<LegalCenter />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />
      <Route path="/legal/privacy" element={<Navigate to="/privacy" replace />} />
      <Route path="/terms" element={<TermsOfService />} />
      <Route path="/legal/terms" element={<Navigate to="/terms" replace />} />

      {/* Projects & Workspace Core */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/workspace" element={<Navigate to="/dashboard" replace />} />
      <Route path="/projects" element={<Navigate to="/dashboard" replace />} />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <ProjectDetail />
          </ProtectedRoute>
        }
      />

      {/* Pipeline Stage Routes */}
      <Route
        path="/data"
        element={
          <ProtectedRoute>
            <DataStage />
          </ProtectedRoute>
        }
      />
      <Route path="/data/upload" element={<Navigate to="/data" replace />} />
      <Route path="/data/datasets" element={<Navigate to="/data" replace />} />
      <Route path="/data/cleaning" element={<Navigate to="/transformations" replace />} />

      <Route
        path="/data-analysis"
        element={
          <ProtectedRoute>
            <DataAnalysisStage />
          </ProtectedRoute>
        }
      />
      <Route path="/data/profiling" element={<Navigate to="/data-analysis" replace />} />
      <Route path="/analysis/eda" element={<Navigate to="/data-analysis" replace />} />
      <Route path="/analysis/outliers" element={<Navigate to="/data-analysis" replace />} />
      <Route path="/analysis/imputation" element={<Navigate to="/data-analysis" replace />} />

      <Route
        path="/transformations"
        element={
          <ProtectedRoute>
            <TransformationStage />
          </ProtectedRoute>
        }
      />
      <Route path="/transform" element={<Navigate to="/transformations" replace />} />

      <Route
        path="/feature-engineering"
        element={
          <ProtectedRoute>
            <FeatureEngineeringStage />
          </ProtectedRoute>
        }
      />
      <Route path="/features" element={<Navigate to="/feature-engineering" replace />} />
      <Route path="/analysis/feature-selection" element={<Navigate to="/feature-engineering" replace />} />
      <Route path="/analysis/feature-engineering" element={<Navigate to="/feature-engineering" replace />} />

      <Route
        path="/ml"
        element={
          <ProtectedRoute>
            <MLStage />
          </ProtectedRoute>
        }
      />
      <Route path="/ml/training" element={<Navigate to="/ml" replace />} />
      <Route path="/ml/experiments" element={<Navigate to="/ml" replace />} />
      <Route path="/ml/evaluation" element={<Navigate to="/ml" replace />} />
      <Route path="/machine-learning" element={<Navigate to="/ml" replace />} />
      <Route path="/ml/registry" element={<Navigate to="/ml" replace />} />
      <Route path="/leaderboard" element={<Navigate to="/ml" replace />} />

      <Route
        path="/diagnostics"
        element={
          <ProtectedRoute>
            <DiagnosticsStage />
          </ProtectedRoute>
        }
      />
      <Route path="/intelligence/diagnostics" element={<Navigate to="/diagnostics" replace />} />
      <Route path="/intelligence/recommendations" element={<Navigate to="/diagnostics" replace />} />
      <Route path="/intelligence/explainability" element={<Navigate to="/diagnostics" replace />} />
      <Route path="/explainability" element={<Navigate to="/diagnostics" replace />} />

      <Route
        path="/production"
        element={
          <ProtectedRoute>
            <ProductionStage />
          </ProtectedRoute>
        }
      />
      <Route path="/validation" element={<Navigate to="/production" replace />} />
      <Route path="/production/predictions" element={<Navigate to="/production" replace />} />

      <Route
        path="/monitoring"
        element={
          <ProtectedRoute>
            <DeploymentMonitoring />
          </ProtectedRoute>
        }
      />
      <Route path="/production/monitoring" element={<Navigate to="/monitoring" replace />} />
      <Route
        path="/deployments/:id/monitoring"
        element={
          <ProtectedRoute>
            <DeploymentMonitoring />
          </ProtectedRoute>
        }
      />

      {/* Admin Route */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="ADMIN">
            <AdminConsole />
          </ProtectedRoute>
        }
      />

      {/* Catch-all 404 Route */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};
