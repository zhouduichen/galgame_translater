import { useEffect, useState, useRef, useCallback } from "react";

export function useTypewriter(text: string, speedMs: number, enabled: boolean = true) {
  const [displayed, setDisplayed] = useState("");
  const [complete, setComplete] = useState(false);
  const indexRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const skip = useCallback(() => {
    setDisplayed(text);
    setComplete(true);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, [text]);

  useEffect(() => {
    setDisplayed("");
    setComplete(false);
    indexRef.current = 0;
    if (!enabled || speedMs <= 0) {
      setDisplayed(text);
      setComplete(true);
      return;
    }
    timerRef.current = setTimeout(function tick() {
      indexRef.current++;
      setDisplayed(text.slice(0, indexRef.current));
      if (indexRef.current >= text.length) {
        setComplete(true);
      } else {
        timerRef.current = setTimeout(tick, speedMs);
      }
    }, speedMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [text, speedMs, enabled]);

  return { displayed, complete, skip };
}
