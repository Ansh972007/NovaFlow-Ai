/** Single rAF-smoothed mouse position as CSS custom properties (replaces per-component Framer springs). */

import { getPointer } from "./pointerBus";
import { subscribeAnimationFrame } from "./rafLoop";

let refCount = 0;
let smoothX = -500;
let smoothY = -500;
let unsubFrame = null;

function tick() {
  const { clientX, clientY, active } = getPointer();
  const targetX = active ? clientX : smoothX;
  const targetY = active ? clientY : smoothY;
  const ease = active ? 0.14 : 0.05;
  smoothX += (targetX - smoothX) * ease;
  smoothY += (targetY - smoothY) * ease;

  if (typeof document !== "undefined") {
    const root = document.documentElement;
    root.style.setProperty("--nf-mx", `${smoothX}px`);
    root.style.setProperty("--nf-my", `${smoothY}px`);
  }
}

/** Enable shared CSS mouse tracking. Returns cleanup. */
export function enableMouseCss() {
  refCount += 1;
  if (refCount === 1 && !unsubFrame) {
    unsubFrame = subscribeAnimationFrame(tick);
  }
  return () => {
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0 && unsubFrame) {
      unsubFrame();
      unsubFrame = null;
    }
  };
}
