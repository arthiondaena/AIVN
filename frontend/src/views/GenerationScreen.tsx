import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { storyApi } from '../services/api';

export default function GenerationScreen() {
    const { id } = useParams();
    const navigate = useNavigate();
    const storyId = Number(id);

    const [status, setStatus] = useState<'idle' | 'pipeline' | 'converting' | 'success' | 'error'>('idle');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const startGeneration = async () => {
            setStatus('pipeline');
            try {
                // 1. Run full pipeline (LLM scenes + poses + backgrounds + audio)
                await storyApi.generatePipeline(storyId);
                
                // 2. Convert to screenplay.json
                setStatus('converting');
                await storyApi.convertStory(storyId);
                
                setStatus('success');
                // Auto-redirect to review after a short delay
                setTimeout(() => navigate(`/story/${storyId}/review`), 2000);
            } catch (err: any) {
                console.error('Generation failed:', err);
                setStatus('error');
                setError(err.response?.data?.detail || 'An unexpected error occurred during generation.');
            }
        };

        startGeneration();
    }, [storyId, navigate]);

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-neutral-950 text-white overflow-hidden relative font-sans">
            {/* Animated Background Pulse */}
            <div className="absolute inset-0 overflow-hidden opacity-20 pointer-events-none">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-primary-500/30 rounded-full blur-[120px] animate-pulse" />
            </div>

            <div className="relative z-10 max-w-lg w-full text-center space-y-8">
                {status === 'error' ? (
                    <div className="space-y-4">
                        <AlertCircle size={80} className="mx-auto text-rose-500" />
                        <h1 className="text-3xl font-bold">Production Halted</h1>
                        <p className="text-neutral-400 leading-relaxed bg-neutral-900 p-4 rounded-xl border border-neutral-800">
                            {error}
                        </p>
                        <button 
                            onClick={() => window.location.reload()}
                            className="bg-white text-neutral-900 px-8 py-3 rounded-full font-bold hover:bg-neutral-200 transition-colors shadow-lg"
                        >
                            Retry Production
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="relative inline-block">
                            {status === 'success' ? (
                                <CheckCircle2 size={120} className="text-emerald-400 animate-bounce" />
                            ) : (
                                <Loader2 size={120} className="text-primary-400 animate-spin" />
                            )}
                        </div>

                        <div className="space-y-4">
                            <h1 className="text-4xl font-bold tracking-tight">
                                {status === 'pipeline' && 'AI Production Studio'}
                                {status === 'converting' && 'Packaging Assets'}
                                {status === 'success' && 'Production Complete!'}
                            </h1>
                            <p className="text-neutral-400 text-lg leading-relaxed px-4">
                                {status === 'pipeline' && 'Generative models are currently writing dialogue, rendering character poses, and composing music...'}
                                {status === 'converting' && 'Linking all generated scenes and assets into the final game script...'}
                                {status === 'success' && 'Your visual novel is ready for review and play.'}
                            </p>
                        </div>

                        <div className="space-y-3 pt-8">
                            <Step 
                                label="Story Outline Approval" 
                                status="complete" 
                            />
                            <Step 
                                label="Script & Dialogue Writing" 
                                status={status === 'pipeline' ? 'loading' : status === 'idle' ? 'pending' : 'complete'} 
                            />
                            <Step 
                                label="Asset Generation (Sprites & BGs)" 
                                status={status === 'pipeline' ? 'loading' : status === 'idle' ? 'pending' : 'complete'} 
                            />
                            <Step 
                                label="Final Script Conversion" 
                                status={status === 'converting' ? 'loading' : (status === 'success' ? 'complete' : 'pending')} 
                            />
                        </div>

                        <div className="pt-12 text-sm text-neutral-500 italic font-mono">
                            Do not close this window. Heavy lifting in progress.
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

function Step({ label, status }: { label: string, status: 'complete' | 'loading' | 'pending' }) {
    return (
        <div className="flex items-center justify-between bg-white/5 border border-white/10 px-6 py-4 rounded-2xl backdrop-blur-sm transition-all">
            <span className={`font-medium ${status === 'pending' ? 'text-neutral-500' : 'text-neutral-200'}`}>{label}</span>
            {status === 'complete' && <CheckCircle2 size={20} className="text-emerald-400" />}
            {status === 'loading' && <Loader2 size={20} className="text-primary-400 animate-spin" />}
            {status === 'pending' && <div className="w-5 h-5 rounded-full border-2 border-neutral-700" />}
        </div>
    );
}
