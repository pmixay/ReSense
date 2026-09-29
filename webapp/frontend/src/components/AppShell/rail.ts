import { createContext, useContext, useEffect } from 'react';

/** Lets a page add a sub label to its station on the line ("Прогоны / doubleT_obstacle"). */
export const RailContext = createContext<(sub: string | undefined) => void>(() => undefined);

export function useRailSub(sub: string | undefined): void {
  const set = useContext(RailContext);
  useEffect(() => {
    set(sub);
    return () => set(undefined);
  }, [set, sub]);
}
