from app.metadata import TrendingVideo, build_metadata


def test_build_metadata_keeps_defaults_and_adds_trending_values() -> None:
    result = build_metadata(
        video_id="abc123",
        title="My Python Upload",
        default_description="Watch {title}. Trending: {trending_topics} {trending_hashtags}",
        default_tags=["my channel", "python"],
        default_hashtags=["#MyChannel"],
        trending_videos=[
            TrendingVideo(title="Python automation tutorial", tags=["python", "automation", "youtube tips"]),
            TrendingVideo(title="AI automation workflow", tags=["automation", "ai tools"]),
        ],
        max_tags=10,
        trending_tag_limit=5,
        trending_title_keyword_limit=5,
    )

    assert result.tags[:2] == ["my channel", "python"]
    assert "automation" in [tag.lower() for tag in result.tags]
    assert sum(len(tag) for tag in result.tags) <= 500
    assert "#MyChannel" in result.description
    assert "Trending:" in result.description


def test_build_metadata_respects_tag_count_limit() -> None:
    result = build_metadata(
        video_id="abc123",
        title="Upload",
        default_description="Description",
        default_tags=["one", "two", "three"],
        default_hashtags=[],
        trending_videos=[TrendingVideo(title="Four Five Six", tags=["four", "five", "six"])],
        max_tags=4,
        trending_tag_limit=3,
        trending_title_keyword_limit=3,
    )

    assert result.tags == ["one", "two", "three", "four"]
