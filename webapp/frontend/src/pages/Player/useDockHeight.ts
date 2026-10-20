import { useLayoutEffect, type RefObject } from 'react';

/** Reserve the real responsive transport height without including the overlay tray. */
export function useDockHeight(workspaceRef: RefObject<HTMLDivElement>, dockRef: RefObject<HTMLDivElement>): void {
  useLayoutEffect(() => {
    const dock = dockRef.current;
    const workspace = workspaceRef.current;
    if (!dock || !workspace) return;
    const measure = () => workspace.style.setProperty('--player-dock-h', `${dock.offsetHeight}px`);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(dock);
    return () => observer.disconnect();
  }, [workspaceRef, dockRef]);
}
