import { useState, useEffect, useMemo, useCallback } from 'react';
import { migrationService } from '../services/migrationService';
import type { MigrationPipeline, DatabaseEngine, MigrationDraftState } from '../types/migration';

export function useMigrationProjects(currentUser: string = 'Aalok') {
  const [pipelines, setPipelines] = useState<MigrationPipeline[]>(() =>
    migrationService.getPipelines()
  );

  useEffect(() => {
    return migrationService.subscribe((updated) => setPipelines(updated));
  }, []);

  const continueWorkingProject = useMemo(
    () => migrationService.getHeroPipeline(currentUser),
    [pipelines, currentUser]
  );

  const draftProjects = useMemo(
    () => pipelines.filter((p) => p.isDraft && !p.isArchived),
    [pipelines]
  );

  const pinnedProjects = useMemo(
    () => pipelines.filter((p) => p.isPinned && !p.isArchived && !p.isDraft),
    [pipelines]
  );

  const regularProjects = useMemo(
    () => pipelines.filter((p) => !p.isPinned && !p.isArchived && !p.isShared && !p.isDraft),
    [pipelines]
  );

  const sharedProjects = useMemo(
    () => pipelines.filter((p) => p.isShared && !p.isArchived && !p.isDraft),
    [pipelines]
  );

  const archivedProjects = useMemo(
    () => pipelines.filter((p) => p.isArchived),
    [pipelines]
  );

  const activeProjectsCount = useMemo(
    () => pipelines.filter((p) => !p.isArchived && !p.isDraft).length,
    [pipelines]
  );

  const togglePin = useCallback((id: string) => migrationService.togglePin(id), []);
  const renameProject = useCallback((id: string, newName: string) => migrationService.renamePipeline(id, newName), []);
  const duplicateProject = useCallback((id: string) => migrationService.duplicatePipeline(id), []);
  const archiveProject = useCallback((id: string) => migrationService.archivePipeline(id), []);
  const unarchiveProject = useCallback((id: string) => migrationService.unarchivePipeline(id), []);
  const deleteProject = useCallback((id: string) => migrationService.deletePipeline(id), []);
  const saveDraft = useCallback(
    (draft: MigrationDraftState) => migrationService.saveDraft(draft, currentUser),
    [currentUser]
  );
  const createProject = useCallback(
    (name: string, sourceEngine: DatabaseEngine, targetEngine: DatabaseEngine, migrationId?: string) =>
      migrationService.createPipeline(name, sourceEngine, targetEngine, currentUser, migrationId),
    [currentUser]
  );
  const touchProject = useCallback((id: string) => migrationService.touchPipeline(id), []);

  return {
    projects: pipelines,
    continueWorkingProject,
    draftProjects,
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
    saveDraft,
    createProject,
    touchProject,
  };
}
