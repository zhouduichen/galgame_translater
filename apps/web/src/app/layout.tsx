import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Galgame Translater",
  description: "Upload novels → generate playable visual novels",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
