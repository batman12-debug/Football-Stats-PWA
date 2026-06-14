"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchNewsFeedClient } from "@/lib/api";
import { resolveNewsImage, resolveTransferImage } from "@/lib/newsImages";
import { safeExternalUrl } from "@/lib/security";
import { stripDisplayDashes } from "@/lib/utils";
import type { NewsArticle, NewsFeedResponse, TransferItem } from "@/types";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

function formatStableTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;

  const day = date.getUTCDate();
  const month = MONTHS[date.getUTCMonth()];
  return `${day} ${month}`;
}

function formatRelativeTime(iso: string, nowMs: number = Date.now()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;

  const diffMs = nowMs - date.getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;

  return formatStableTime(iso);
}

function RelativeTime({ iso }: { iso: string }) {
  const [label, setLabel] = useState(() => formatStableTime(iso));

  useEffect(() => {
    const update = () => setLabel(formatRelativeTime(iso));
    update();
    const intervalId = window.setInterval(update, 60_000);
    return () => window.clearInterval(intervalId);
  }, [iso]);

  return <span suppressHydrationWarning>{label}</span>;
}

function BookmarkIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className="h-4 w-4 shrink-0 opacity-60"
      aria-hidden="true"
    >
      <path d="M7 4h10v16l-5-3.5L7 20V4z" />
    </svg>
  );
}

function NewsCardFooter({ source, publishedAt }: { source: string; publishedAt: string }) {
  return (
    <div className="mt-auto flex items-center justify-between gap-2 pt-2">
      <p className="truncate text-xs text-muted">
        {source} · <RelativeTime iso={publishedAt} />
      </p>
      <BookmarkIcon />
    </div>
  );
}

function getNewsCardLayout(index: number): "wide" | "tall" | null {
  const slot = index % 6;
  if (slot === 0) return "wide";
  if (slot === 3) return "tall";
  return null;
}

function newsCardLayoutClass(layout: "wide" | "tall" | null): string {
  if (layout === "wide") return "news-card--wide";
  if (layout === "tall") return "news-card--tall";
  return "";
}

