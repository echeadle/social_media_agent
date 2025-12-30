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

# Tool: Generate social media content from transcript
@function_tool
def generate_content(video_transcript: str, social_media_platform: str):
    print(f"Generating social media content for {social_media_platform}...")

    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Generate contentpy

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "user", "content": f"Here is a new video transcript:\n{video_transcript}\n\n"
                                        f"Generate a social media post on my {social_media_platform} based on my provided video transcript.\n"}
        ],
        max_output_tokens=2500  # Increase tokens for longer blog posts
    )

    return response.output_text


#-------------------------------------------------------
# Step 3: Define Agents
#-------------------------------------------------------
@dataclass
class Post:
    platform: str
    content: str


content_writer_agent = Agent(
    name="Content Writer Agent",
    instructions="""You are a talented content writer who writes engaging, humorous, informative and 
                    highly readable social media posts. 
                    You will be given a video transcript and social media platforms. 
                    You will generate a social media post based on the video transcript 
                    and the social media platforms.
                    You may search the web for up-to-date information on the topic and 
                    fill in some useful details if needed.""",
    model="gpt-4o-mini",
    tools=[generate_content,
           WebSearchTool(),
           ],
    output_type=List[Post],
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
    #video_url = "https://www.youtube.com/watch?v=OZ5OZZZ2cvk"
    #video_url ="https://www.youtube.com/watch?v=bZzyPscbtI8&list=PL3QtKUJkA75n2Rp22ClKpDmLF1r-eUOWw&index=2"
    video_url = "https://www.youtube.com/watch?v=zcYtSckecD8&list=PL3QtKUJkA75n2Rp22ClKpDmLF1r-eUOWw&index=27"
    video_id = get_youtube_video_id(video_url)
    
    transcript = get_transcript(video_id)

    msg = f"Generate a LinkedIn post and an Instagram caption based on this video transcript: {transcript}"

    # Package input for the agent
    input_items = [{"content": msg, "role": "user"}]

    # Run content writer agent
    # Add trace to see the agent's execution steps
    # You can check the trace on https://platform.openai.com/traces
    with trace("Writing content"):
        result = await Runner.run(content_writer_agent, input_items)
        output = ItemHelpers.text_message_outputs(result.new_items)
        print("Generated Post:\n", output)

if __name__ == "__main__":
    asyncio.run(main())
