/**
 * Native Folder Picker Dialog Service Wrapper
 */
export const dialogService = {
  async pickFolder(defaultPath?: string): Promise<string | null> {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const selected = await open({
        directory: true,
        multiple: false,
        defaultPath: defaultPath || undefined,
        title: 'Select AKAAL Workspace Storage Directory',
      });

      if (typeof selected === 'string') {
        return selected;
      }
      return null;
    } catch (err) {
      console.warn('Native folder dialog failed or cancelled in web fallback mode:', err);
      return null;
    }
  },
};

