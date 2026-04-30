"use client";

import { useEffect, useRef } from "react";
import { animate, motionValue } from "framer-motion";
import { useFrameInterval } from "@/lib/anim-context";
import type { Point } from "@/lib/types";

const X_MIN = 0, X_MAX = 110, Y_MIN = 0, Y_MAX = 100;
const PAD = 14;
const DOT_R = 2.4;

interface CanvasState {
  n: number;
  fromX: Float32Array; fromY: Float32Array;
  toX: Float32Array;   toY: Float32Array;
}

function blankState(): CanvasState {
  const e = new Float32Array(0);
  return { n: 0, fromX: e, fromY: e, toX: e, toY: e };
}

/** Pure draw — no closures, no hooks. All state passed explicitly. */
function drawFrame(
  t: number,
  ctx: CanvasRenderingContext2D,
  s: CanvasState,
  w: number,
  h: number,
  dpr: number,
  dotColor: string,
) {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = dotColor;
  for (let i = 0; i < s.n; i++) {
    const x = s.fromX[i] + (s.toX[i] - s.fromX[i]) * t;
    const y = s.fromY[i] + (s.toY[i] - s.fromY[i]) * t;
    const cx = PAD + ((x - X_MIN) / (X_MAX - X_MIN)) * (w - PAD * 2);
    const cy = h - PAD - ((y - Y_MIN) / (Y_MAX - Y_MIN)) * (h - PAD * 2);
    ctx.beginPath();
    ctx.arc(cx, cy, DOT_R, 0, Math.PI * 2);
    ctx.fill();
  }
}

export function ScatterCanvas({ points }: { points: Point[] | null }) {
  const canvasRef     = useRef<HTMLCanvasElement>(null);
  const ctxRef        = useRef<CanvasRenderingContext2D | null>(null);
  const csRef         = useRef<CanvasState>(blankState());
  const dimRef        = useRef({ w: 0, h: 0, dpr: 1 });
  const colorRef      = useRef(""); // populated on mount from --dot-color
  const mvRef         = useRef(motionValue(1)); // framer-motion scalar 0→1
  const frameInterval = useFrameInterval();

  // Acquire 2D context once on mount
  useEffect(() => {
    ctxRef.current = canvasRef.current!.getContext("2d");
  }, []);

  // Cache dot color; refresh automatically when the theme class on <html> changes
  useEffect(() => {
    const read = () => {
      colorRef.current =
        getComputedStyle(document.documentElement)
          .getPropertyValue("--dot-color").trim() || "currentColor";
    };
    read();
    const mo = new MutationObserver(read);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => mo.disconnect();
  }, []);

  // Cache logical dimensions — avoids layout-triggering reads inside the rAF loop
  useEffect(() => {
    const canvas = canvasRef.current!;
    const ro = new ResizeObserver(() => {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      dimRef.current = { w, h, dpr };
    });
    ro.observe(canvas);
    return () => ro.disconnect();
  }, []);

  // Framer-motion spring toward new point positions
  useEffect(() => {
    const s = csRef.current;

    if (!points || points.length === 0) {
      // React already ran the previous effect's cleanup, which stopped any
      // in-flight animation. Just reset visual state.
      s.n = 0;
      const canvas = canvasRef.current!;
      ctxRef.current?.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    const n = points.length;

    // "from" = current interpolated positions at the moment of interruption
    const fromX = new Float32Array(n);
    const fromY = new Float32Array(n);
    if (s.n === n) {
      const t = mvRef.current.get();
      for (let i = 0; i < n; i++) {
        fromX[i] = s.fromX[i] + (s.toX[i] - s.fromX[i]) * t;
        fromY[i] = s.fromY[i] + (s.toY[i] - s.fromY[i]) * t;
      }
    } else {
      // Point count changed — snap, no transition
      for (let i = 0; i < n; i++) { fromX[i] = points[i][0]; fromY[i] = points[i][1]; }
    }

    const toX = new Float32Array(n);
    const toY = new Float32Array(n);
    for (let i = 0; i < n; i++) { toX[i] = points[i][0]; toY[i] = points[i][1]; }

    // Preserve velocity for smooth hand-off across interrupted animations
    // Velocity from framer-motion's own spring math — precise, no manual tracking
    const prevVelocity = mvRef.current.getVelocity();

    // Adaptive stiffness: snappier for fast SSE frames, more organic for slow.
    // interval===0 means "not yet measured" → snap to target immediately.
    const interval = frameInterval.current;
    const stiffness = interval === 0
      ? 2_000                                                      // first frame: snap
      : Math.min(700, Math.max(120, 1_800_000 / (interval * interval)));

    Object.assign(s, { n, fromX, fromY, toX, toY });
    mvRef.current.set(0);

    const anim = animate(mvRef.current, 1, {
      type: "spring",
      stiffness,
      damping: 26,
      velocity: prevVelocity,
    });

    const unsub = mvRef.current.on("change", (t) => {
      const ctx = ctxRef.current;
      if (ctx) {
        const { w, h, dpr } = dimRef.current;
        drawFrame(t, ctx, s, w, h, dpr, colorRef.current);
      }
    });

    // Single authoritative cleanup — no double-stop possible
    return () => { anim.stop(); unsub(); };
  }, [points]);

  return <canvas ref={canvasRef} className="w-full h-full block" />;
}

