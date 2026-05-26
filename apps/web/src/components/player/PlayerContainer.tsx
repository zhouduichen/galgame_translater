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

  useEffect(() => {
    store.loadProject(project);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.project_id]);

  const { node, status, autoMode, textSpeed } = usePlayerStore();
  useEffect(() => {
    if (autoMode && status === "playing" && node) {
      const text = "text" in node ? node.text || "" : "";
      const delay = Math.max(800, text.length ? text.length * textSpeed + 600 : 1500);
      autoTimer.current = setTimeout(() => {
        const state = usePlayerStore.getState();
        if (state.node && state.node.type !== "choice" && state.node.type !== "ending") {
          state.advance();
        }
      }, delay);
      return () => {
        if (autoTimer.current) clearTimeout(autoTimer.current);
      };
    }
  }, [autoMode, status, node, textSpeed]);

  const {
    scene,
    history,
    advance,
    chooseOption,
    goBack,
    restartScene,
    toggleAutoMode,
    setTextSpeed,
  } = store;

  if (!scene || !node) {
    return <div className="flex h-screen items-center justify-center text-[var(--text-secondary)]">加载中...</div>;
  }

  const backgroundRes = scene.background_id ? project.asset_resources[scene.background_id] : null;

  return (
    <div className="relative h-screen w-full overflow-hidden bg-[var(--bg-deep)]">
      <BackgroundLayer resource={backgroundRes} />

      {node.type === "dialogue" && (
        <CharacterSprite
          character={project.characters[node.character_id] ?? null}
          emotion={node.emotion}
          side={node.side}
          assetResources={project.asset_resources}
        />
      )}

      {node.type === "dialogue" && (
        <DialogueBox
          text={node.text}
          character={project.characters[node.character_id] ?? null}
          emotion={node.emotion}
          textSpeed={textSpeed}
          onClick={advance}
        />
      )}

      {node.type === "narration" && (
        <NarrationBox
          text={node.text}
          textSpeed={textSpeed}
          onClick={advance}
        />
      )}

      {node.type === "choice" && (
        <ChoicePanel
          narration={node.text}
          options={node.options}
          onChoose={(opt) => chooseOption(opt.option_id)}
        />
      )}

      {node.type === "scene_transition" && (
        <div className="flex h-full items-center justify-center">
          <p className="animate-pulse text-[var(--text-secondary)]">正在切换到下一幕...</p>
        </div>
      )}

      {node.type === "ending" && (
        <div className="flex h-full items-center justify-center">
          <div className="rounded-lg border border-[var(--bg-border)] bg-[var(--bg-card)]/80 p-8 text-center backdrop-blur-sm">
            <span className="mb-3 inline-block rounded-full bg-sakura-pink/20 px-3 py-1 text-xs text-sakura-pink">
              {node.ending_type} ending
            </span>
            {node.epilogue && <p className="mt-4 text-lg italic text-[var(--text-primary)]">{node.epilogue}</p>}
            <button
              className="mt-8 rounded-lg bg-sakura-pink px-6 py-2 text-sm text-white transition-colors hover:bg-sakura-deep"
              onClick={restartScene}
            >
              重新开始本幕
            </button>
          </div>
        </div>
      )}

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

      <div className="absolute left-4 top-4 flex items-center gap-2">
        <span className="rounded bg-[var(--bg-card)]/60 px-2 py-1 text-xs text-[var(--text-muted)]">
          {scene.title}
        </span>
        <a
          href={`/project/${project.project_id}/edit`}
          className="rounded bg-[var(--bg-card)]/60 px-2 py-1 text-xs text-sakura-pink transition-colors hover:bg-sakura-pink/30"
        >
          编辑
        </a>
      </div>
    </div>
  );
}
