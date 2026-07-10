export const themeBootstrapScript = `(() => {
  const storageKey = 'ias-theme';
  const root = document.documentElement;
  let resolvedTheme = 'dark';

  try {
    const storedTheme = window.localStorage.getItem(storageKey);
    const hasExplicitTheme = storedTheme === 'light' || storedTheme === 'dark';
    const systemTheme =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
    resolvedTheme = hasExplicitTheme ? storedTheme : systemTheme;
  } catch {
    resolvedTheme = 'dark';
  }

  root.setAttribute('data-theme', resolvedTheme);
  root.style.colorScheme = resolvedTheme;
})();`
