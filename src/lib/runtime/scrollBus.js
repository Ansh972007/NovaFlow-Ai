/** Shared scroll position — one scroll listener, rAF-batched subscribers. */

let scrollY = 0;
let dirty = false;
let flushRaf = 0;
let listening = false;

const subscribers = new Set();

function flushScroll() {
  flushRaf = 0;
  if (!dirty) return;
  dirty = false;
  subscribers.forEach((fn) => fn(scrollY));
}

function scheduleFlush() {
  if (flushRaf) return;
  flushRaf = requestAnimationFrame(flushScroll);
}

function onScroll() {
  scrollY = window.scrollY;
  dirty = true;
  scheduleFlush();
}

function ensureListener() {
  if (listening || typeof window === "undefined") return;
  listening = true;
  scrollY = window.scrollY;
  window.addEventListener("scroll", onScroll, { passive: true });
}

function maybeRemoveListener() {
  if (subscribers.size > 0 || !listening) return;
  window.removeEventListener("scroll", onScroll);
  listening = false;
  if (flushRaf) {
    cancelAnimationFrame(flushRaf);
    flushRaf = 0;
  }
}

export function getScrollY() {
  return scrollY;
}

/** Subscribe to rAF-batched scroll updates. Returns unsubscribe. */
export function subscribeScroll(callback) {
  ensureListener();
  subscribers.add(callback);
  callback(scrollY);
  return () => {
    subscribers.delete(callback);
    maybeRemoveListener();
  };
}
