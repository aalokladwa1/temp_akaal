import {
  useState,
  useMemo,
  useEffect,
  useRef,
  useCallback,
  type FC,
} from 'react';
import type { WorkspaceConfig } from '../../types/workspace';
import { getEnterpriseGreeting } from '../../utils/greetingUtils';
import { useTheme } from '../../hooks/useTheme';
import { useNotifications } from '../../hooks/useNotifications';
import { notificationService } from '../../services/notificationService';
import styles from './Dashboard.module.css';

// ── Types ────────────────────────────────────────────────────

type MigrationStatus = 'running' | 'paused' | 'failed' | 'completed';

interface ActiveMigration {
  id: string;
  name: string;
  status: MigrationStatus;
  progress: number; // 0–100
  lastActiveAgo: string;
}

interface RecentProject {
  id: string;
  name: string;
  status: MigrationStatus;
  progress?: number;
  lastActivity: string;
}

interface Alert {
  id: string;
  title: string;
  sub: string;
  severity: 'warning' | 'error' | 'info';
}

export type NavSection =
  | 'dashboard'
  | 'projects'
  | 'migrations'
  | 'monitoring'
  | 'reports'
  | 'administration'
  | 'settings';

interface SearchDestination {
  id: string;
  title: string;
  category: 'Page' | 'Project';
  targetSection: NavSection;
}

// ── Demo Data ────────────────────────────────────────────────

const DEMO_ACTIVE: ActiveMigration = {
  id: 'mig_001',
  name: 'Oracle → PostgreSQL',
  status: 'running',
  progress: 87,
  lastActiveAgo: '18 minutes ago',
};

const DEMO_RECENT: RecentProject[] = [
  { id: 'p1', name: 'Oracle → PostgreSQL',  status: 'running',   progress: 87, lastActivity: '18m ago'    },
  { id: 'p2', name: 'SQL Server → PostgreSQL', status: 'completed', lastActivity: 'Yesterday'              },
  { id: 'p3', name: 'MongoDB → PostgreSQL', status: 'paused',    progress: 54, lastActivity: '3 days ago' },
];

const DEMO_ALERTS: Alert[] = [
  { id: 'a1', title: 'Validation Pending', sub: 'MongoDB → PostgreSQL requires schema review.', severity: 'warning' },
];

const SEARCH_DESTINATIONS: SearchDestination[] = [
  { id: 'nav-projects',       title: 'Projects',             category: 'Page',    targetSection: 'projects'       },
  { id: 'nav-migrations',     title: 'Migrations',           category: 'Page',    targetSection: 'migrations'     },
  { id: 'nav-monitoring',     title: 'Monitoring',           category: 'Page',    targetSection: 'monitoring'     },
  { id: 'nav-reports',        title: 'Reports',              category: 'Page',    targetSection: 'reports'        },
  { id: 'nav-administration', title: 'Administration',       category: 'Page',    targetSection: 'administration' },
  { id: 'nav-settings',       title: 'Settings',             category: 'Page',    targetSection: 'settings'       },
  { id: 'proj-oracle',        title: 'Oracle → PostgreSQL',  category: 'Project', targetSection: 'migrations'     },
  { id: 'proj-sqlserver',     title: 'SQL Server → PostgreSQL', category: 'Project', targetSection: 'projects'    },
  { id: 'proj-mongodb',       title: 'MongoDB → PostgreSQL', category: 'Project', targetSection: 'projects'       },
];

// ── Helpers ──────────────────────────────────────────────────

