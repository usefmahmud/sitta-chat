import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiClient, type AuthResponse, type AuthUser } from '../lib/api';

interface SessionValue {
  token: string | null;
  user: AuthUser | null;
  api: ApiClient;
  signIn: (auth: AuthResponse) => void;
  signOut: () => void;
}

const SessionContext = createContext<SessionValue | null>(null);

/**
 * The access token lives here and nowhere else: no browser storage, no cookie.
 * A reload therefore lands on /login — the accepted Sprint 1 trade-off.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const tokenRef = useRef<string | null>(null);
  const navigate = useNavigate();

  const signOut = useCallback(() => {
    tokenRef.current = null;
    setToken(null);
    setUser(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  const api = useMemo(
    () =>
      new ApiClient({
        getToken: () => tokenRef.current,
        onUnauthorized: signOut,
      }),
    [signOut],
  );

  const signIn = useCallback(
    (auth: AuthResponse) => {
      tokenRef.current = auth.access_token;
      setToken(auth.access_token);
      setUser(auth.user);
      navigate('/', { replace: true });
    },
    [navigate],
  );

  const value = useMemo<SessionValue>(
    () => ({ token, user, api, signIn, signOut }),
    [token, user, api, signIn, signOut],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error('useSession must be used inside a SessionProvider');
  }
  return value;
}
