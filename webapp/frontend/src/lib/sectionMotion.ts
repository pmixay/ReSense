import { createContext, useContext } from 'react';

/** The AppShell's navigation phase ('idle' at rest; 'boarding' while the walk into the cab plays). */
export const SectionMotionContext = createContext<string>('idle');
export const useSectionMotion = () => useContext(SectionMotionContext);

/** Phases in which the routed page exists but is covered by the navigation overlay. */
export const COVERED_PHASES: readonly string[] = ['covered', 'travelling', 'boarding'];
