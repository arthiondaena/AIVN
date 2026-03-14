import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PlusCircle, Play, BookOpen, Edit3 } from 'lucide-react';
import { storyApi } from '../services/api';
import type { StorySummary } from '../types';

export default function Dashboard() {
    const [stories, setStories] = useState<StorySummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        storyApi.listStories()
            .then(setStories)
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="container mx-auto px-4 py-8">
            <header className="flex justify-between items-center mb-12">
                <div>
                    <h1 className="text-4xl font-bold text-neutral-900">My Stories</h1>
                    <p className="text-neutral-600">Create and manage your AI-powered visual novels</p>
                </div>
                <Link 
                    to="/create/setup"
                    className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors shadow-md"
                >
                    <PlusCircle size={20} />
                    Create New Story
                </Link>
            </header>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="bg-white rounded-xl h-48 animate-pulse shadow-sm border border-neutral-200" />
                    ))}
                </div>
            ) : stories.length === 0 ? (
                <div className="text-center py-20 bg-white rounded-2xl border-2 border-dashed border-neutral-200">
                    <h2 className="text-xl font-medium text-neutral-600 mb-4">No stories yet. Start by creating one!</h2>
                    <Link 
                        to="/create/setup"
                        className="text-primary-600 font-semibold hover:underline"
                    >
                        Create your first story →
                    </Link>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {stories.map(story => (
                        <div key={story.id} className="bg-white rounded-xl shadow-sm border border-neutral-200 overflow-hidden hover:shadow-md transition-shadow">
                            <div className="p-6">
                                <div className="flex justify-between items-start mb-2">
                                    <h2 className="text-xl font-bold text-neutral-900 truncate pr-4">
                                        {story.title || "Untitled Story"}
                                    </h2>
                                    <span className="bg-primary-100 text-primary-700 text-xs font-bold px-2 py-1 rounded uppercase tracking-wider">
                                        {story.style}
                                    </span>
                                </div>
                                <p className="text-neutral-600 line-clamp-2 text-sm mb-6 h-10">
                                    {story.logline || "No logline provided."}
                                </p>
                                <div className="mt-auto">
                                    <Link 
                                        to={`/play/${story.id}`}
                                        className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-bold transition-all shadow-sm hover:shadow-md active:scale-[0.98]"
                                        title="Play Game"
                                    >
                                        <Play size={20} />
                                        PLAY GAME
                                    </Link>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
