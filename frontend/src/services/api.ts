import axios from 'axios';
import type { 
    ArtStyle, 
    MainStoryOutline, 
    StoryOutlineResponse, 
    StorySummary, 
    ChapterWithScenes, 
    StatusResponse,
    CharacterImageResponse
} from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://aivn-backend-771191326524.us-central1.run.app';

const api = axios.create({
    baseURL: API_BASE_URL,
});

export const storyApi = {
    listStories: async (): Promise<StorySummary[]> => {
        const response = await api.get('/api/stories');
        return response.data;
    },
    createOutline: async (synopsis: string, artStyle: ArtStyle): Promise<StoryOutlineResponse> => {
        const response = await api.post('/api/story/outline', { synopsis, art_style: artStyle });
        return response.data;
    },
    updateOutline: async (storyId: number, outline: MainStoryOutline): Promise<StatusResponse> => {
        const response = await api.put(`/api/story/${storyId}/outline`, { story_outline: outline });
        return response.data;
    },
    regenerateCharacterBase: async (storyId: number, characterId: number, appearance: string, artStyle: ArtStyle): Promise<CharacterImageResponse> => {
        const response = await api.post(`/api/story/${storyId}/character/${characterId}/regenerate-base`, {
            appearance,
            art_style: artStyle
        });
        return response.data;
    },
    generatePipeline: async (storyId: number): Promise<StatusResponse> => {
        const response = await api.post(`/api/story/${storyId}/generate-pipeline`);
        return response.data;
    },
    convertStory: async (storyId: number): Promise<StatusResponse> => {
        const response = await api.post(`/api/story/${storyId}/convert`);
        return response.data;
    },
    getStoryScenes: async (storyId: number): Promise<ChapterWithScenes[]> => {
        const response = await api.get(`/api/story/${storyId}/scenes`);
        return response.data;
    }
};
