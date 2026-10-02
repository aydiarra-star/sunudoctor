/**
 * Offline-first helpers.
 *
 * Requests that cannot reach the backend are queued in localStorage and
 * replayed when connectivity returns. Nothing is invented: queued items are
 * clearly pending and surfaced to the user.
 */
export interface QueuedRequest {
  id: string;
  path: string;
  method: string;
  body?: unknown;
  createdAt: number;
}

const QUEUE_KEY = "sd_sync_queue";

export function getQueue(): QueuedRequest[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? "[]") as QueuedRequest[];
  } catch {
    return [];
  }
}

export function enqueue(req: Omit<QueuedRequest, "id" | "createdAt">): QueuedRequest {
  const item: QueuedRequest = {
    ...req,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: Date.now(),
  };
  localStorage.setItem(QUEUE_KEY, JSON.stringify([...getQueue(), item]));
  return item;
}

export function clearQueue(): void {
  localStorage.removeItem(QUEUE_KEY);
}

export function isOnline(): boolean {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}
