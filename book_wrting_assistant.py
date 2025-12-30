#-------------------------------------------------------
# Step 0: Import packages and modules
#-------------------------------------------------------
import asyncio

import os
from youtube_transcript_api import YouTubeTranscriptApi
from agents import Agent, Runner, WebSearchTool, function_tool, ItemHelpers, trace
from openai import OpenAI
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List
from utils import get_youtube_video_id, get_transcript

#-------------------------------------------------------
# Step 1: Get OpenAI API key
#-------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


#-------------------------------------------------------
# Step 2: Define Tools for Agents
#-------------------------------------------------------


#-------------------------------------------------------
# Step 3: Define Agents
#-------------------------------------------------------
@dataclass
class BookSection:
    """Represents a structured section of content for the book."""
    title: str
    summary: str
    key_concepts: List[str]
    code_examples: List[str]
    explanation: str


book_writing_assistant_agent = Agent(
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

You may use the web search tool to clarify concepts or find up-to-date information.""",
    model="gpt-4o-mini",
    tools=[WebSearchTool()],
    output_type=List[BookSection],
)


#-------------------------------------------------------
# Step 4: Define Helper Functions
#-------------------------------------------------------
# Fetch transcript from a youtube video using the video id

#-------------------------------------------------------
# Step 5: Run the agent
#-------------------------------------------------------

#video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#video_id = get_youtube_video_id(video_url)

# if video_id:
#     print(f"Found Video ID: {video_id}")
# else:
#     print("Could not find a valid YouTube video ID in the URL.")

async def main():
    # This video URL is a great starting point for a book on building agents.
    video_url = "https://www.youtube.com/watch?v=T1Lowy1mnEg"
    #"https://www.youtube.com/watch?v=bZzyPscbtI8&list=PL3QtKUJkA75n2Rp22ClKpDmLF1r-eUOWw&index=2"
    
    video_id = get_youtube_video_id(video_url)
    print(f"Video ID extracted from URL: {video_id}")
    if not video_id:
        print(f"Could not extract a valid video ID from the URL: {video_url}")
        return

    try:
        print(f"Fetching transcript for video ID: {video_id}...")
        transcript = get_transcript(video_id)
        print("Transcript fetched successfully.")
    except Exception as e:
        print(f"Could not retrieve transcript: {e}")
        return

    # This is the user role/prompt that guides the agent for this specific task.
    user_prompt = f"""Please analyze the following transcript and extract the key information for my book on building AI agents, based on your instructions.

Here is the transcript:
---
{transcript}
---
"""

    # Package input for the agent
    input_items = [{"content": user_prompt, "role": "user"}]

    # Run the book writing assistant agent
    with trace("Extracting book content"):
        result = await Runner.run(book_writing_assistant_agent, input_items)

        # The structured output is likely in the `content` of the last item in `new_items`.
        # The `result.output` attribute might be from an older version of the library.
        book_sections: List[BookSection] = []
        if result.new_items and hasattr(result.new_items[-1], "content"):
            book_sections = result.new_items[-1].content

        if not book_sections or not isinstance(book_sections, list):
            print("The agent did not return any structured book sections.")
            return

        print("\n--- Generated Book Content ---\n")
        for i, section in enumerate(book_sections):
            print(f"## Section {i+1}: {section.title}\n")
            print(f"**Summary:**\n{section.summary}\n")
            print(f"**Key Concepts:**\n- " + "\n- ".join(section.key_concepts) + "\n")
            if section.code_examples:
                print(f"**Code Examples:**")
                for code in section.code_examples:
                    print(f"```python\n{code}\n```")
                print()
            print(f"**Explanation:**\n{section.explanation}\n")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(main())