# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Fetches a YouTube transcript and uses an OpenAI agent to convert it into structured Markdown book sections. Output files land in `books/`.

## Environment Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

Requires a `.env` file (not committed) with:
```
OPENAI_API_KEY=...
LLM_MODEL=gpt-4o-mini   # or any OpenAI model name
```

## Running the Script

```bash
# Basic — auto-generated filename
uv run book.py "https://www.youtube.com/watch?v=VIDEO_ID"

# With a custom output filename and heading
uv run book.py "https://www.youtube.com/watch?v=VIDEO_ID" --title "My_Book_Title"
```

Always quote the URL — the `&` in timestamp parameters (`&t=`) is special in bash.

`--title` controls both the output filename (`books/<title>.md`) and the H1 heading inside the file. Without it, the file is named `book_sections_<video_id>_<timestamp>.md`.

## Architecture

```
book.py       — main entry point; argparse, agent definition, orchestration
utils.py      — get_youtube_video_id(), get_transcript()
books/        — generated Markdown output
book_agent.log — rotating log (1 MB × 3 backups)
```

### Data flow

1. `get_youtube_video_id(url)` extracts the 11-char video ID via regex
2. `get_transcript(video_id)` fetches English captions via `YouTubeTranscriptApi`
3. Transcript is chunked into 4000-char pieces
4. Each chunk is sent to `book_writing_agent` (an `openai-agents` `Agent` with `WebSearchTool`)
5. The agent returns `List[BookSection]` (Pydantic model with title, summary, key_concepts, code_examples, explanation)
6. `save_to_markdown()` writes all sections to a single `.md` file

### Key dependencies

| Package | Purpose |
|---|---|
| `openai-agents` | Agent + Runner + WebSearchTool + trace |
| `youtube-transcript-api` | Transcript fetching |
| `pydantic` | Structured output (`BookSection`) |
| `python-dotenv` | `.env` loading |
