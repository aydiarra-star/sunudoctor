import { useEffect, useState } from "react";
import { api, type Meta } from "../lib/api";

/**
 * Fetches public, non-sensitive capability metadata. The UI uses it to be
 * honest about what is real, what is demonstration, and what is not connected.
 */
export function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Meta>("/meta")
      .then(setMeta)
      .catch((e) => setError(e instanceof Error ? e.message : "Backend non connecté"));
  }, []);

  return { meta, error };
}
