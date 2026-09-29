// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Recording } from '../../api/types';
import { resetDemoStore, startDemo, takeDemoResult, useDemoGenerator } from './useDemo';

const rec = { id: 'r1', name: 'demo_crossing' } as Recording;
const json = (body: unknown, status: number) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** fetch of POST /recordings/demo answered by hand; every other request (progress polls) 404s. */
function stubFetch() {
  let answer!: (r: Response) => void;
  const posts: RequestInit[] = [];
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (init?.method === 'POST' && url.endsWith('/recordings/demo')) {
      posts.push(init);
      return new Promise<Response>((r) => (answer = r));
    }
    return Promise.resolve(json({ detail: 'нет' }, 404));
  });
  vi.stubGlobal('fetch', fetchMock);
  return { posts, answer: (r: Response) => answer(r) };
}

beforeEach(() => resetDemoStore());
afterEach(() => vi.unstubAllGlobals());

describe('demo generation store', () => {
  it('runs one generation at a time and hands the result to the page that asked for it', async () => {
    const f = stubFetch();
    const qc = new QueryClient();
    const p1 = startDemo(qc, { scenario: 'crossing', seconds: 5 }, 'upload');
    const p2 = startDemo(qc, { scenario: 'approach', seconds: 15 }, 'overview');
    expect(p2).toBe(p1);
    expect(f.posts).toHaveLength(1);
    const body = JSON.parse(String(f.posts[0].body)) as Record<string, unknown>;
    expect(body).toMatchObject({ scenario: 'crossing', seconds: 5 });
    expect(body.progress_id).toMatch(/^[A-Za-z0-9_-]{8,64}$/);

    f.answer(json(rec, 201));
    await expect(p1).resolves.toEqual(rec);
    expect(takeDemoResult('overview')).toBeNull();
    expect(takeDemoResult('upload')).toEqual(rec);
    expect(takeDemoResult('upload')).toBeNull(); // taken once
  });

  it('shares the running generation between pages; the error goes to the page that asked', async () => {
    const f = stubFetch();
    const qc = new QueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
    const upload = renderHook(() => useDemoGenerator('upload'), { wrapper });
    const overview = renderHook(() => useDemoGenerator('overview'), { wrapper });
    expect(upload.result.current.active).toBeNull();

    let done!: Promise<Recording | null>;
    act(() => {
      done = upload.result.current.generate({ scenario: 'clear', seconds: 10 });
    });
    expect(upload.result.current.active).toEqual({ scenario: 'clear', seconds: 10 });
    expect(overview.result.current.active).toEqual({ scenario: 'clear', seconds: 10 }); // another page sees it

    await act(async () => {
      f.answer(json({ detail: 'Мало места на диске' }, 507));
      await done;
    });
    await waitFor(() => expect(upload.result.current.active).toBeNull());
    expect(upload.result.current.error?.message).toBe('Мало места на диске');
    expect(overview.result.current.error).toBeNull();
    act(() => upload.result.current.dismissError());
    expect(upload.result.current.error).toBeNull();
  });
});
