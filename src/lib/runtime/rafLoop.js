/** Shared requestAnimationFrame scheduler — one loop for all subscribers. */

const callbacks = new Set();
let rafId = 0;

function tick(time) {
  rafId = 0;
  callbacks.forEach((fn) => {
    try {
      fn(time);
    } catch {
      /* isolate subscriber failures */
    }
  });
  if (callbacks.size > 0) {
    rafId = requestAnimationFrame(tick);
  }
}

function ensureRunning() {
  if (!rafId && callbacks.size > 0) {
    rafId = requestAnimationFrame(tick);
  }
}

/** Subscribe to the shared animation frame loop. Returns unsubscribe. */
export function subscribeAnimationFrame(callback) {
  callbacks.add(callback);
  ensureRunning();
  return () => {
    callbacks.delete(callback);
    if (callbacks.size === 0 && rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
  };
}

/** Returns true when the shared loop is active. */
export function isAnimationLoopRunning() {
  return rafId !== 0;
}
