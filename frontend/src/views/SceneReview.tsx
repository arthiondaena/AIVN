import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Play, ChevronRight, BookOpen, User } from 'lucide-react';
import { storyApi } from '../services/api';
import type { ChapterWithScenes } from '../types';

export default function SceneReview() {
    const { id } = useParams();
    const storyId = Number(id);

    const [chapters, setChapters] = useState<ChapterWithScenes[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        storyApi.getStoryScenes(storyId)
            .then(setChapters)
            .finally(() => setLoading(false));
    }, [storyId]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-white font-sans">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mb-4 mx-auto" />
                    <p className="text-neutral-600 font-medium">Drafting the screenplay...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-screen bg-neutral-50 font-sans">
            <header className="bg-white border-b border-neutral-200 px-8 py-4 flex justify-between items-center sticky top-0 z-50">
                <div className="flex items-center gap-4">
                    <Link to="/" className="text-neutral-500 font-bold hover:text-neutral-700 transition-colors uppercase tracking-widest text-xs">DASHBOARD</Link>
                    <ChevronRight size={16} className="text-neutral-300" />
                    <h1 className="text-xl font-bold text-neutral-900">Script Review</h1>
                </div>
                <Link 
                    to={`/play/${storyId}`}
                    className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-8 py-3 rounded-full font-bold shadow-lg transform active:scale-95 transition-all"
                >
                    <Play size={20} />
                    Launch Final Game
                </Link>
            </header>

            <div className="flex-1 flex overflow-hidden">
                {/* Navigation Sidebar */}
                <nav className="w-80 bg-white border-r border-neutral-200 overflow-y-auto hidden md:block">
                    <div className="p-6 text-sm">
                        <h2 className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-4">Table of Contents</h2>
                        <ul className="space-y-6">
                            {chapters.map((chapter, i) => (
                                <li key={chapter.id}>
                                    <div className="font-bold text-neutral-900 mb-2 truncate">
                                        CH {i + 1}: {chapter.title || 'Untitled Chapter'}
                                    </div>
                                    <ul className="space-y-1 pl-4 border-l-2 border-neutral-100">
                                        {chapter.scenes.map((scene) => (
                                            <li key={scene.id}>
                                                <a 
                                                    href={`#scene-${scene.id}`} 
                                                    className="block text-xs text-neutral-500 hover:text-primary-600 truncate py-1 transition-colors"
                                                >
                                                    {scene.title}
                                                </a>
                                            </li>
                                        ))}
                                    </ul>
                                </li>
                            ))}
                        </ul>
                    </div>
                </nav>

                {/* Main Content Area */}
                <main className="flex-1 overflow-y-auto p-12 bg-white flex justify-center">
                    <div className="max-w-2xl w-full space-y-24 pb-32">
                        {chapters.map((chapter, i) => (
                            <section key={chapter.id} className="space-y-12">
                                <div className="text-center space-y-2 border-b-2 border-neutral-900 pb-4">
                                    <span className="text-primary-600 font-bold tracking-[0.2em] uppercase text-sm">Chapter {i + 1}</span>
                                    <h2 className="text-3xl font-bold text-neutral-900">{chapter.title || 'Untitled Chapter'}</h2>
                                </div>

                                <div className="space-y-20">
                                    {chapter.scenes.map((scene) => (
                                        <div key={scene.id} id={`scene-${scene.id}`} className="space-y-8 scroll-mt-32">
                                            <div className="flex items-center gap-4 bg-neutral-50 p-4 rounded-lg border border-neutral-100">
                                                <div className="bg-primary-600 text-white w-8 h-8 rounded flex items-center justify-center font-bold text-xs shadow-sm">
                                                    S
                                                </div>
                                                <h3 className="font-bold text-neutral-900">{scene.title}</h3>
                                            </div>

                                            <div className="space-y-6 px-4">
                                                {scene.dialogue?.map((line, idx) => (
                                                    <div key={idx} className="space-y-2">
                                                        <div className="flex items-center gap-2 group">
                                                            <span className="text-xs font-bold text-primary-600 uppercase tracking-widest">
                                                                {line.speaker}
                                                            </span>
                                                            {line.character_pose_expression && (
                                                                <span className="text-[10px] text-neutral-400 italic opacity-0 group-hover:opacity-100 transition-opacity font-mono">
                                                                    [{line.character_pose_expression}]
                                                                </span>
                                                            )}
                                                        </div>
                                                        <p className="text-neutral-700 leading-relaxed font-serif text-lg">
                                                            {line.text}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        ))}
                    </div>
                </main>
            </div>
        </div>
    );
}
