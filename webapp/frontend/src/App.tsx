// Routes. Every page is its own lazy chunk; the Player is a fullscreen route outside the AppShell so
// three.js (and its chunk) never loads with the other pages.
import { lazy, Suspense, type ComponentType, type LazyExoticComponent } from 'react';
import { createBrowserRouter, RouterProvider, useRouteError, type RouteObject } from 'react-router-dom';
import { AppShell, PageFallback } from './components/AppShell/AppShell';
import { Button } from './components/Button/Button';
import { ErrorBanner } from './components/ErrorBanner/ErrorBanner';

const Overview = lazy(() => import('./pages/Overview'));
const Upload = lazy(() => import('./pages/Upload'));
const Queue = lazy(() => import('./pages/Queue'));
const Runs = lazy(() => import('./pages/Runs'));
const RunDetail = lazy(() => import('./pages/RunDetail'));
const Player = lazy(() => import('./pages/Player'));
const Compare = lazy(() => import('./pages/Compare'));
const Live = lazy(() => import('./pages/Live'));
const Presets = lazy(() => import('./pages/Presets'));
const About = lazy(() => import('./pages/About'));
const NotFound = lazy(() => import('./pages/NotFound'));
const UiGuide = lazy(() => import('./pages/UiGuide'));

/** Shown instead of a page that threw or whose chunk failed to load (e.g. after a redeploy). */
export function RouteError() {
  const err = useRouteError();
  const chunk = err instanceof Error && /dynamically imported module|Loading chunk|Failed to fetch/i.test(err.message);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 720 }}>
      <ErrorBanner
        title={chunk ? 'Страница не загрузилась' : 'Ошибка на странице'}
        error={chunk ? 'Возможно, приложение обновилось — перезагрузите страницу.' : err}
      />
      <div style={{ display: 'flex', gap: 10 }}>
        <Button variant="dark" icon="retry" onClick={() => window.location.reload()}>
          Перезагрузить
        </Button>
        <Button variant="outline" icon="home" to="/">
          На главную
        </Button>
      </div>
    </div>
  );
}

const page = (C: LazyExoticComponent<ComponentType>): Pick<RouteObject, 'element' | 'errorElement'> => ({
  element: <C />,
  errorElement: <RouteError />,
});

const fullscreen = (C: LazyExoticComponent<ComponentType>): Pick<RouteObject, 'element' | 'errorElement'> => ({
  element: (
    <Suspense fallback={<PageFallback />}>
      <C />
    </Suspense>
  ),
  errorElement: (
    <div style={{ padding: 40 }}>
      <RouteError />
    </div>
  ),
});

export const routes: RouteObject[] = [
  { path: '/player', ...fullscreen(Player) },
  { path: '/player/:runId', ...fullscreen(Player) },
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, ...page(Overview) },
      { path: 'upload', ...page(Upload) },
      { path: 'queue', ...page(Queue) },
      { path: 'runs', ...page(Runs) },
      { path: 'runs/:id', ...page(RunDetail) },
      { path: 'compare', ...page(Compare) },
      { path: 'live', ...page(Live) },
      { path: 'presets', ...page(Presets) },
      { path: 'about', ...page(About) },
      { path: '_ui', ...page(UiGuide) },
      { path: '*', ...page(NotFound) },
    ],
  },
];

const router = createBrowserRouter(routes, {
  future: { v7_relativeSplatPath: true, v7_fetcherPersist: true, v7_normalizeFormMethod: true, v7_partialHydration: true, v7_skipActionErrorRevalidation: true },
});

export default function App() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
