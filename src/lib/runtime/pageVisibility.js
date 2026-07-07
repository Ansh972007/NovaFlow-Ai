/** Shared document visibility — single visibilitychange listener. */

let visible = typeof document !== "undefined" ? document.visibilityState !== "hidden" : true;
const subscribers = new Set();
let initialized = false;

function init() {
  if (initialized || typeof document === "undefined") return;
  initialized = true;
  document.addEventListener("visibilitychange", () => {
    visible = document.visibilityState !== "hidden";
    subscribers.forEach((fn) => fn(visible));
  });
}

export function isPageVisible() {
  init();
  return visible;
}

/** Subscribe to visibility changes. Returns unsubscribe. */
export function subscribeVisibility(callback) {
  init();
  subscribers.add(callback);
  return () => subscribers.delete(callback);
}
