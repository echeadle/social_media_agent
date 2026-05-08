#!/usr/bin/env python3
"""
YouTube Transcript → Structured Book Sections
Takes a YouTube URL, fetches the transcript, and asks an LLM
to turn it into structured book sections using an Agent.
Saves the output as a Markdown file.

This script teaches beginners how to use LLM APIs, structured outputs (Pydantic),
and tool integration, with security best practices (python-dotenv).
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from agents import Agent, Runner, WebSearchTool, trace
from dotenv import load_dotenv
from pydantic import BaseModel

from utils import get_transcript, get_youtube_video_id

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
BOOKS_DIR = SCRIPT_DIR / "books"
LOG_PATH = SCRIPT_DIR / "book_agent.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)


class BookSection(BaseModel):
    title: str
    summary: str
    key_concepts: List[str]
    code_examples: List[str]
    explanation: str


def chunk_transcript(text: str, max_length: int = 4000) -> List[str]:
    """Split transcript into chunks to manage LLM token limits."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def save_to_markdown(sections: List[BookSection], video_id: str, url: str = "", title: str = "") -> Path:
    """Write sections to a timestamped markdown file under books/. Returns the path."""
    BOOKS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if title:
        safe_name = title.replace(" ", "_")
        path = BOOKS_DIR / f"{safe_name}.md"
    else:
        path = BOOKS_DIR / f"book_sections_{video_id}_{timestamp}.md"

    header = f"# {title or 'Generated Book Sections'}\n\n"
    header += f"Source URL: {url}\n"
    header += f"Video ID: {video_id}\n"
    header += f"Generated on: {timestamp}\n\n"
    parts = [header]
    for i, section in enumerate(sections, 1):
        parts.append(f"## {i}. {section.title}\n\n")
        parts.append(f"**Summary:**\n{section.summary}\n\n")
        parts.append("**Key Concepts:**\n- " + "\n- ".join(section.key_concepts) + "\n\n")
        if section.code_examples:
            parts.append("**Code Examples:**\n")
            for code in section.code_examples:
                parts.append(f"```python\n{code}\n```\n")
            parts.append("\n")
        parts.append(f"**Explanation:**\n{section.explanation}\n\n")
        parts.append("-" * 20 + "\n")

    path.write_text("".join(parts), encoding="utf-8")
    return path


book_writing_agent = Agent(
    name="Book Writing Assistant Agent",
    instructions="""You are an expert research assistant helping to write a technical book about building AI agents from scratch in Python.
Your goal is to analyze video transcripts and extract key information relevant to the book's outline.

The book covers these main topics:
Part 1: Building Blocks - The Augmented LLM
- Basic LLM calls
- Structured output (e.g., Pydantic, JSON mode)
- Tool use and function calling
- Retrieval Augmented Generation (RAG)

Part 2: Workflow Patterns for AI Systems
- Prompt chaining
- Routing (deciding which tool or path to take)
- Parallelization (running tools or agents concurrently)

Given a video transcript, identify sections that discuss these topics. For each relevant section, return a BookSection with:
- title: A concise title for the topic discussed.
- summary: A detailed summary of the concept.
- key_concepts: A list of keywords or short phrases.
- code_examples: A list of relevant code snippets from the transcript.
- explanation: An explanation of how the concepts or code work.

You may use the web search tool to clarify concepts or find up-to-date information.""",
    model=os.getenv("LLM_MODEL"),
    tools=[WebSearchTool()],
    output_type=List[BookSection],
)


async def main():
    parser = argparse.ArgumentParser(
        description="Convert a YouTube transcript into structured book sections"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--title", default="", help="Proposed title for the book")
    args = parser.parse_args()

    try:
        video_id = get_youtube_video_id(args.url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {args.url}")

        logger.info(f"Video ID extracted from URL: {video_id}")

        try:
            transcript_text = get_transcript(video_id)
            logger.info(f"Transcript fetched. Length: {len(transcript_text)} characters")
        except Exception as e:
            logger.error(f"Failed to fetch transcript: {e}")
            sys.exit(1)

        chunks = chunk_transcript(transcript_text)
        sections: List[BookSection] = []

        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing transcript chunk {i}/{len(chunks)}")
            user_prompt = f"""Please analyze the following transcript chunk and break it into structured book sections, based on your instructions.

            Here is the transcript chunk:
            ---
            {chunk}
            ---
            """
            with trace(f"Extracting book content from transcript chunk {i}"):
                result = await Runner.run(
                    book_writing_agent,
                    [{"content": user_prompt, "role": "user"}],
                )

            sections.extend(result.final_output)

        if not sections:
            logger.warning("The agent did not return any structured book sections.")
            return

        with trace("Saving book sections to Markdown"):
            path = save_to_markdown(sections=sections, video_id=video_id, url=args.url, title=args.title)
            logger.info(f"Saved {len(sections)} sections to {path}")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
