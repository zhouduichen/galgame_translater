import fs from "fs";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

const BG_DIR = path.resolve(process.cwd(), "..", "..", "背景图");

const MIME: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  gif: "image/gif",
};

export async function GET(request: NextRequest) {
  const file = request.nextUrl.searchParams.get("file");

  // Serve a specific image file
  if (file) {
    const decoded = decodeURIComponent(file);
    const filePath = path.join(BG_DIR, decoded);
    if (!filePath.startsWith(BG_DIR)) {
      return new NextResponse(null, { status: 404 });
    }
    try {
      const buffer = fs.readFileSync(filePath);
      const ext = path.extname(decoded).slice(1).toLowerCase();
      return new NextResponse(buffer, {
        headers: { "Content-Type": MIME[ext] ?? "application/octet-stream" },
      });
    } catch {
      return new NextResponse(null, { status: 404 });
    }
  }

  // List all images
  try {
    const files = fs.readdirSync(BG_DIR).filter((f) =>
      /\.(jpg|jpeg|png|webp|gif)$/i.test(f)
    );
    return NextResponse.json({
      images: files.map((f) => "/api/bg-images?file=" + encodeURIComponent(f)),
    });
  } catch {
    return NextResponse.json({ images: [] });
  }
}
