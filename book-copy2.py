#!/usr/bin/env python3
"""
YouTube Transcript → Structured Book Sections
Takes a YouTube URL, fetches the transcript, and asks an LLM
to turn it into structured book sections using an Agent.
"""

import argparse
import logging
import sys
import asyncio
from typing import List, Sequence, TypedDict, Literal

from openai import OpenAI  # noqa: F401
from dotenv import load_dotenv
from pydantic import BaseModel
from utils import get_youtube_video_id, get_transcript
from agents import Agent, Runner, WebSearchTool, trace

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()  # pulls OPENAI_API_KEY and others from .env

# -------------------------------
# Setup logging
# -------------------------------
logging.basicConfig(
    filename="book_agent.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# -------------------------------
# Type Definitions
# -------------------------------
class AgentInputItem(TypedDict):
    content: str
    role: Literal["user", "system", "assistant", "tool"]

# Pydantic Model
# -------------------------------
class BookSection(BaseModel):
    title: str
    summary: str
    key_concepts: List[str]
    code_examples: List[str]
    explanation: str

# -------------------------------
# Helper Functions
# -------------------------------
def chunk_transcript(text: str, max_length: int = 8000) -> List[str]:
    """Split transcript into chunks to manage token limits."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# -------------------------------
# Agent Definition
# -------------------------------
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

Given a video transcript, your task is to identify sections that discuss these topics. For each relevant section you find, you must structure your output as a list of 'BookSection' objects. Each object should contain:
- title: A concise title for the topic discussed.
- summary: A detailed summary of the concept.
- key_concepts: A list of keywords or short phrases.
- code_examples: A list of relevant code snippets from the transcript.
- explanation: An explanation of how the concepts or code work.

Output ONLY a valid JSON array of BookSection objects, like this:
[
  {
    "title": "Example Title",
    "summary": "Detailed summary here.",
    "key_concepts": ["concept1", "concept2"],
    "code_examples": ["code snippet 1", "code snippet 2"],
    "explanation": "Explanation of how it works."
  }
]
Do not include any other text, explanations, or markdown outside the JSON.""",
    model="gpt-4o-mini",
    tools=[],  # Temporarily disabled WebSearchTool to isolate issues; re-enable with [WebSearchTool()] after testing
    output_type=List[BookSection],
)

# -------------------------------
# Main function
# -------------------------------
async def main():
    parser = argparse.ArgumentParser(
        description="Convert a YouTube transcript into structured book sections"
    )
    parser.add_argument("url", help="YouTube video URL")
    args = parser.parse_args()

    try:
        video_id = get_youtube_video_id(args.url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {args.url}")

        logger.info(f"Video ID extracted from URL: {video_id}")

        transcript_text = get_transcript(video_id)
        logger.info(f"Transcript fetched successfully. Length: {len(transcript_text)} characters")

        # Chunk transcript to manage token limits
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
            input_items: Sequence[AgentInputItem] = [{"content": user_prompt, "role": "user"}]

            # Run the book writing assistant agent
            with trace(f"Extracting book content from transcript chunk {i}"):
                result = await Runner.run(book_writing_agent, input_items)
                logger.info(f"Agent result: {result}")

            # Access the structured output from the final_output attribute
            if hasattr(result, "final_output") and isinstance(result.final_output, list):
                chunk_sections = result.final_output
                sections.extend(chunk_sections)
            else:
                logger.warning(f"No valid sections returned for chunk {i}")

        if not sections:
            logger.warning("⚠️ The agent did not return any structured book sections.")
            return

        # Render structured sections
        logger.info("\n--- Generated Book Content ---\n")
        for i, section in enumerate(sections, 1):
            logger.info(f"## {i}. {section.title}\n")
            logger.info(f"**Summary:**\n{section.summary}\n")
            logger.info(f"**Key Concepts:**\n- " + "\n- ".join(section.key_concepts) + "\n")
            if section.code_examples:
                logger.info(f"**Code Examples:**")
                for code in section.code_examples:
                    logger.info(f"```python\n{code}\n```")
                logger.info("")
            logger.info(f"**Explanation:**\n{section.explanation}\n")
            logger.info("-" * 20)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

# -------------------------------
# Entry point
# -------------------------------
if __name__ == "__main__":
    asyncio.run(main())