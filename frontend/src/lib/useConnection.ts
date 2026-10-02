import { useEffect, useState } from "react";
import type { Connection } from "../components/ui";

/**
 * Connection state derived from the browser plus a periodic API probe.
 *
 * - "offline": the browser reports no network, or the API is unreachable.
 * - "limited": the API answered with a server/rate-limit error (degraded).
 * - "online": the API health endpoint answered 200.
 *
 * This drives an honest indicator; it never claims a sync happened.
 */
export function useConnection(apiBase?: string): Connection {
  const [status, setStatus] = useState<Connection>(
    typeof navigator === "undefined" || navigator.onLine ? "online" : "offline",
  );

  useEffect(() => {
    const base = apiBase ?? (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";
    let cancelled = false;

    async function probe() {
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        if (!cancelled) setStatus("offline");
        return;
      }
      try {
        const res = await fetch(`${base}/health`, { method: "GET" });
        if (!cancelled) setStatus(res.ok ? "online" : "limited");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    probe();
    const onOnline = () => probe();
    const onOffline = () => setStatus("offline");
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    const interval = setInterval(probe, 30000);

    return () => {
      cancelled = true;
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      clearInterval(interval);
    };
  }, [apiBase]);

  return status;
}
