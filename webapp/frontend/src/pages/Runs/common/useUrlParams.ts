// URL search params as page state (filters, compared runs). The router commits navigations in a
// transition (v7_startTransition), so two quick updates — a filter and then a sort, two chips
// removed in a row — would both start from the same stale params and the first would be lost.
// Updates here build on the latest requested params until the router has caught up.
import { useCallback, useLayoutEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export type UpdateParams = (mutate: (params: URLSearchParams) => void) => void;

export function useUrlParams(): [URLSearchParams, UpdateParams] {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const latest = useRef(params);
  useLayoutEffect(() => {
    latest.current = params;
  }, [params]);

  const update = useCallback<UpdateParams>(
    (mutate) => {
      const next = new URLSearchParams(latest.current);
      mutate(next);
      latest.current = next;
      // commas stay readable in deep links (?runs=a,b)
      const search = next.toString().replace(/%2C/gi, ',');
      navigate({ search: search ? `?${search}` : '' }, { replace: true });
    },
    [navigate],
  );
  return [params, update];
}
