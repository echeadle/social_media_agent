import re
from typing import List, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    InvalidVideoId,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


def get_youtube_video_id(url: str) -> Optional[str]:
    """
    Extracts the YouTube video ID from a given YouTube URL.

    This function supports various YouTube URL formats, including:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - URLs with additional query parameters.

    Args:
        url: The YouTube URL as a string.

    Returns:
        The 11-character YouTube video ID as a string, or None if no
        valid ID can be found.
    """
    # Regular expression to find the video ID in various YouTube URL formats.
    regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None


def get_youtube_video_title(video_id: str) -> Optional[str]:
    """
    Retrieves the title of a YouTube video given its ID.

    Args:
        video_id: The 11-character YouTube video ID.

    Returns:
        The video title as a string, or None if the title cannot be retrieved.
    """
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        return yt.title
    except Exception:
        # It's non-critical if the title can't be fetched, so we can fail silently.
        return None


def get_transcript(video_id: str, languages: List[str] = None) -> str:
    """
    Retrieves the transcript for a YouTube video.

    Args:
        video_id (str): The YouTube video ID.
        languages (list, optional): List of language codes to try, in order of preference.
                                   Defaults to ["en"].

    Returns:
        str: The concatenated transcript text.

    Raises:
        Exception: If transcript retrieval fails.
    """
    if languages is None:
        languages = ["en"]

    try:
        # Use the .fetch() method which is confirmed to work in the user's environment.
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id, languages=languages)
        return " ".join(snippet.text for snippet in transcript_list)
    except Exception as e:
        if isinstance(e, NoTranscriptFound):
            raise Exception(f"No transcript found for video {video_id} in languages: {languages}") from e
        elif isinstance(e, (VideoUnavailable, TranscriptsDisabled)):
            raise Exception(f"Transcripts are unavailable or disabled for video {video_id}: {e}") from e
        elif isinstance(e, (InvalidVideoId, CouldNotRetrieveTranscript)):
            raise Exception(f"Could not retrieve transcript for video {video_id}: {e}") from e
        raise Exception(f"An unexpected error occurred fetching transcript for {video_id}: {e}") from e


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = get_youtube_video_id(video_url)
    print(video_id)
