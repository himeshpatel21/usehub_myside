"""Seed the tool catalog on first run."""

import asyncio

from slugify import slugify
from sqlalchemy import select

from app.db.base import new_uuid
from app.db.models.profile import Tool
from app.db.session import AsyncSessionLocal

TOOLS = [
    ("ChatGPT", "llm"),
    ("Claude", "llm"),
    ("Gemini", "llm"),
    ("GPT-4", "llm"),
    ("GPT-4o", "llm"),
    ("Llama 3", "llm"),
    ("Mistral", "llm"),
    ("Perplexity", "search"),
    ("Midjourney", "image"),
    ("DALL-E", "image"),
    ("Stable Diffusion", "image"),
    ("Ideogram", "image"),
    ("Cursor", "coding"),
    ("GitHub Copilot", "coding"),
    ("Windsurf", "coding"),
    ("Codeium", "coding"),
    ("ElevenLabs", "audio"),
    ("Suno", "audio"),
    ("Runway", "video"),
    ("Kling", "video"),
    ("Notion AI", "productivity"),
    ("v0", "design"),
]


async def seed_tools() -> None:
    async with AsyncSessionLocal() as db:
        for name, category in TOOLS:
            slug = slugify(name, separator="-")
            result = await db.execute(select(Tool).where(Tool.slug == slug))
            if not result.scalar_one_or_none():
                db.add(Tool(id=new_uuid(), name=name, slug=slug, category=category))
        await db.commit()
    print(f"Seeded {len(TOOLS)} tools")


if __name__ == "__main__":
    asyncio.run(seed_tools())
