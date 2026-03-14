import { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { Save, Sparkles, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import { storyApi } from '../services/api';
import type { MainStoryOutline, StoryOutlineResponse } from '../types';

export default function OutlineEditor() {
    const { id } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const storyId = Number(id);

    const [outline, setOutline] = useState<MainStoryOutline | null>(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (location.state) {
            const data = location.state as StoryOutlineResponse;
            setOutline(data.outline);
        } else {
            // In a real app, we'd fetch the outline here if not passed in state
            // For now, redirecting to dashboard if no data
            navigate('/');
        }
    }, [location.state, navigate]);

    if (!outline) return null;

    const handleSave = async (redirect = false) => {
        setSaving(true);
        try {
            await storyApi.updateOutline(storyId, outline);
            if (redirect) {
                navigate(`/story/${storyId}/generating`);
            }
        } catch (error) {
            console.error('Failed to save outline:', error);
        } finally {
            setSaving(false);
        }
    };

    const updateChapter = (index: number, field: string, value: string) => {
        const newChapters = [...outline.main_chapters];
        newChapters[index] = { ...newChapters[index], [field]: value };
        setOutline({ ...outline, main_chapters: newChapters });
    };

    return (
        <div className="flex flex-col h-screen bg-neutral-50">
            <header className="flex justify-between items-center px-6 py-4 border-b border-neutral-200 bg-white">
                <div className="flex items-center gap-4">
                    <h1 className="text-xl font-bold text-neutral-900">{outline.title}</h1>
                    <div className="flex bg-neutral-100 rounded-lg p-1">
                        <div className="flex items-center gap-2 px-4 py-1.5 rounded-md font-bold text-sm bg-white shadow-sm text-primary-600">
                            <BookOpen size={16} />
                            Story & Chapters
                        </div>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button 
                        onClick={() => handleSave()}
                        disabled={saving}
                        className="flex items-center gap-2 px-4 py-2 text-neutral-600 font-bold hover:bg-neutral-100 rounded-lg"
                    >
                        <Save size={18} />
                        {saving ? 'Saving...' : 'Save Draft'}
                    </button>
                    <button 
                        onClick={() => handleSave(true)}
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-lg shadow-sm"
                    >
                        <Sparkles size={18} />
                        Generate Full Game
                    </button>
                </div>
            </header>

            <main className="flex-1 overflow-y-auto p-8">
                <div className="max-w-4xl mx-auto space-y-12">
                    <div className="bg-primary-50 border border-primary-100 text-primary-800 px-4 py-3 rounded-lg text-sm flex items-center gap-3">
                        <Sparkles size={18} className="text-primary-600 flex-shrink-0" />
                        <p><strong>You can edit the Outline!</strong> Feel free to adjust the title, logline, or chapter summaries below before generating the full game.</p>
                    </div>
                    <section className="space-y-6">
                        <div>
                            <label className="block text-xs font-bold text-neutral-400 uppercase tracking-wider mb-2">Title</label>
                            <input 
                                className="w-full text-3xl font-bold text-neutral-900 border-none outline-none focus:ring-0 p-0 bg-transparent"
                                value={outline.title}
                                onChange={(e) => setOutline({...outline, title: e.target.value})}
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-neutral-400 uppercase tracking-wider mb-2">Logline</label>
                            <textarea 
                                className="w-full text-lg text-neutral-600 border-none outline-none focus:ring-0 p-0 resize-none h-20 bg-transparent"
                                value={outline.logline}
                                onChange={(e) => setOutline({...outline, logline: e.target.value})}
                            />
                        </div>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-neutral-900 mb-6">Chapters</h2>
                        <div className="space-y-4">
                            {outline.main_chapters.map((chapter, idx) => (
                                <div key={chapter.chapter_id} className="border border-neutral-200 rounded-xl overflow-hidden bg-white">
                                    <div className="bg-neutral-50 px-6 py-4 flex justify-between items-center cursor-pointer border-b border-neutral-200">
                                        <div className="flex items-center gap-3 w-full">
                                            <span className="text-neutral-400 font-mono text-sm whitespace-nowrap">CH {idx + 1}</span>
                                            <input 
                                                className="font-bold text-neutral-900 bg-transparent border-none outline-none focus:ring-0 p-0 flex-1"
                                                value={chapter.title}
                                                onChange={(e) => updateChapter(idx, 'title', e.target.value)}
                                            />
                                        </div>
                                        <div className="flex items-center gap-2 text-neutral-400 pl-4">
                                            <span className="text-xs whitespace-nowrap">{chapter.primary_location}</span>
                                            <ChevronDown size={18} />
                                        </div>
                                    </div>
                                    <div className="p-6">
                                        <label className="block text-xs font-bold text-neutral-400 uppercase mb-2">Chapter Summary</label>
                                        <textarea 
                                            className="w-full text-neutral-600 text-sm leading-relaxed border-none outline-none focus:ring-0 p-0 resize-none h-32 bg-transparent"
                                            value={chapter.plot_summary}
                                            onChange={(e) => updateChapter(idx, 'plot_summary', e.target.value)}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}