function getInitials(name: string): string {
  const parts = name.trim().split(' ');
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ago`;
  if (m > 0) return `${m}m ago`;
  return 'Just now';
}

// ── Sub-components ───────────────────────────────────────────

const StatusTag: FC<{ status: MigrationStatus }> = ({ status }) => {
  const cls = {
    running:   styles.statusTagRunning,
    paused:    styles.statusTagPaused,
    failed:    styles.statusTagFailed,
    completed: styles.statusTagCompleted,
  }[status];
  const labels = { running: 'Running', paused: 'Paused', failed: 'Failed', completed: 'Completed' };
  return <span className={[styles.statusTag, cls].join(' ')}>{labels[status]}</span>;
};

const ProgressBar: FC<{ pct: number; status: MigrationStatus }> = ({ pct, status }) => {
  const fillCls = {
    running:   styles.progressFillRunning,
    paused:    styles.progressFillPaused,
    failed:    styles.progressFillFailed,
    completed: styles.progressFill,
  }[status];
  return (
    <div className={styles.progressTrack}>
      <div className={[styles.progressFill, fillCls].join(' ')} style={{ width: `${pct}%` }} />
    </div>
  );
};

// ── SVG Icons ────────────────────────────────────────────────

const IconDashboard = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="1" y="1" width="6" height="6" rx="1.5" />
    <rect x="9" y="1" width="6" height="6" rx="1.5" />
    <rect x="1" y="9" width="6" height="6" rx="1.5" />
    <rect x="9" y="9" width="6" height="6" rx="1.5" />
  </svg>
);

const IconProjects = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M2 3h12M2 8h8M2 13h10" strokeLinecap="round" />
  </svg>
);

const IconMigrations = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 8h10M10 5l3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const IconMonitoring = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M2 9h3l2-5 3 8 2-4h2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const IconReports = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M4 1.5h5.5L13 5v9.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1z" />
    <path d="M9.5 1.5V5H13" />
    <path d="M5.5 8h5M5.5 11h5" strokeLinecap="round" />
  </svg>
);

const IconAdmin = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="5" r="2.5" />
    <path d="M2 13c0-3 2.7-5 6-5s6 2 6 5" strokeLinecap="round" />
  </svg>
);

const IconSettings = () => (
  <svg className={styles.navIcon} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="8" r="2" />
    <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" strokeLinecap="round" />
  </svg>
);

const IconSearch = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="6.5" cy="6.5" r="4.5" />
    <path d="M10 10l3.5 3.5" strokeLinecap="round" />
  </svg>
);

const IconBell = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 1.5A4.5 4.5 0 0 0 3.5 6v3L2 11h12l-1.5-2V6A4.5 4.5 0 0 0 8 1.5z" strokeLinejoin="round" />
    <path d="M6.5 13a1.5 1.5 0 0 0 3 0" />
  </svg>
);

const IconSun = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="8" cy="8" r="3" />
    <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" strokeLinecap="round" />
  </svg>
);

const IconMoon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M13.5 10A6 6 0 0 1 6 2.5a6 6 0 1 0 7.5 7.5z" strokeLinejoin="round" />
  </svg>
);

const IconNewMigration = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 3v10M3 8h10" strokeLinecap="round" />
  </svg>
);

const IconArrowRight = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ── Main Dashboard Component ──────────────────────────────────

export interface DashboardProps {
  config: WorkspaceConfig;
  onSignOut: () => void;
  onNavigate: (section: NavSection) => void;
}

export const Dashboard: FC<DashboardProps> = ({ config, onSignOut, onNavigate }) => {
  const { theme, toggle: toggleTheme } = useTheme();
  const { history: notifHistory } = useNotifications();

  const [activeNav, setActiveNav] = useState<NavSection>('dashboard');
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchFocusIndex, setSearchFocusIndex] = useState(0);

  const profileRef = useRef<HTMLButtonElement>(null);
  const notifRef = useRef<HTMLButtonElement>(null);
  const searchWrapperRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const greeting = useMemo(
    () => getEnterpriseGreeting(config.ownerDisplayName),
    [config.ownerDisplayName]
  );

  const displayName = config.ownerDisplayName || 'Administrator';
  const initials = useMemo(() => getInitials(displayName), [displayName]);

  // Filtered search results
  const searchResults = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return SEARCH_DESTINATIONS;
    return SEARCH_DESTINATIONS.filter((item) =>
      item.title.toLowerCase().includes(query) ||
      item.category.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  const handleNavClick = useCallback((section: NavSection) => {
    setActiveNav(section);
    onNavigate(section);
    if (section === 'migrations') {
      notificationService.push('Migrations', 'info', '3 migrations are currently active.');
    } else if (section === 'monitoring') {
      notificationService.push('Monitoring', 'info', 'System metrics healthy.');
    }
  }, [onNavigate]);

  const handleSelectSearchResult = useCallback((item: SearchDestination) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    handleNavClick(item.targetSection);
  }, [handleNavClick]);

  // Global Ctrl + K / Cmd + K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifPanel(false);
      }
      if (searchWrapperRef.current && !searchWrapperRef.current.contains(e.target as Node)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Keyboard navigation within search dropdown
  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSearchFocusIndex((prev) => (prev + 1) % Math.max(1, searchResults.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSearchFocusIndex((prev) => (prev - 1 + searchResults.length) % Math.max(1, searchResults.length));
    } else if (e.key === 'Enter' && searchResults.length > 0) {
      e.preventDefault();
      const target = searchResults[searchFocusIndex] || searchResults[0];
      if (target) handleSelectSearchResult(target);
    } else if (e.key === 'Escape') {
      setIsSearchOpen(false);
      searchInputRef.current?.blur();
    }
  };

  const navItems: { id: NavSection; label: string; icon: FC }[] = [
    { id: 'dashboard',      label: 'Dashboard',      icon: IconDashboard   },
    { id: 'projects',       label: 'Projects',        icon: IconProjects    },
    { id: 'migrations',     label: 'Migrations',      icon: IconMigrations  },
    { id: 'monitoring',     label: 'Monitoring',      icon: IconMonitoring  },
    { id: 'reports',        label: 'Reports',         icon: IconReports     },
    { id: 'administration', label: 'Administration',  icon: IconAdmin       },
    { id: 'settings',       label: 'Settings',        icon: IconSettings    },
  ];

  const quickActions: { id: string; label: string; icon: FC; navTarget: NavSection }[] = [
    { id: 'qa-new-migration', label: 'New Migration', icon: IconNewMigration, navTarget: 'migrations' },
    { id: 'qa-projects',      label: 'Projects',      icon: IconProjects,     navTarget: 'projects'   },
    { id: 'qa-monitoring',    label: 'Monitoring',    icon: IconMonitoring,   navTarget: 'monitoring' },
    { id: 'qa-reports',       label: 'Reports',       icon: IconReports,      navTarget: 'reports'    },
  ];

  const hasAlerts = DEMO_ALERTS.length > 0;
  const hasActiveMigration = !!DEMO_ACTIVE;

  return (
    <div className={styles.shell}>
      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarBrand}>
          <span className={styles.sidebarBrandAccent}>AKAAL</span> Desktop
        </div>

        <nav className={styles.sidebarNav} aria-label="Primary navigation">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`nav-${id}`}
              className={[styles.navItem, activeNav === id ? styles.navItemActive : ''].filter(Boolean).join(' ')}
              onClick={() => handleNavClick(id)}
              aria-current={activeNav === id ? 'page' : undefined}
            >
              <Icon />
              {label}
            </button>
          ))}
        </nav>
      </aside>

      {/* ── Main ─────────────────────────────────────────── */}
      <div className={styles.main}>
        {/* ── Top Bar ────────────────────────────────────── */}
        <header className={styles.topbar}>
          {/* Interactive Application Search Bar */}
          <div className={styles.searchBoxWrapper} ref={searchWrapperRef}>
            <div className={styles.searchBox} role="search">
              <IconSearch />
              <input
                ref={searchInputRef}
                className={styles.searchInput}
                placeholder="Search projects, pages..."
                aria-label="Search projects and pages"
                value={searchQuery}
                onFocus={() => setIsSearchOpen(true)}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsSearchOpen(true);
                  setSearchFocusIndex(0);
                }}
                onKeyDown={handleSearchKeyDown}
                id="dashboard-search"
              />
              <span className={styles.searchKbd}>Ctrl K</span>
            </div>

            {isSearchOpen && (
              <div className={styles.searchDropdown} role="listbox">
                {searchResults.length === 0 ? (
                  <div className={styles.searchEmpty}>No matching destinations found</div>
                ) : (
                  searchResults.map((item, idx) => (
                    <button
                      key={item.id}
                      className={[
                        styles.searchItem,
                        idx === searchFocusIndex ? styles.searchItemActive : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => handleSelectSearchResult(item)}
                      onMouseEnter={() => setSearchFocusIndex(idx)}
                      role="option"
                      aria-selected={idx === searchFocusIndex}
                    >
                      <span>{item.title}</span>
                      <span className={styles.searchItemCat}>{item.category}</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          <div className={styles.topbarSpacer} />

          <div className={styles.topbarActions}>
            {/* Theme Toggle */}
            <button
              id="theme-toggle-btn"
              className={styles.iconBtn}
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <IconSun /> : <IconMoon />}
            </button>

            {/* Notifications Bell */}
            <div style={{ position: 'relative' }}>
              <button
                ref={notifRef}
                id="notifications-btn"
                className={styles.iconBtn}
                onClick={() => { setShowNotifPanel((v) => !v); setShowProfileMenu(false); }}
                aria-label="Notifications"
                aria-expanded={showNotifPanel}
              >
                <IconBell />
                {notifHistory.length > 0 && <div className={styles.notifBadge} />}
              </button>

              {showNotifPanel && (
                <div className={styles.notifPanel}>
                  <div className={styles.notifPanelHeader}>
                    <span className={styles.notifPanelTitle}>Notifications</span>
                    {notifHistory.length > 0 && (
                      <button
                        className={styles.notifPanelClear}
                        onClick={() => { notificationService.clearHistory(); }}
                      >
                        Clear all
                      </button>
                    )}
                  </div>
                  <div className={styles.notifPanelList}>
                    {notifHistory.length === 0 ? (
                      <div className={styles.notifPanelEmpty}>No notifications</div>
                    ) : (
                      notifHistory.slice(0, 20).map((n) => (
                        <div key={n.id} className={styles.notifPanelItem}>
                          <div className={[styles.alertDot, n.severity === 'error' ? styles.alertDotError : n.severity === 'warning' ? styles.alertDotWarning : styles.alertDotInfo].join(' ')} />
                          <div className={styles.notifPanelItemBody}>
                            <div className={styles.notifPanelItemTitle}>{n.title}</div>
                            {n.message && <div className={styles.notifPanelItemMsg}>{n.message}</div>}
                            <div className={styles.notifPanelItemTime}>{formatTime(Date.now() - n.createdAt)}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Profile */}
            <div style={{ position: 'relative' }}>
              <button
                ref={profileRef}
                id="profile-btn"
                className={styles.avatar}
                onClick={() => { setShowProfileMenu((v) => !v); setShowNotifPanel(false); }}
                aria-label="Profile menu"
                aria-expanded={showProfileMenu}
              >
                {initials}
              </button>

              {showProfileMenu && (
                <div className={styles.dropdown}>
                  <button className={styles.dropdownItem} onClick={() => setShowProfileMenu(false)}>
                    Profile
                  </button>
                  <button className={styles.dropdownItem} onClick={() => setShowProfileMenu(false)}>
                    Preferences
                  </button>
                  <div className={styles.dropdownDivider} />
                  <button
                    className={`${styles.dropdownItem} ${styles.danger}`}
                    onClick={() => { setShowProfileMenu(false); onSignOut(); }}
                    id="sign-out-btn"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* ── Content ────────────────────────────────────── */}
        <main className={styles.content} id="dashboard-content">
          {/* Greeting */}
          <section className={styles.greeting} aria-label="Greeting">
            <h1 className={styles.greetingTitle}>{greeting.title}</h1>
            <p className={styles.greetingSubtitle}>{greeting.subtitle}</p>
          </section>

          {/* Continue Working — only shown when active migration exists */}
          {hasActiveMigration && (
            <section aria-label="Continue working">
              <div className={styles.sectionHeader}>
                <span className={styles.sectionTitle}>Continue Working</span>
              </div>
              <div className={styles.heroCard}>
                <div className={styles.heroLeft}>
                  <div className={styles.heroMeta}>
                    <StatusTag status={DEMO_ACTIVE.status} />
                    <span className={styles.heroLastActive}>Last active {DEMO_ACTIVE.lastActiveAgo}</span>
                  </div>
                  <div className={styles.heroProjectName}>{DEMO_ACTIVE.name}</div>
                  <div className={styles.heroProgressRow} style={{ marginTop: 14 }}>
                    <div className={styles.heroProgressTrackWrap}>
                      <ProgressBar pct={DEMO_ACTIVE.progress} status={DEMO_ACTIVE.status} />
                    </div>
                    <span className={styles.heroProgress}>{DEMO_ACTIVE.progress}%</span>
                  </div>
                </div>
                <div className={styles.heroRight}>
                  <button
                    id="continue-working-btn"
                    className={styles.resumeBtn}
                    onClick={() => notificationService.push('Migration Resumed', 'success', `${DEMO_ACTIVE.name} is now active.`)}
                  >
                    Resume <IconArrowRight />
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* Quick Actions — Displays ONLY Icon and Title */}
          <section aria-label="Quick actions">
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Quick Actions</span>
            </div>
            <div className={styles.quickActionsGrid}>
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.id}
                    id={action.id}
                    className={styles.quickCard}
                    onClick={() => handleNavClick(action.navTarget)}
                  >
                    <div className={styles.quickCardIcon}><Icon /></div>
                    <div className={styles.quickCardLabel}>{action.label}</div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Needs Attention — only shown when alerts exist */}
          {hasAlerts && (
            <section aria-label="Needs attention">
              <div className={styles.sectionHeader}>
                <span className={styles.sectionTitle}>Needs Attention</span>
              </div>
              <div className={styles.alertList}>
                {DEMO_ALERTS.map((alert) => (
                  <div key={alert.id} className={styles.alertRow}>
                    <div className={[
                      styles.alertDot,
                      alert.severity === 'error'   ? styles.alertDotError :
                      alert.severity === 'warning' ? styles.alertDotWarning :
                      styles.alertDotInfo
                    ].filter(Boolean).join(' ')} />
                    <div className={styles.alertText}>{alert.title}</div>
                    <div className={styles.alertSub}>{alert.sub}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Recent Projects */}
          <section aria-label="Recent projects">
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Recent Projects</span>
              <button className={styles.sectionLink} onClick={() => handleNavClick('projects')}>
                View all →
              </button>
            </div>
            <div className={styles.projectList}>
              {DEMO_RECENT.map((proj) => (
                <div
                  key={proj.id}
                  className={styles.projectRow}
                  role="button"
                  tabIndex={0}
                  onClick={() => notificationService.push(proj.name, 'info', 'Project detail — coming in Sprint 4 Part 2.')}
                  onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.click()}
                >
                  <div className={styles.projectInfo}>
                    <div className={styles.projectName}>{proj.name}</div>
                    <div className={styles.projectMeta}>
                      <StatusTag status={proj.status} />
                    </div>
                  </div>
                  {proj.progress !== undefined && (
                    <div className={styles.projectProgress}>
                      <div className={styles.miniProgressTrack}>
                        <div
                          className={styles.miniProgressFill}
                          style={{ width: `${proj.progress}%` }}
                        />
                      </div>
                      <span className={styles.projectPct}>{proj.progress}%</span>
                    </div>
                  )}
                  <span className={styles.projectLastActive}>{proj.lastActivity}</span>
                </div>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};
