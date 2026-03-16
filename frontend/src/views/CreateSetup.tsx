import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, Dices } from 'lucide-react';
import { storyApi } from '../services/api';
import type { ArtStyle } from '../types';

const ART_STYLES: { value: ArtStyle; label: string; description: string }[] = [
    { value: 'anime', label: 'Anime', description: 'Classic Japanese animation style.' },
    { value: 'american cartoon style', label: 'American Cartoon', description: 'Bold, expressive Western cartooning.' },
    { value: 'western comic style', label: 'Western Comic', description: 'Detailed, cinematic superhero comic vibes.' },
    { value: 'korean manhwa style', label: 'Korean Manhwa', description: 'Clean lines and modern digital webtoon art.' },
    { value: 'chibi style', label: 'Chibi', description: 'Cute, simplified characters with large heads.' }
];

export default function CreateSetup() {
    const navigate = useNavigate();
    const [synopsis, setSynopsis] = useState('');
    const [artStyle, setArtStyle] = useState<ArtStyle>('anime');
    const [loading, setLoading] = useState(false);

    const handleLucky = async () => {
        try {
            const response = await fetch('/lucky.json');
            const data: { artstyle: string; synopsis: string }[] = await response.json();
            const randomEntry = data[Math.floor(Math.random() * data.length)];
            
            // Map artstyle label from JSON to ArtStyle value
            const styleMap: Record<string, ArtStyle> = {
                'Anime': 'anime',
                'American Cartoon': 'american cartoon style',
                'Western Comic': 'western comic style',
                'Korean Manhwa': 'korean manhwa style',
                'Chibi': 'chibi style'
            };

            setSynopsis(randomEntry.synopsis);
            setArtStyle(styleMap[randomEntry.artstyle] || 'anime');
        } catch (error) {
            console.error('Failed to load lucky settings:', error);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!synopsis.trim()) return;

        setLoading(true);
        try {
            const response = await storyApi.createOutline(synopsis, artStyle);
            // Omit character_images (base64) from navigation state to prevent exceeding the browser's 2MB history state limit.
            const { character_images, ...safeState } = response;
            navigate(`/story/${response.story_id}/editor`, { state: safeState });
        } catch (error) {
            console.error('Failed to create outline:', error);
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-neutral-50">
                <div className="w-16 h-16 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mb-8" />
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">Brainstorming your world...</h2>
                <p className="text-neutral-600 text-center max-w-sm">
                    Our AI is currently drafting your characters, chapters, and the core of your story.
                </p>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto px-4 py-12">
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-4xl font-bold text-neutral-900">Pitch Your Story</h1>
                <button
                    type="button"
                    onClick={handleLucky}
                    className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white font-bold rounded-lg shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-1 active:scale-95"
                >
                    <Dices size={20} />
                    I'm Feeling Lucky
                </button>
            </div>
            <p className="text-neutral-600 mb-12">Give us a synopsis and pick an art style, and we'll handle the rest.</p>

            <form onSubmit={handleSubmit} className="space-y-12">
                <section>
                    <label className="block text-lg font-bold text-neutral-900 mb-4">
                        What's your story about?
                    </label>
                    <textarea 
                        className="w-full h-48 p-4 rounded-xl border border-neutral-300 focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all outline-none text-lg resize-none"
                        placeholder="e.g. A sci-fi detective must solve a murder on a space station while dealing with an AI sidekick..."
                        value={synopsis}
                        onChange={(e) => setSynopsis(e.target.value)}
                        required
                    />
                </section>

                <section>
                    <label className="block text-lg font-bold text-neutral-900 mb-4">
                        Pick an Art Style
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {ART_STYLES.map((style) => (
                            <button
                                key={style.value}
                                type="button"
                                onClick={() => setArtStyle(style.value)}
                                className={`p-4 rounded-xl border-2 text-left transition-all ${
                                    artStyle === style.value 
                                    ? 'border-primary-600 bg-primary-50 shadow-sm' 
                                    : 'border-neutral-200 hover:border-neutral-300'
                                }`}
                            >
                                <div className="font-bold text-neutral-900 mb-1">{style.label}</div>
                                <div className="text-sm text-neutral-600 leading-relaxed">{style.description}</div>
                            </button>
                        ))}
                    </div>
                </section>

                <div className="pt-4">
                    <button
                        type="submit"
                        disabled={!synopsis.trim()}
                        className="w-full md:w-auto flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-neutral-300 text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors shadow-md"
                    >
                        <Sparkles size={20} />
                        Generate Outline
                        <ArrowRight size={20} />
                    </button>
                </div>
            </form>
        </div>
    );
}
