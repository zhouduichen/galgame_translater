"use client";

import { useEffect, useState } from "react";

const FALLBACK_BG_IMAGES = [
  "/assets/bg_school_gate.png",
  "/assets/bg_classroom.png",
  "/assets/bg_rooftop.png",
  "/assets/bg_sakura_path.png",
];

type Props = {
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
        } else {
          setSrc(FALLBACK_BG_IMAGES[Math.floor(Math.random() * FALLBACK_BG_IMAGES.length)]);
        }
      })
      .catch(() => {
        setSrc(FALLBACK_BG_IMAGES[Math.floor(Math.random() * FALLBACK_BG_IMAGES.length)]);
      });
  }, []);

  if (!src) return null;

  return (
    <div className="pointer-events-none fixed inset-0 -z-10">
      <img src={src} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0" style={{ backgroundColor: `rgba(0,0,0,${overlay})` }} />
    </div>
  );
}
