import { NewsBlobBackground } from "@/components/NewsBlobBackground";
import { NewsView } from "@/components/NewsView";
import { getNewsFeed } from "@/lib/api";
import { getBlobSceneSvg } from "@/lib/blobSceneSvg";

const NEWS_BLOB_SVG = getBlobSceneSvg("blob-scene-haikei-4.svg", "panel", "news-blob__svg");

export default async function NewsPage() {
  const feed = await getNewsFeed();

  return (
    <main className="container mx-auto bg-black px-4 pb-8 pt-0 sm:pb-10">
      <div className="news-panel relative isolate">
        <NewsBlobBackground svg={NEWS_BLOB_SVG} />
        <div className="relative z-10">
          <NewsView initialFeed={feed} />
        </div>
      </div>
    </main>
  );
}
