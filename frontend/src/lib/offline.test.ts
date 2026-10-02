import { describe, expect, it, beforeEach, vi } from "vitest";
import {
  clearQueue,
  enqueue,
  getQueue,
  setOfflinePassphrase,
  syncQueue,
  isEncryptionReady,
} from "./offline";

describe("offline encrypted queue", () => {
  beforeEach(async () => {
    setOfflinePassphrase("test-passphrase");
    localStorage.clear();
    await clearQueue();
  });

  it("refuses to persist without an encryption passphrase", async () => {
    setOfflinePassphrase(null);
    expect(isEncryptionReady()).toBe(false);
    await expect(
      enqueue({ path: "/patients", method: "POST", body: { a: 1 } }),
    ).rejects.toThrow();
    setOfflinePassphrase("test-passphrase");
  });

  it("stores items encrypted (not readable in clear text)", async () => {
    await enqueue({ path: "/patients", method: "POST", body: { secret: "clinical-data" } });
    const raw = localStorage.getItem("sd_sync_queue_v2") ?? "";
    expect(raw).not.toContain("clinical-data");
    const q = await getQueue();
    expect(q).toHaveLength(1);
    expect(q[0].path).toBe("/patients");
    expect(q[0].attempts).toBe(0);
  });

  it("replays the queue and removes confirmed items", async () => {
    await enqueue({ path: "/patients", method: "POST", body: { a: 1 } });
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, status: 201 } as Response);
    const result = await syncQueue("/api", "token", fetchImpl as unknown as typeof fetch);
    expect(result.synced).toBe(1);
    expect(await getQueue()).toHaveLength(0);
    // The idempotency key is sent so a retry is not duplicated server-side.
    const headers = (fetchImpl.mock.calls[0][1] as RequestInit).headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toBeTruthy();
  });

  it("keeps items on network failure for retry", async () => {
    await enqueue({ path: "/patients", method: "POST", body: { a: 1 } });
    const fetchImpl = vi.fn().mockRejectedValue(new Error("offline"));
    const result = await syncQueue("/api", "token", fetchImpl as unknown as typeof fetch);
    expect(result.synced).toBe(0);
    expect(result.failed).toHaveLength(1);
    const q = await getQueue();
    expect(q).toHaveLength(1);
    expect(q[0].attempts).toBe(1);
  });

  it("surfaces conflicts without auto-resolving them", async () => {
    await enqueue({ path: "/patients", method: "POST", body: { a: 1 } });
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 409 } as Response);
    const result = await syncQueue("/api", "token", fetchImpl as unknown as typeof fetch);
    expect(result.conflicts).toHaveLength(1);
    expect(result.synced).toBe(0);
  });
});
