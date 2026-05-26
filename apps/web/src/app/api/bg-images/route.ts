import fs from "fs";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

function findBgDir(): string | null {
  if (process.env.BG_IMAGES_DIR) return process.env.BG_IMAGES_DIR;
  const fromRepo = path.resolve(process.cwd(), "..", "..", "背景图");
  if (fs.existsSync(fromRepo)) return fromRepo;
  const fromCwd = path.resolve(process.cwd(), "背景图");
  if (fs.existsSync(fromCwd)) return fromCwd;
  return null;
}

const BG_DIR = findBgDir();

const MIME: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  gif: "image/gif",
};

export async function GET(request: NextRequest) {
  if (!BG_DIR) {
    return NextResponse.json({ images: [] });
  }

  const bgDir: string = BG_DIR;

  const file = request.nextUrl.searchParams.get("file");

  // Serve a specific image file
  if (file) {
    function safeImagePath(f: string, base: string): string | null {
      const decoded = decodeURIComponent(f);
      const filePath = path.resolve(base, decoded);
      const relative = path.relative(base, filePath);
      if (relative.startsWith("..") || path.isAbsolute(relative)) return null;
      return filePath;
    }

    const filePath = safeImagePath(file, bgDir);
    if (!filePath) {
      return new NextResponse(null, { status: 404 });
    }
    try {
      const buffer = fs.readFileSync(filePath);
      const ext = path.extname(filePath).slice(1).toLowerCase();
      return new NextResponse(buffer, {
        headers: { "Content-Type": MIME[ext] ?? "application/octet-stream" },
      });
    } catch {
      return new NextResponse(null, { status: 404 });
    }
  }

  // List all images
  try {
    const files = fs.readdirSync(bgDir).filter((f) =>
      /\.(jpg|jpeg|png|webp|gif)$/i.test(f)
    );
    return NextResponse.json({
      images: files.map((f) => "/api/bg-images?file=" + encodeURIComponent(f)),
    });
  } catch {
    return NextResponse.json({ images: [] });
  }
}
