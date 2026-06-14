interface NewsBlobBackgroundProps {
  svg: string;
}

export function NewsBlobBackground({ svg }: NewsBlobBackgroundProps) {
  return (
    <div
      className="news-blob pointer-events-none"
      data-visible="true"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
