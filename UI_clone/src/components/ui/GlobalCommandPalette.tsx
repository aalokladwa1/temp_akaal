'use client';

import React, { useState, useEffect } from 'react';
import { CommandPalette } from './CommandPalette';

import { useRouter } from 'next/navigation';

export function GlobalCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      // "/" key to focus search or open command palette when not typing in input
      if (e.key === '/' && !isInput) {
        e.preventDefault();
        setIsOpen(true);
        return;
      }

      // Ctrl+Shift+F or Cmd+K for Command Search
      if (((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') || ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'f')) {
        e.preventDefault();
        setIsOpen(prev => !prev);
        return;
      }

      // Enterprise navigation shortcuts (Ctrl+Shift+<Letter>)
      if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
        const k = e.key.toLowerCase();
        if (k === 'm') { e.preventDefault(); router.push('/migration-workspace'); }
        else if (k === 'd') { e.preventDefault(); router.push('/databases'); }
        else if (k === 'e') { e.preventDefault(); router.push('/execution-center'); }
        else if (k === 'l') { e.preventDefault(); router.push('/live-monitor'); }
        else if (k === 'r') { e.preventDefault(); router.push('/reports'); }
        else if (k === 'a') { e.preventDefault(); router.push('/agents'); }
        else if (k === 's') { e.preventDefault(); router.push('/settings'); }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [router]);

  return <CommandPalette isOpen={isOpen} onClose={() => setIsOpen(false)} />;
}
