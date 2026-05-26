import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";

export async function GET() {
  const dir = path.join(process.cwd(), "public", "assets", "bg");
  try {
    const files = fs.readdirSync(dir).filter((f) =>
      /\.(jpg|jpeg|png|webp|gif)$/i.test(f)
    );
    return NextResponse.json({ images: files.map((f) => "/assets/bg/" + f) });
  } catch {
    return NextResponse.json({ images: [] });
  }
}
