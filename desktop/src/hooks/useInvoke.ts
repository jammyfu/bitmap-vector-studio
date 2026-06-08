import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

interface UseInvokeResult<TArgs extends Record<string, unknown>, TResult> {
  call: (args?: TArgs) => Promise<TResult | null>;
  loading: boolean;
  error: string | null;
  clearError: () => void;
}

/// Generic invoke hook with loading and error states.
/// Wraps Tauri invoke for use inside React components.
export function useInvoke<TArgs extends Record<string, unknown>, TResult>(
  command: string
): UseInvokeResult<TArgs, TResult> {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const call = useCallback(
    async (args?: TArgs): Promise<TResult | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await invoke<TResult>(command, args);
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [command]
  );

  const clearError = useCallback(() => setError(null), []);

  return { call, loading, error, clearError };
}
