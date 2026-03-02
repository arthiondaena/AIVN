from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    logline: Mapped[Optional[str]] = mapped_column(Text)
    original_text: Mapped[Optional[str]] = mapped_column(Text)
    style: Mapped[str] = mapped_column(String(50))  # anime, western, etc.
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapters: Mapped[List["Chapter"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    characters: Mapped[List["Character"]] = relationship(back_populates="story", cascade="all, delete-orphan")
    backgrounds: Mapped[List["Background"]] = relationship(back_populates="story", cascade="all, delete-orphan")

class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    chapter_cid: Mapped[str] = mapped_column(String(50)) # e.g. act1_chapter1
    title: Mapped[Optional[str]] = mapped_column(String(255))
    primary_location: Mapped[Optional[str]] = mapped_column(String(255))
    plot_summary: Mapped[Optional[str]] = mapped_column(Text)
    sequence_number: Mapped[int] = mapped_column(Integer)

    story: Mapped["Story"] = relationship(back_populates="chapters")
    scenes: Mapped[List["Scene"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")

class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[Optional[str]] = mapped_column(String(100))
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    voice_id: Mapped[Optional[str]] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    base_image_gcs_path: Mapped[Optional[str]] = mapped_column(String(512))

    story: Mapped["Story"] = relationship(back_populates="characters")
    poses: Mapped[List["CharacterPose"]] = relationship(back_populates="character", cascade="all, delete-orphan")


class CharacterPose(Base):
    __tablename__ = "character_poses"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"))
    pose_description: Mapped[str] = mapped_column(Text)
    image_gcs_path: Mapped[str] = mapped_column(String(512))
    embedding: Mapped[Vector] = mapped_column(Vector(768))

    character: Mapped["Character"] = relationship(back_populates="poses")


class Background(Base):
    __tablename__ = "backgrounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    image_gcs_path: Mapped[Optional[str]] = mapped_column(String(512))
    image_type: Mapped[str] = mapped_column(String(20), default="static")

    story: Mapped["Story"] = relationship(back_populates="backgrounds")

class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id"))
    scene_sid: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    primary_location: Mapped[Optional[str]] = mapped_column(String(255))
    scene_summary: Mapped[Optional[str]] = mapped_column(Text)
    sequence_number: Mapped[int] = mapped_column(Integer)

    # Detailed content
    initial_location_name: Mapped[Optional[str]] = mapped_column(String(255))
    initial_location_description: Mapped[Optional[str]] = mapped_column(Text)
    initial_bgm: Mapped[Optional[str]] = mapped_column(String(255))

    dialogue_content: Mapped[Optional[dict]] = mapped_column(JSON) # List of DialogueLine
    choices_content: Mapped[Optional[dict]] = mapped_column(JSON) # List of StoryBranch
    location_changes: Mapped[Optional[dict]] = mapped_column(JSON) # List of LocationChange

    chapter: Mapped["Chapter"] = relationship(back_populates="scenes")