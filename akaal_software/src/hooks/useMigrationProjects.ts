import { useState, useEffect, useMemo, useCallback } from 'react';
import { migrationService } from '../services/migrationService';
import type { MigrationProject } from '../types/migration';

export function useMigrationProjects(currentUser: string = 'Aalok') {
  const [projects, setProjects] = useState<MigrationProject[]>(() =>
    migrationService.getProjects()
  );

  useEffect(() => {
    return migrationService.subscribe((updated) => setProjects(updated));
  }, []);

  const continueWorkingProject = useMemo(
    () => migrationService.getContinueWorkingProject(currentUser),
    [projects, currentUser]
  );

  const pinnedProjects = useMemo(
    () => projects.filter((p) => p.isPinned && !p.isArchived),
    [projects]
  );

  const regularProjects = useMemo(
    () => projects.filter((p) => !p.isPinned && !p.isArchived && !p.isShared),
    [projects]
  );

  const sharedProjects = useMemo(
    () => projects.filter((p) => p.isShared && !p.isArchived),
    [projects]
  );

  const archivedProjects = useMemo(
    () => projects.filter((p) => p.isArchived),
    [projects]
  );

  const activeProjectsCount = useMemo(
    () => projects.filter((p) => !p.isArchived).length,
    [projects]
  );

  const togglePin = useCallback((id: string) => migrationService.togglePin(id), []);
  const renameProject = useCallback((id: string, newName: string) => migrationService.renameProject(id, newName), []);
  const duplicateProject = useCallback((id: string) => migrationService.duplicateProject(id), []);
  const archiveProject = useCallback((id: string) => migrationService.archiveProject(id), []);
  const unarchiveProject = useCallback((id: string) => migrationService.unarchiveProject(id), []);
  const deleteProject = useCallback((id: string) => migrationService.deleteProject(id), []);
  const createProject = useCallback(
    (name: string, sourceDb: string, targetDb: string) =>
      migrationService.createProject(name, sourceDb, targetDb, currentUser),
    [currentUser]
  );
  const touchProject = useCallback((id: string) => migrationService.touchProject(id), []);

  return {
    projects,
    continueWorkingProject,
    pinnedProjects,
    regularProjects,
    sharedProjects,
    archivedProjects,
    activeProjectsCount,
    togglePin,
    renameProject,
    duplicateProject,
    archiveProject,
    unarchiveProject,
    deleteProject,
    createProject,
    touchProject,
  };
}
