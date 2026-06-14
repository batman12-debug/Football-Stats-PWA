"""News and transfer feed models."""

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """A football news article from an external feed."""

    id: str
    title: str
    summary: str
    url: str
    source: str
    category: str
    published_at: str
    image_url: str | None = None


class TransferItem(BaseModel):
    """A transfer market update — structured deal or reported move."""

    id: str
    player_name: str
    from_club: str | None = None
    to_club: str | None = None
    fee: str | None = None
    transfer_type: str | None = None
    date: str
    source: str
    url: str
    summary: str | None = None
    image_url: str | None = None


class NewsFeedResponse(BaseModel):
    """Combined news and transfer payload."""

    articles: list[NewsArticle] = Field(default_factory=list)
    transfers: list[TransferItem] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
