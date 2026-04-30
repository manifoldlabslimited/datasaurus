import { createContext, useContext } from "react";

/**
 * Carries the smoothed SSE inter-frame interval (ms) from `useBatchSSE` down
 * to each `ScatterCanvas` without triggering re-renders. The value is read
 * imperatively (`.current`) only when a new animation is about to start.
 */
const AnimContext = createContext<{ current: number }>({ current: 300 });

export const AnimProvider = AnimContext.Provider;
export const useFrameInterval = () => useContext(AnimContext);
