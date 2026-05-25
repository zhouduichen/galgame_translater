"use client";

import type { Character, AssetResource, Side } from "@/lib/types";

type Props = {
  character?: Character | null;
  emotion?: string;
  side: Side;
  assetResources: Record<string, AssetResource>;
};

export function CharacterSprite({ character, emotion, side, assetResources }: Props) {
  if (!character) return null;

  const assetId = emotion ? character.asset_ids[emotion] : null;
  const resource = assetId ? assetResources[assetId] : null;

  const sideClasses: Record<Side, string> = {
    left: "left-0 translate-x-0",
    right: "right-0 translate-x-0",
    center: "left-1/2 -translate-x-1/2",
  };

  return (
    <div className={`pointer-events-none absolute bottom-0 ${sideClasses[side]} h-[85%] w-auto max-w-[45%]`}>
      {resource && !resource.url.startsWith("/assets/placeholder") ? (
        <img src={resource.url} alt={character.name} className="h-full w-auto object-contain" />
      ) : (
        <div className="flex h-full w-48 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-2 flex h-24 w-24 items-center justify-center rounded-full border-2 border-[#2a2a3a] bg-[#1a1a25] text-3xl">
              {character.name.charAt(0)}
            </div>
            <p className="text-sm text-[#8888a0]">{character.name}</p>
          </div>
        </div>
      )}
    </div>
  );
}
