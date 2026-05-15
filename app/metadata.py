from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "new",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}")


@dataclass(frozen=True)
class TrendingVideo:
    title: str
    tags: Sequence[str]


@dataclass(frozen=True)
class MetadataResult:
    description: str
    tags: List[str]
    trending_topics: List[str]
    trending_hashtags: List[str]


def build_metadata(
    *,
    video_id: str,
    title: str,
    default_description: str,
    default_tags: Sequence[str],
    default_hashtags: Sequence[str],
    trending_videos: Sequence[TrendingVideo],
    max_tags: int,
    trending_tag_limit: int,
    trending_title_keyword_limit: int,
) -> MetadataResult:
    """Build a final description and tag list from defaults plus current trending data."""

    trending_tags = _top_trending_tags(trending_videos, trending_tag_limit)
    title_keywords = _top_title_keywords(trending_videos, trending_title_keyword_limit)
    trending_topics = _dedupe([*title_keywords, *trending_tags])
    trending_hashtags = _to_hashtags(trending_topics)

    tags = _limit_tags(_dedupe([*default_tags, *trending_tags, *title_keywords]), max_tags=max_tags)
    description = default_description.format(
        title=title,
        video_id=video_id,
        trending_topics=", ".join(trending_topics),
        trending_hashtags=" ".join(trending_hashtags),
    ).strip()

    hashtags = _dedupe([*default_hashtags, *trending_hashtags])
    if hashtags:
        description = f"{description}\n\n{' '.join(hashtags)}"

    return MetadataResult(
        description=description,
        tags=tags,
        trending_topics=trending_topics,
        trending_hashtags=hashtags,
    )


def _top_trending_tags(videos: Sequence[TrendingVideo], limit: int) -> List[str]:
    counter: Counter[str] = Counter()
    original_by_key: dict[str, str] = {}
    for video in videos:
        for tag in video.tags:
            cleaned = _clean_tag(tag)
            if not cleaned:
                continue
            key = cleaned.lower()
            original_by_key.setdefault(key, cleaned)
            counter[key] += 1
    return [original_by_key[key] for key, _ in counter.most_common(limit)]


def _top_title_keywords(videos: Sequence[TrendingVideo], limit: int) -> List[str]:
    counter: Counter[str] = Counter()
    original_by_key: dict[str, str] = {}
    for video in videos:
        for match in WORD_RE.findall(video.title):
            word = match.strip("'-").lower()
            if word in STOP_WORDS or len(word) < 3:
                continue
            original_by_key.setdefault(word, word)
            counter[word] += 1
    return [original_by_key[key] for key, _ in counter.most_common(limit)]


def _to_hashtags(values: Iterable[str]) -> List[str]:
    hashtags: List[str] = []
    for value in values:
        compact = re.sub(r"[^A-Za-z0-9]", "", value.title())
        if compact:
            hashtags.append(f"#{compact}")
    return _dedupe(hashtags)


def _clean_tag(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned or len(cleaned) > 500:
        return ""
    return cleaned


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        cleaned = _clean_tag(value)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _limit_tags(values: Sequence[str], *, max_tags: int, max_total_chars: int = 500) -> List[str]:
    limited: List[str] = []
    total_chars = 0
    for value in values:
        if len(limited) >= max_tags:
            break
        projected_total = total_chars + len(value)
        if projected_total > max_total_chars:
            continue
        limited.append(value)
        total_chars = projected_total
    return limited
