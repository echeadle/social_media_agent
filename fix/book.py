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
import logging
import sys
import asyncio
from typing import List, Sequence, TypedDict, Literal
import os
from datetime import datetime
import re
import json

from openai import OpenAI  # noqa: F401
from dotenv import load_dotenv
from pydantic import BaseModel
from utils import get_youtube_video_id, get_transcript
from agents import Agent, Runner, WebSearchTool, trace, function_tool

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()  # Securely load OPENAI_API_KEY from .env

# -------------------------------
# Setup logging
# -------------------------------
logging.basicConfig(
    filename="book_agent.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Also log to console for immediate feedback
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

# Pydantic Model for structured output
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
def chunk_transcript(text: str, max_length: int = 4000) -> List[str]:
    """Split transcript into chunks to manage LLM token limits."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def save_to_markdown(sections: List[BookSection], video_id: str) -> str:
    """
    Saves a list of book sections to a Markdown file.

    Args:
        sections: A list of BookSection objects to save.
        video_id: The YouTube video ID to include in the filename.

    Returns:
        str: Success or error message.
    """
    logger.info(f"Saving {len(sections)} sections for video ID: {video_id}")
    
    # Validate sections
    if not all(isinstance(section, BookSection) for section in sections):
        error_message = "Error: Invalid sections provided"
        logger.error(error_message)
        return error_message
    
    # Sanitize video_id for safe filename
    safe_video_id = re.sub(r'[^\w\-]', '_', video_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"book_sections_{safe_video_id}_{timestamp}.md"
    
    # Add metadata to Markdown
    markdown_content = f"# Generated Book Sections\n\nVideo ID: {video_id}\nGenerated on: {timestamp}\n\n"
    for i, section in enumerate(sections, 1):
        markdown_content += f"## {i}. {section.title}\n\n"
        markdown_content += f"**Summary:**\n{section.summary}\n\n"
        markdown_content += f"**Key Concepts:**\n- " + "\n- ".join(section.key_concepts) + "\n\n"
        if section.code_examples:
            markdown_content += f"**Code Examples:**\n"
            for code in section.code_examples:
                markdown_content += f"```python\n{code}\n```\n"
            markdown_content += "\n"
        markdown_content += f"**Explanation:**\n{section.explanation}\n\n"
        markdown_content += "-" * 20 + "\n"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        success_message = f"Successfully saved content to {filename}"
        logger.info(success_message)
        return success_message
    except Exception as e:
        error_message = f"Error: Failed to save file. {e}"
        logger.error(error_message)
        return error_message

# -------------------------------
# Tools
# -------------------------------
logger.info("Initializing SaveToMarkdown tool")
save_markdown_tool = function_tool(save_to_markdown)

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

You may use the web search tool to clarify concepts or find up-to-date information.

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
    tools=[WebSearchTool(), save_markdown_tool],
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

        # Fetch transcript with error handling
        try:
            transcript_text = get_transcript(video_id)
            logger.info(f"Transcript fetched successfully. Length: {len(transcript_text)} characters")
        except Exception as e:
            logger.error(f"Failed to fetch transcript: {e}")
            sys.exit(1)

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

        # Save sections to Markdown file
        with trace("Saving book sections to Markdown"):
            result_message = save_to_markdown(sections=sections, video_id=video_id)
            if "Successfully" in result_message:
                logger.info(result_message)
            else:
                logger.error(result_message)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

# -------------------------------
# Entry point
# -------------------------------
if __name__ == "__main__":
    asyncio.run(main())