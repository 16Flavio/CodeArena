import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { useAuth } from './AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
// Public auth flow pages stay eager — they're on the critical path for
// first-time visitors and the landing bundle is already small.
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import VerifyEmail from './pages/VerifyEmail';
import Dashboard from './pages/Dashboard';

// Lazy-load the heavier authenticated pages. ContestDetail pulls CodeMirror +
// ReactMarkdown, Admin pulls the whole form tree — splitting these out drops
// the initial bundle significantly.
const Teams = lazy(() => import('./pages/Teams'));
const MySubmissions = lazy(() => import('./pages/MySubmissions'));
const ContestDetail = lazy(() => import('./pages/ContestDetail'));
const Scoreboard = lazy(() => import('./pages/Scoreboard'));
const Presentation = lazy(() => import('./pages/Presentation'));
const Security = lazy(() => import('./pages/Security'));
const Admin = lazy(() => import('./pages/Admin'));
const Learn = lazy(() => import('./pages/Learn'));
const LessonReader = lazy(() => import('./pages/LessonReader'));
const AdminLearning = lazy(() => import('./pages/AdminLearning'));
const AdminLearningWidgets = lazy(() => import('./pages/AdminLearningWidgets'));

function RouteSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function App() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <Suspense fallback={<RouteSpinner />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/my-submissions" element={<MySubmissions />} />
          <Route path="/contests/:id" element={<ContestDetail />} />
          <Route path="/scoreboard/:id" element={<Scoreboard />} />
          <Route path="/scoreboard/:id/presentation" element={<Presentation />} />
          <Route path="/security" element={<Security />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/learn/sections/:slug" element={<Learn />} />
          <Route path="/learn/lessons/:lessonId" element={<LessonReader />} />
          <Route path="/admin/learning" element={<AdminLearning />} />
          <Route path="/admin/learning/widgets" element={<AdminLearningWidgets />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
