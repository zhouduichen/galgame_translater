import fs from "fs";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

function findVideoDir(): string {
  if (process.env.BG_VIDEOS_DIR) return process.env.BG_VIDEOS_DIR;
  const fromRepo = path.resolve(process.cwd(), "..", "..", "视频");
  if (fs.existsSync(fromRepo)) return fromRepo;
  const fromCwd = path.resolve(process.cwd(), "视频");
  if (fs.existsSync(fromCwd)) return fromCwd;
  return fromRepo;
}

const VIDEO_DIR = findVideoDir();

const MIME: Record<string, string> = {
  mp4: "video/mp4",
  webm: "video/webm",
  ogg: "video/ogg",
  mov: "video/quicktime",
  avi: "video/x-msvideo",
};

export async function GET(request: NextRequest) {
  const file = request.nextUrl.searchParams.get("file");

  if (file) {
    function safePath(f: string): string | null {
      const decoded = decodeURIComponent(f);
      const filePath = path.resolve(VIDEO_DIR, decoded);
      const relative = path.relative(VIDEO_DIR, filePath);
      if (relative.startsWith("..") || path.isAbsolute(relative)) return null;
      return filePath;
    }

    const filePath = safePath(file);
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

  try {
    const files = fs.readdirSync(VIDEO_DIR).filter((f) =>
      /\.(mp4|webm|ogg|mov|avi)$/i.test(f)
    );
    return NextResponse.json({
      videos: files.map((f) => "/api/bg-videos?file=" + encodeURIComponent(f)),
    });
  } catch {
    return NextResponse.json({ videos: [] });
  }
}
