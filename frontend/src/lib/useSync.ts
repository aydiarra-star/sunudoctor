import { useCallback, useEffect, useState } from "react";
import { getQueue, syncQueue, type QueuedItem } from "./offline";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

export interface SyncState {
  pending: number;
  lastResult: { synced: number; conflicts: QueuedItem[]; failed: QueuedItem[] } | null;
  syncing: boolean;
  sync: () => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Drives the offline outbox. It only ever reports what really happened:
 * - pending counts come from the encrypted store,
 * - a sync attempt is triggered by regaining connectivity or manually,
 * - conflicts are surfaced, never silently resolved.
 */
export function useSync(enabled: boolean): SyncState {
  const [pending, setPending] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [lastResult, setLastResult] = useState<SyncState["lastResult"]>(null);

  const refresh = useCallback(async () => {
    try {
      setPending((await getQueue()).length);
    } catch {
      setPending(0);
    }
  }, []);

  const sync = useCallback(async () => {
    if (!enabled) return;
    setSyncing(true);
    try {
      const token = localStorage.getItem("sd_token");
      const result = await syncQueue(API_BASE, token);
      setLastResult(result);
      await refresh();
    } finally {
      setSyncing(false);
    }
  }, [enabled, refresh]);

  useEffect(() => {
    refresh();
    const onOnline = () => {
      sync();
    };
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, [refresh, sync]);

  return { pending, lastResult, syncing, sync, refresh };
}
