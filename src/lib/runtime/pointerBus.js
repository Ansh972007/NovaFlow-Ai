/** Shared pointer position — one mousemove listener, rAF-batched subscribers. */

let clientX = 0;
let clientY = 0;
let active = false;
let dirty = false;
let flushRaf = 0;

const subscribers = new Set();
let listening = false;

function flushPointer() {
  flushRaf = 0;
  if (!dirty) return;
  dirty = false;
  subscribers.forEach((fn) => fn(clientX, clientY, active));
}

function scheduleFlush() {
  if (flushRaf) return;
  flushRaf = requestAnimationFrame(flushPointer);
}

function onMouseMove(e) {
  clientX = e.clientX;
  clientY = e.clientY;
  active = true;
  dirty = true;
  scheduleFlush();
}

function onMouseLeave() {
  active = false;
  dirty = true;
  scheduleFlush();
}

function ensureListener() {
  if (listening || typeof window === "undefined") return;
  listening = true;
  window.addEventListener("mousemove", onMouseMove, { passive: true });
  document.addEventListener("mouseleave", onMouseLeave);
}

function maybeRemoveListener() {
  if (subscribers.size > 0 || !listening) return;
  window.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseleave", onMouseLeave);
  listening = false;
  if (flushRaf) {
    cancelAnimationFrame(flushRaf);
    flushRaf = 0;
  }
}

/** Latest pointer in viewport coordinates (updated synchronously on move). */
export function getPointer() {
  return { clientX, clientY, active };
}

/**
 * Subscribe to rAF-batched pointer updates.
 * @param {(clientX: number, clientY: number, active: boolean) => void} callback
 */
export function subscribePointer(callback) {
  ensureListener();
  subscribers.add(callback);
  callback(clientX, clientY, active);
  return () => {
    subscribers.delete(callback);
    maybeRemoveListener();
  };
}
