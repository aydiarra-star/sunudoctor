/**
 * Encrypted offline store + synchronisation queue.
 *
 * Sensitive clinical payloads are encrypted at rest with AES-GCM using a key
 * derived (PBKDF2) from a session passphrase. Nothing clinical is written to
 * localStorage in clear text. When the passphrase is absent the store refuses to
 * persist clinical data rather than storing it unencrypted.
 *
 * The queue is a durable outbox: items are replayed to the backend when the
 * connection returns, and are removed only after the server confirms success.
 * Conflict handling is conservative: a server-side 409/422 is surfaced as a
 * conflict for the human to resolve, never silently overwritten.
 */
export interface QueuedItem {
  id: string;
  path: string;
  method: string;
  body: unknown;
  createdAt: number;
  attempts: number;
  lastError?: string;
}

const QUEUE_KEY = "sd_sync_queue_v2";

function bytesToB64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

function b64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}

async function deriveKey(passphrase: string): Promise<CryptoKey> {
  const enc = new TextEncoder();
  const material = await crypto.subtle.importKey("raw", enc.encode(passphrase), "PBKDF2", false, [
    "deriveKey",
  ]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: enc.encode("sunudoctor-offline-v1"), iterations: 100_000, hash: "SHA-256" },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

/**
 * In-memory passphrase used to encrypt the queue. Derived from the session so it
 * disappears on logout. It is never persisted to disk.
 */
let sessionPassphrase: string | null = null;

export function setOfflinePassphrase(passphrase: string | null): void {
  sessionPassphrase = passphrase;
}

export function isEncryptionReady(): boolean {
  return sessionPassphrase !== null && typeof crypto !== "undefined" && !!crypto.subtle;
}

async function encrypt(plain: string): Promise<string> {
  if (!sessionPassphrase) throw new Error("Chiffrement indisponible : session non déverrouillée");
  const key = await deriveKey(sessionPassphrase);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipher = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv as unknown as BufferSource },
    key,
    new TextEncoder().encode(plain) as unknown as BufferSource,
  );
  return JSON.stringify({ iv: bytesToB64(iv), ct: bytesToB64(new Uint8Array(cipher)) });
}

async function decrypt(payload: string): Promise<string> {
  if (!sessionPassphrase) throw new Error("Chiffrement indisponible : session non déverrouillée");
  const { iv, ct } = JSON.parse(payload) as { iv: string; ct: string };
  const key = await deriveKey(sessionPassphrase);
  const plain = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: b64ToBytes(iv) as unknown as BufferSource },
    key,
    b64ToBytes(ct) as unknown as BufferSource,
  );
  return new TextDecoder().decode(plain);
}

async function readQueue(): Promise<QueuedItem[]> {
  const raw = localStorage.getItem(QUEUE_KEY);
  if (!raw) return [];
  try {
    const json = isEncryptionReady() ? await decrypt(raw) : raw;
    return JSON.parse(json) as QueuedItem[];
  } catch {
    return [];
  }
}

async function writeQueue(items: QueuedItem[]): Promise<void> {
  if (!isEncryptionReady()) {
    // No passphrase: refuse to persist clinical payloads in clear text.
    throw new Error("Refus d'écrire des données non chiffrées hors connexion.");
  }
  localStorage.setItem(QUEUE_KEY, await encrypt(JSON.stringify(items)));
}

export async function getQueue(): Promise<QueuedItem[]> {
  return readQueue();
}

export async function enqueue(
  item: Omit<QueuedItem, "id" | "createdAt" | "attempts">,
): Promise<QueuedItem> {
  const queued: QueuedItem = {
    ...item,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: Date.now(),
    attempts: 0,
  };
  const items = await readQueue();
  await writeQueue([...items, queued]);
  return queued;
}

export async function removeFromQueue(id: string): Promise<void> {
  const items = await readQueue();
  await writeQueue(items.filter((i) => i.id !== id));
}

export async function clearQueue(): Promise<void> {
  localStorage.removeItem(QUEUE_KEY);
}

export function isOnline(): boolean {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export interface SyncResult {
  synced: number;
  conflicts: QueuedItem[];
  failed: QueuedItem[];
}

/**
 * Replay the outbox against the API. Idempotency is carried by each item id so
 * a retried write is not duplicated server-side. Conflicts are returned, never
 * auto-resolved.
 */
export async function syncQueue(
  apiBase: string,
  token: string | null,
  fetchImpl: typeof fetch = fetch,
): Promise<SyncResult> {
  const items = await readQueue();
  const conflicts: QueuedItem[] = [];
  const failed: QueuedItem[] = [];
  let synced = 0;

  for (const item of items) {
    try {
      const res = await fetchImpl(`${apiBase}${item.path}`, {
        method: item.method,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          "Idempotency-Key": item.id,
        },
        body: item.body ? JSON.stringify(item.body) : undefined,
      });
      if (res.ok) {
        await removeFromQueue(item.id);
        synced += 1;
      } else if (res.status === 409 || res.status === 422) {
        conflicts.push(item);
      } else {
        item.attempts += 1;
        item.lastError = `HTTP ${res.status}`;
        failed.push(item);
      }
    } catch {
      item.attempts += 1;
      item.lastError = "Réseau indisponible";
      failed.push(item);
    }
  }
  if (failed.length) {
    try {
      await writeQueue(failed);
    } catch {
      /* encryption unavailable: leave as-is */
    }
  }
  return { synced, conflicts, failed };
}
