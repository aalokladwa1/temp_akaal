import { useEffect, useState, type FC } from 'react';
import { useStartupInitialization } from '../../hooks/useStartupInitialization';
import backgroundImage from '../../assets/akaal-enterprise-bg.svg';
import styles from './SplashScreen.module.css';

export interface SplashScreenProps {
  onComplete: () => void;
}

export const SplashScreen: FC<SplashScreenProps> = ({ onComplete }) => {
  const { initialize } = useStartupInitialization();
  const [statusMessage, setStatusMessage] = useState(
    'Preparing your workspace...'
  );

  useEffect(() => {
    let isMounted = true;

    const runStartupSequence = async () => {
      if (isMounted) setStatusMessage('Preparing your workspace...');
      await new Promise((r) => setTimeout(r, 100));

      if (isMounted) setStatusMessage('Hold on for a moment.');
      await new Promise((r) => setTimeout(r, 100));

      if (isMounted) setStatusMessage('Validating Session Vault...');
      await initialize();

      await new Promise((r) => setTimeout(r, 120));
      if (isMounted) {
        onComplete();
      }
    };

    runStartupSequence();

    return () => {
      isMounted = false;
    };
  }, [initialize, onComplete]);

  return (
    <div className={`enterprise-light-theme ${styles.container}`}>
      <img
        src={backgroundImage}
        alt=""
        aria-hidden="true"
        className={styles.bgImage}
      />
      <div className={styles.card}>
        <h1 className={styles.brandTitle}>AKAAL</h1>
        <p className={styles.subTitle}>Preparing your workspace...</p>
        <div className={styles.spinner} role="status" aria-label="Loading" />
        <p className={styles.statusText}>{statusMessage}</p>
      </div>
    </div>
  );
};
