export type ArtStyle = "anime" | "american cartoon style" | "western comic style" | "korean manhwa style" | "chibi style";

export interface CharacterSpriteInfo {
    name: string;
    role: string;
    gender: "male" | "female";
    appearance: string;
}

export interface ChapterOutline {
    chapter_id: string;
    title: string;
    primary_location: string;
    plot_summary: string;
}

export interface MainStoryOutline {
    title: string;
    logline: string;
    main_characters: CharacterSpriteInfo[];
    side_characters: CharacterSpriteInfo[];
    main_chapters: ChapterOutline[];
}

export interface StorySummary {
    id: number;
    title: string | null;
    logline: string | null;
    style: ArtStyle;
}

export interface StoryOutlineResponse {
    story_id: number;
    outline: MainStoryOutline;
    character_images: Record<string, string>; // base64 strings!
}

export interface SceneDetail {
    id: number;
    title: string;
    dialogue: Array<{ speaker: string; text: string; character_pose_expression?: string }> | null;
}

export interface ChapterWithScenes {
    id: number;
    title: string | null;
    scenes: SceneDetail[];
}

export interface StatusResponse {
    status: string;
    message: string;
}

export interface CharacterImageResponse {
    status: string;
    image_data: string | null;
}
