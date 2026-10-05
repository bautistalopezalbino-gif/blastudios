"use client";

import { memo } from "react";
import type { Word } from "@/lib/types";

type Props = {
  words: Word[];
  onChange: (index: number, text: string) => void;
  onSeek: (t: number) => void;
};

/**
 * Lista de palabras editables. Memorizada: con videos largos hay miles de palabras y no debe
 * volver a pintarse cada vez que avanza el cabezal (onChange y onSeek tienen que ser estables).
 */
export default memo(function WordList({ words, onChange, onSeek }: Props) {
  if (!words.length) return null;
  return (
    <div className="words">
      {words.map((w, i) => (
        <input
          key={i}
          value={w.text}
          title={`${w.start.toFixed(2)} – ${w.end.toFixed(2)} s`}
          size={Math.max(2, w.text.length)}
          onFocus={() => onSeek(w.start)}
          onChange={(e) => onChange(i, e.target.value)}
        />
      ))}
    </div>
  );
});
