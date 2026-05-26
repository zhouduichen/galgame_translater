"use client";

import { useEffect, useState } from "react";

type Props = {
  /** 遮罩不透明度，默认 0.5 */
  overlay?: number;
};

export function BgImage({ overlay = 0.5 }: Props) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/bg-images")
      .then((r) => r.json())
      .then((data) => {
        const images: string[] = data.images ?? [];
        if (images.length > 0) {
          setSrc(images[Math.floor(Math.random() * images.length)]);
        }
      })
      .catch(() => {});
  }, []);

  if (!src) return null;

  return (
    <div className="pointer-events-none fixed inset-0 -z-10">
      <img src={src} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0" style={{ backgroundColor: `rgba(0,0,0,${overlay})` }} />
    </div>
  );
}
