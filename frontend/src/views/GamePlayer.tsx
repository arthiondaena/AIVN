import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { API_BASE_URL } from '../services/api';

export default function GamePlayer() {
    const { id } = useParams();
    const storyId = Number(id);

    return (
        <div className="w-screen h-screen overflow-hidden bg-neutral-950 flex flex-col items-center justify-center relative font-sans">
            <Link 
                to={`/story/${storyId}/review`}
                className="absolute top-6 left-6 z-50 bg-white/10 hover:bg-white/20 text-white p-3 rounded-full backdrop-blur-md transition-all group"
                title="Back to Script"
            >
                <ArrowLeft size={24} className="group-hover:-translate-x-1 transition-transform" />
            </Link>
            
            <div className="w-full h-full relative">
                <iframe
                    src={`/game.html?story_id=${storyId}&backend_url=${encodeURIComponent(API_BASE_URL)}`}
                    className="w-full h-full border-none"
                    title={`Game Player for Story ${storyId}`}
                    allowFullScreen
                />
            </div>
        </div>
    );
}
