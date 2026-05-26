"use client";

import { useEffect, useState } from "react";

/**
 * 添加新背景图：
 * 1. 把图片文件放入 public/assets/bg/
 * 2. 在下方 IMAGES 数组中添加路径即可
 */
const IMAGES = [
  "/assets/bg/131588635_p0_master1200(1).jpg",
  "/assets/bg/131588635_p0_master1200(2).jpg",
  "/assets/bg/142935665_p0(1).jpg",
];

type Props = {
  /** 遮罩不透明度，默认 0.5 */
  overlay?: number;
};

export function BgImage({ overlay = 0.5 }: Props) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    setSrc(IMAGES[Math.floor(Math.random() * IMAGES.length)]);
  }, []);

  if (!src) return null;

  return (
    <div className="pointer-events-none fixed inset-0 -z-10">
      <img src={src} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0" style={{ backgroundColor: `rgba(0,0,0,${overlay})` }} />
    </div>
  );
}
