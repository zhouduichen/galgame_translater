"use client";

import { useEffect, useRef } from "react";
import { usePlayerStore } from "@/stores/playerStore";
import { BackgroundLayer } from "./BackgroundLayer";
import { CharacterSprite } from "./CharacterSprite";
import { DialogueBox } from "./DialogueBox";
import { NarrationBox } from "./NarrationBox";
import { ChoicePanel } from "./ChoicePanel";
import { PlayerControls } from "./PlayerControls";
import type { Project } from "@/lib/types";

type Props = {
  project: Project;
};

export function PlayerContainer({ project }: Props) {
  const store = usePlayerStore();
  const autoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load project on mount
  useEffect(() => {
    store.loadProject(project);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.project_id]);

  // Auto-advance
  const { node, status, autoMode, textSpeed } = usePlayerStore();
  useEffect(() => {
    if (autoMode && status === "playing" && node) {
      const text = "text" in node ? node.text || "" : "";
      const delay = Math.max(800, text.length ? text.length * textSpeed + 600 : 1500);
      autoTimer.current = setTimeout(() => {
        if (node.type === "dialogue" && node.next_node_id) {
          const scene = usePlayerStore.getState().scene;
          if (scene && scene.nodes[node.next_node_id]) {
            store.goTo(scene.nodes[node.next_node_id]);
          }
        }
      }, delay);
      return () => {
        if (autoTimer.current) clearTimeout(autoTimer.current);
      };
    }
  }, [autoMode, status, node, textSpeed, store]);

  const {
    scene,
    history,
    goTo,
    goBack,
    restartScene,
    toggleAutoMode,
    setTextSpeed,
  } = store;

  if (!scene || !node) {
    return <div className="flex h-screen items-center justify-center text-[#8888a0]">Loading...</div>;
  }

  const backgroundRes = scene.background_id ? project.asset_resources[scene.background_id] : null;

  return (
    <div className="relative h-screen w-full overflow-hidden bg-black">
      {/* Background layer */}
      <BackgroundLayer resource={backgroundRes} />

      {/* Character sprite / scene content */}
      {node.type === "dialogue" && (
        <CharacterSprite
          character={project.characters[node.character_id] ?? null}
          emotion={node.emotion}
          side={node.side}
          assetResources={project.asset_resources}
        />
      )}

      {/* Foreground overlay based on node type */}
      {node.type === "dialogue" && (
        <DialogueBox
          text={node.text}
          character={project.characters[node.character_id] ?? null}
          emotion={node.emotion}
          textSpeed={textSpeed}
          onClick={() => {
            if (node.next_node_id && scene.nodes[node.next_node_id]) {
              goTo(scene.nodes[node.next_node_id]);
            }
          }}
        />
      )}

      {node.type === "narration" && (
        <NarrationBox
          text={node.text}
          textSpeed={textSpeed}
          onClick={() => {
            if (node.next_node_id && scene.nodes[node.next_node_id]) {
              goTo(scene.nodes[node.next_node_id]);
            }
          }}
        />
      )}

      {node.type === "choice" && (
        <ChoicePanel
          narration={node.text}
          options={node.options}
          onChoose={(opt) => {
            if (scene.nodes[opt.next_node_id]) {
              goTo(scene.nodes[opt.next_node_id]);
            }
          }}
        />
      )}

      {node.type === "scene_transition" && (
        <div className="flex h-full items-center justify-center">
          <p className="animate-pulse text-[#8888a0]">Loading next scene...</p>
        </div>
      )}

      {node.type === "ending" && (
        <div className="flex h-full items-center justify-center">
          <div className="rounded-lg border border-[#2a2a3a] bg-[#1a1a25]/80 p-8 text-center backdrop-blur-sm">
            <span className="mb-3 inline-block rounded-full bg-[#6688ff]/20 px-3 py-1 text-xs text-[#6688ff]">
              {node.ending_type} ending
            </span>
            {node.epilogue && <p className="mt-4 text-lg italic">{node.epilogue}</p>}
            <button
              className="mt-8 rounded-lg bg-[#6688ff] px-6 py-2 text-sm text-white transition-colors hover:bg-[#5577ee]"
              onClick={restartScene}
            >
              Restart scene
            </button>
          </div>
        </div>
      )}

      {/* Controls */}
      <PlayerControls
        status={status}
        autoMode={autoMode}
        textSpeed={textSpeed}
        hasHistory={history.length > 0}
        onBack={goBack}
        onToggleAuto={toggleAutoMode}
        onTextSpeedChange={setTextSpeed}
        onRestart={restartScene}
      />

      {/* Scene title + Edit */}
      <div className="absolute left-4 top-4 flex items-center gap-2">
        <span className="rounded bg-[#1a1a25]/60 px-2 py-1 text-xs text-[#555568]">
          {scene.title}
        </span>
        <a
          href={`/project/${project.project_id}/edit`}
          className="rounded bg-[#1a1a25]/60 px-2 py-1 text-xs text-[#6688ff] transition-colors hover:bg-[#6688ff]/30"
        >
          Edit
        </a>
      </div>
    </div>
  );
}
