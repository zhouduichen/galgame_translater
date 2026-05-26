"use client";

import Link from "next/link";
import { useRef, useState, useEffect } from "react";
import { gsap } from "gsap";
import { Plus } from "lucide-react";

export default function HomePage() {
  const cardRef = useRef<HTMLDivElement>(null);
  const pixelGridRef = useRef<HTMLDivElement>(null);
  const tagsRef = useRef<HTMLDivElement>(null);
  const customCursorRef = useRef<HTMLDivElement>(null);
  const [showCustomCursor, setShowCustomCursor] = useState(false);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/bg-videos")
      .then((res) => res.json())
      .then((data) => {
        if (data.videos && data.videos.length > 0) {
          const randomIndex = Math.floor(Math.random() * data.videos.length);
          setVideoSrc(data.videos[randomIndex]);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const tagsElement = tagsRef.current;
    const cursorElement = customCursorRef.current;
    if (!tagsElement || !cursorElement) return;

    let cursorX = 0;
    let cursorY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      cursorX = e.clientX;
      cursorY = e.clientY;
      gsap.to(cursorElement, {
        x: cursorX - 15,
        y: cursorY - 15,
        duration: 0.3,
        ease: "power2.out",
      });
    };

    const handleMouseEnter = () => setShowCustomCursor(true);
    const handleMouseLeave = () => setShowCustomCursor(false);

    tagsElement.addEventListener("mouseenter", handleMouseEnter);
    tagsElement.addEventListener("mouseleave", handleMouseLeave);
    tagsElement.addEventListener("mousemove", handleMouseMove);

    return () => {
      tagsElement.removeEventListener("mouseenter", handleMouseEnter);
      tagsElement.removeEventListener("mouseleave", handleMouseLeave);
      tagsElement.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  const handleMouseLeave = () => {
    if (!cardRef.current || !pixelGridRef.current) return;

    const gridSize = 4;
    const pixelSize = 100 / gridSize;

    pixelGridRef.current.innerHTML = "";

    const totalPixels = gridSize * gridSize;
    const clearIndices = new Set<number>();
    while (clearIndices.size < 3) {
      clearIndices.add(Math.floor(Math.random() * totalPixels));
    }

    let pixelIndex = 0;
    for (let row = 0; row < gridSize; row++) {
      for (let col = 0; col < gridSize; col++) {
        if (clearIndices.has(pixelIndex)) { pixelIndex++; continue; }

        const pixel = document.createElement("div");
        const isAccent = Math.random() < 0.5;
        const targetOpacity = Math.random() * 0.5 + 0.5;

        pixel.className = `absolute ${isAccent ? "bg-white/30" : "bg-black/50"}`;
        pixel.style.width = `${pixelSize}%`;
        pixel.style.height = `${pixelSize}%`;
        pixel.style.left = `${col * pixelSize}%`;
        pixel.style.top = `${row * pixelSize}%`;
        pixel.style.opacity = "0";
        pixel.style.display = "block";
        pixel.setAttribute("data-target-opacity", targetOpacity.toString());
        pixelGridRef.current.appendChild(pixel);

        pixelIndex++;
      }
    }

    const pixels = Array.from(pixelGridRef.current.children);
    const animationStepDuration = 0.45;
    const actualPixelCount = pixels.length;
    const staggerDuration = animationStepDuration / actualPixelCount;

    const tl = gsap.timeline();

    tl.to(cardRef.current, { scale: 0.995, duration: 0.2, ease: "power2.in" });

    tl.to(
      pixels,
      {
        opacity: (_index, target) => {
          const el = target as HTMLElement;
          return el.getAttribute("data-target-opacity") || "1";
        },
        duration: 0.45,
        ease: "power2.in",
        stagger: { each: staggerDuration, from: "random" },
      },
      "<",
    );

    tl.to(pixels, { opacity: 0, duration: 0.3, ease: "power2.out" }, `+=${animationStepDuration}`);

    tl.to(cardRef.current, { scale: 1, duration: 0.3, ease: "power2.in" }, "<");

    tl.set(pixels, { display: "none" });
  };

  return (
    <section className="bg-zinc-950 min-h-svh">
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <defs>
          <mask id="heroMask" maskContentUnits="objectBoundingBox">
            <rect width="1" height="1" fill="white" />
          </mask>
        </defs>
      </svg>

      <div className="relative isolate w-full min-h-svh">
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ mask: "url(#heroMask)", WebkitMask: "url(#heroMask)" }}
        >
          {/* Anime video background */}
          <div className="absolute inset-0">
            {videoSrc && (
              <video
                key={videoSrc}
                autoPlay
                loop
                muted
                playsInline
                className="absolute inset-0 w-full h-full object-cover"
              >
                <source src={videoSrc} type="video/mp4" />
              </video>
            )}
          </div>

          {/* Gradient overlays for readability */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-b from-zinc-950/40 via-transparent to-zinc-950/60" />
            <div className="absolute inset-0 bg-gradient-to-r from-zinc-950/50 via-zinc-950/10 to-transparent" />
            <div className="absolute inset-0 [background:radial-gradient(90%_60%_at_10%_70%,rgba(0,0,0,.45)_0%,transparent_70%)]" />
          </div>

          {/* Bottom info card */}
          <div className="absolute bottom-6 left-6 right-6 max-w-[min(46rem,92vw)] md:bottom-8 md:left-8 z-10">
            <div
              ref={cardRef}
              onMouseLeave={handleMouseLeave}
              className="relative overflow-hidden backdrop-blur-xl bg-white/5 border border-white/20 rounded-2xl p-6 md:p-8 transition-transform duration-500 ease-in hover:scale-[1.01] shadow-[0_8px_32px_rgba(255,255,255,0.1)]"
            >
              <div ref={pixelGridRef} className="absolute inset-0 pointer-events-none z-10" />

              <h1 className="text-balance text-3xl/tight sm:text-4xl/tight md:text-5xl/tight tracking-tight text-white">
                将你的小说变成 Galgame
              </h1>
              <p className="mt-3 text-sm/6 text-white/85 max-w-prose">
                上传你喜爱的小说，AI 将自动为你生成精美的视觉小说场景，配合动态背景和角色立绘，打造沉浸式的 Galgame 体验。
              </p>
              <Link
                href="/studio"
                className="mt-4 inline-flex items-center rounded-full border border-white/30 bg-white/10 hover:bg-white/20 px-4 py-2 text-sm font-medium text-white backdrop-blur-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white transition-colors"
              >
                开始创作
              </Link>
            </div>
          </div>
        </div>

        {/* Top tags */}
        <div ref={tagsRef} className="absolute top-4 left-1/2 -translate-x-1/2 z-20 cursor-none pb-10">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white font-normal">Made with</span>
            <button className="rounded-full border border-white/30 bg-white/10 backdrop-blur-md px-3 py-1 text-xs font-bold text-white">
              AI
            </button>
            <Plus className="w-3 h-3 text-white stroke-[2.5]" />
            <button className="rounded-full border border-white/30 bg-white/10 backdrop-blur-md px-3 py-1 text-xs font-bold text-white">
              v0
            </button>
          </div>
        </div>

        {/* Custom cursor */}
        <div
          ref={customCursorRef}
          className={`fixed w-[30px] h-[30px] rounded-full bg-white/50 backdrop-blur-sm pointer-events-none z-50 transition-opacity duration-200 ${
            showCustomCursor ? "opacity-100" : "opacity-0"
          }`}
          style={{ left: 0, top: 0 }}
        />
      </div>
    </section>
  );
}
