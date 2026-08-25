import type { FC, MouseEvent } from 'react';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import { Card } from '../../components/Card';
import { PrimaryButton, SecondaryButton } from '../../components/Button';
import { Heading, Body, Caption } from '../../components/Typography';
import styles from './WelcomeScreen.module.css';

export interface WelcomeScreenProps {
  onStartSetup?: () => void;
  onExit?: (e?: MouseEvent) => void;
}

export const defaultExitHandler = async (e?: MouseEvent) => {
  if (e && typeof e.preventDefault === 'function') {
    e.preventDefault();
  }

  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window');
    const appWindow = getCurrentWindow();
    await appWindow.destroy();
    return;
  } catch {
    try {
      const { getCurrentWindow } = await import('@tauri-apps/api/window');
      const appWindow = getCurrentWindow();
      await appWindow.close();
      return;
    } catch {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('exit_app');
        return;
      } catch {
        if (typeof window !== 'undefined') {
          window.close();
        }
      }
    }
  }
};

export const WelcomeScreen: FC<WelcomeScreenProps> = ({
  onStartSetup,
  onExit = defaultExitHandler,
}) => {
  return (
    <div className={`enterprise-light-theme ${styles.container}`}>
      {/* Background Image Integration */}
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.backgroundImage}
      />

      {/* Center Layout Content */}
      <main className={styles.content}>
        {/* Title Section */}
        <div className={styles.titleHeader}>
          <Heading
            as="h2"
            size="welcomeSub"
            weight="regular"
            color="secondary"
            align="center"
            className={styles.welcomeSub}
          >
            Welcome to
          </Heading>
          <Heading
            as="h1"
            size="welcomeTitle"
            weight="bold"
            color="brandEmphasis"
            align="center"
            className={styles.akaalTitle}
          >
            AKAAL
          </Heading>
        </div>

        {/* Enterprise Card */}
        <Card>
          <div className={styles.cardContent}>
            <Body
              size="body"
              weight="medium"
              color="secondary"
              align="center"
              className={styles.subtitle}
            >
              Let's set up your workspace.
            </Body>

            <div className={styles.buttonGroup}>
              <PrimaryButton onClick={onStartSetup}>
                Start Setup
              </PrimaryButton>
              <SecondaryButton onClick={(e) => onExit(e)}>
                Exit
              </SecondaryButton>
            </div>
          </div>
        </Card>
      </main>

      {/* Pinned Footer */}
      <footer className={styles.footer}>
        <Caption className={styles.footerText}>
          AKAAL v0.1.0
        </Caption>
        <Caption className={styles.footerText}>
          Build 20260801
        </Caption>
      </footer>
    </div>
  );
};
