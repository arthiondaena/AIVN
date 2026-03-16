import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy } from 'react';

// Static import for home only to ensure something loads immediately
import Landing from './views/Landing';
import Dashboard from './views/Dashboard';

// Lazy imports for others with direct paths
const CreateSetup = lazy(() => import('./views/CreateSetup'));
const OutlineEditor = lazy(() => import('./views/OutlineEditor'));
const GenerationScreen = lazy(() => import('./views/GenerationScreen'));
const SceneReview = lazy(() => import('./views/SceneReview'));
const GamePlayer = lazy(() => import('./views/GamePlayer'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div className="flex h-screen w-screen items-center justify-center">Loading production environment...</div>}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/create/setup" element={<CreateSetup />} />
            <Route path="/story/:id/editor" element={<OutlineEditor />} />
            <Route path="/story/:id/generating" element={<GenerationScreen />} />
            <Route path="/story/:id/review" element={<SceneReview />} />
            <Route path="/play/:id" element={<GamePlayer />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