function NewsCardImage({
  src,
  alt,
  layout = null,
}: {
  src: string;
  alt: string;
  layout?: "wide" | "tall" | null;
}) {
  const aspectClass =
    layout === "tall" ? "aspect-[4/5] sm:aspect-[3/4]" : layout === "wide" ? "aspect-[21/9]" : "aspect-[16/10]";

  return (
    <div className={`relative w-full shrink-0 overflow-hidden bg-card-border ${aspectClass}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        decoding="async"
        className="h-full w-full object-cover transition-transform duration-300 ease-out motion-reduce:transition-none [@media(hover:hover)]:group-hover:scale-[1.03]"
      />
    </div>
  );
}

function NewsCard({
  article,
  layout = null,
}: {
  article: NewsArticle;
  layout?: "wide" | "tall" | null;
}) {
  const href = safeExternalUrl(article.url);
  const imageSrc = resolveNewsImage(article.image_url, article.category);

  const cardClass = `group news-card flex h-full flex-col overflow-hidden rounded-xl border border-transparent bg-black/70 backdrop-blur-[3px] transition-[transform,border-color] duration-[160ms] ease-out hover:border-win/30 active:scale-[0.99] ${newsCardLayoutClass(layout)}`;

  const body = (
    <>
      <NewsCardImage src={imageSrc} alt={stripDisplayDashes(article.title)} layout={layout} />
      <div className="flex min-w-0 flex-1 flex-col p-3 sm:p-4">
        <h3 className="line-clamp-3 type-ui text-sm text-white group-hover:text-win sm:text-[15px]">
          {stripDisplayDashes(article.title)}
        </h3>
        <NewsCardFooter source={stripDisplayDashes(article.source)} publishedAt={article.published_at} />
      </div>
    </>
  );

  if (!href) {
    return <article className={`${cardClass} opacity-80`}>{body}</article>;
  }

  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={cardClass}>
      {body}
    </a>
  );
}

function TransferCard({
  transfer,
  compact = false,
  layout = null,
}: {
  transfer: TransferItem;
  compact?: boolean;
  layout?: "wide" | "tall" | null;
}) {
  const href = safeExternalUrl(transfer.url);
  const imageSrc = resolveTransferImage(transfer.image_url);

  const cardClass = `group news-card flex h-full flex-col overflow-hidden rounded-xl border border-transparent bg-black/70 backdrop-blur-[3px] transition-[transform,border-color] duration-[160ms] ease-out hover:border-draw/40 active:scale-[0.99] ${compact ? "" : newsCardLayoutClass(layout)}`;

  const body = (
    <>
      <div
        className={`relative w-full overflow-hidden bg-card-border ${
          compact
            ? "aspect-[16/9]"
            : layout === "tall"
              ? "aspect-[4/5] sm:aspect-[3/4]"
              : layout === "wide"
                ? "aspect-[21/9]"
                : "aspect-[16/10]"
        }`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageSrc}
          alt={transfer.player_name}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
        />
      </div>
      <div className="flex flex-1 flex-col p-3 sm:p-4">
        <h3 className="line-clamp-2 type-ui text-sm group-hover:text-draw sm:text-[15px]">
          {stripDisplayDashes(transfer.player_name)}
        </h3>
        <p className="mt-1 line-clamp-2 text-xs text-muted sm:text-sm">
          {transfer.from_club && transfer.to_club
            ? `${stripDisplayDashes(transfer.from_club)} → ${stripDisplayDashes(transfer.to_club)}`
            : stripDisplayDashes(transfer.summary ?? "Transfer update")}
        </p>
        <div className="mt-auto flex flex-wrap items-center gap-2 pt-2 text-xs text-muted">
          {transfer.fee ? (
            <span className="rounded bg-draw/10 px-2 py-0.5 font-medium text-draw">
              {stripDisplayDashes(transfer.fee)}
            </span>
          ) : null}
          <span className="truncate">
            {stripDisplayDashes(transfer.source)} · {transfer.date}
          </span>
        </div>
      </div>
    </>
  );

  if (!href) {
    return <article className={`${cardClass} opacity-80`}>{body}</article>;
  }

  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={cardClass}>
      {body}
    </a>
  );
}

interface NewsViewProps {
  initialFeed: NewsFeedResponse | null;
}

export function NewsView({ initialFeed }: NewsViewProps) {
  const [feed, setFeed] = useState<NewsFeedResponse | null>(initialFeed);
  const [category, setCategory] = useState("All");
  const [loading, setLoading] = useState(false);

  const loadFeed = useCallback(async (selected: string) => {
    setLoading(true);
    const data = await fetchNewsFeedClient(selected);
    setFeed(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (category === "All" && initialFeed) {
      setFeed(initialFeed);
      return;
    }
    void loadFeed(category);
  }, [category, initialFeed, loadFeed]);

  const categories = feed?.categories ?? [
    "All",
    "World Cup",
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Transfers",
  ];

  const showTransfersOnly = category === "Transfers";
  const articles = feed?.articles ?? [];
  const transfers = feed?.transfers ?? [];

  return (
    <div className="space-y-8 pt-8 sm:pt-10">
      <div>
        <h1 className="type-display text-3xl">Football News</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted sm:text-base">
          Latest headlines from the World Cup, top leagues, and the transfer market.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {categories.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setCategory(item)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-[transform,color,background-color] duration-[160ms] ease-out active:scale-[0.97] ${
              category === item
                ? "bg-win/15 text-win ring-1 ring-win/30"
                : "bg-card text-muted ring-1 ring-card-border hover:text-white"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="rounded-xl border border-card-border bg-black/70 p-10 text-center text-sm text-muted backdrop-blur-[3px]">
          Loading latest news…
        </div>
      ) : !feed ? (
        <div className="rounded-xl border border-card-border bg-black/70 p-10 text-center text-sm text-muted backdrop-blur-[3px]">
          News unavailable. Ensure the backend is running.
        </div>
      ) : (
        <div
          className={`grid w-full gap-8 ${showTransfersOnly ? "" : "xl:grid-cols-[minmax(0,1fr)_minmax(16rem,18rem)]"}`}
        >
          <section className="min-w-0">
            <h2 className="mb-4 text-lg font-semibold">
              {showTransfersOnly ? "Transfer news" : "Latest headlines"}
            </h2>

            {!showTransfersOnly && articles.length === 0 ? (
              <p className="text-sm text-muted">No articles in this category right now.</p>
            ) : null}

            {!showTransfersOnly ? (
              <div className="news-grid">
                {articles.map((article, index) => (
                  <NewsCard key={article.id} article={article} layout={getNewsCardLayout(index)} />
                ))}
              </div>
            ) : null}

            {showTransfersOnly && transfers.length === 0 ? (
              <p className="text-sm text-muted">No recent transfers found.</p>
            ) : null}

            {showTransfersOnly ? (
              <div className="news-grid">
                {transfers.map((transfer, index) => (
                  <TransferCard key={transfer.id} transfer={transfer} layout={getNewsCardLayout(index)} />
                ))}
              </div>
            ) : null}
          </section>

          {!showTransfersOnly ? (
            <aside className="min-w-0 xl:sticky xl:top-24 xl:self-start">
              <h2 className="mb-4 text-lg font-semibold">Transfer market</h2>
              {transfers.length === 0 ? (
                <p className="text-sm text-muted">No recent transfers found.</p>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-1">
                  {transfers.slice(0, 8).map((transfer) => (
                    <TransferCard key={transfer.id} transfer={transfer} compact />
                  ))}
                </div>
              )}
            </aside>
          ) : null}
        </div>
      )}
    </div>
  );
}
