import re
from typing import Optional


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

if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = get_youtube_video_id(video_url)
    print(video_id)

