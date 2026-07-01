import { useEffect } from 'react';
import { useStore } from '../store/useStore';

export function useTheme() {
  const darkMode = useStore((s) => s.darkMode);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  return { darkMode };
}
