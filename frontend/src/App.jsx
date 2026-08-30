import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AlertProvider } from './context/AlertContext';
import Login from './pages/Login';
import CameraManagement from './pages/CameraManagement';
import VideoManagement from './pages/VideoManagement';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-slate-900 flex justify-center items-center text-white">Loading...</div>;
  if (!user) return <Navigate to="/login" />;
  return children;
};

import DashboardOverview from './pages/DashboardOverview';
import LiveMonitor from './pages/LiveMonitor';
import Investigation from './pages/Investigation';
import HelpGuide from './pages/HelpGuide';
import WatchlistManagement from './pages/WatchlistManagement';
import ViewRecords from './pages/ViewRecords';
import Layout from './components/Layout';

const ProtectedLayout = ({ children }) => (
  <ProtectedRoute>
    <Layout>
      {children}
    </Layout>
  </ProtectedRoute>
);

function App() {
  return (
    <AuthProvider>
      <AlertProvider>
        <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedLayout>
                <DashboardOverview />
              </ProtectedLayout>
            } 
          />
          <Route 
            path="/cameras" 
            element={
              <ProtectedLayout>
                <CameraManagement />
              </ProtectedLayout>
            } 
          />
          <Route 
            path="/live" 
            element={
              <ProtectedLayout>
                <LiveMonitor />
              </ProtectedLayout>
            } 
          />
          <Route 
            path="/video" 
            element={
              <ProtectedLayout>
                <VideoManagement />
              </ProtectedLayout>
            } 
          />
          <Route
            path="/search"
            element={
              <ProtectedLayout>
                <Investigation />
              </ProtectedLayout>
            }
          />
          <Route
            path="/records"
            element={
              <ProtectedLayout>
                <ViewRecords />
              </ProtectedLayout>
            }
          />
          <Route
            path="/watchlist"
            element={
              <ProtectedLayout>
                <WatchlistManagement />
              </ProtectedLayout>
            }
          />
          <Route
            path="/guide"
            element={
              <ProtectedLayout>
                <HelpGuide />
              </ProtectedLayout>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </Router>
      </AlertProvider>
    </AuthProvider>
  );
}

export default App;
