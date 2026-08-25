import { useState, useEffect, useCallback } from 'react';
import { themeService, type AppTheme } from '../services/themeService';

export function useTheme() {
  const [theme, setTheme] = useState<AppTheme>(() => themeService.getTheme());

  useEffect(() => {
    return themeService.subscribe((t) => setTheme(t));
  }, []);

  const toggle = useCallback(() => themeService.toggle(), []);

  return { theme, toggle };
}
