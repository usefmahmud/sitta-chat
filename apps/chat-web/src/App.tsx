import { Navigate, Route, Routes } from 'react-router-dom';

import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import { useSession } from './session/SessionProvider';

export default function App() {
  const { token } = useSession();

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={token ? <Navigate to="/" replace /> : <RegisterPage />}
      />
      <Route path="/" element={token ? <HomePage /> : <Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
