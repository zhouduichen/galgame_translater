import type { AssetResource } from "@/lib/types";

export function BackgroundLayer({ resource }: { resource?: AssetResource | null }) {
  if (!resource || resource.url.startsWith("/assets/placeholder")) {
    return (
      <div className="absolute inset-0 bg-gradient-to-b from-[var(--bg-deep)] via-sakura-pink/5 to-[var(--bg-deep)]" />
    );
  }
  return (
    <div className="absolute inset-0">
      <img src={resource.url} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0 bg-black/30" />
    </div>
  );
}
