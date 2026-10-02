import { describe, expect, it } from "vitest";
import { getQueue, enqueue, clearQueue } from "./offline";

describe("offline queue", () => {
  it("starts empty and stores requests", () => {
    clearQueue();
    expect(getQueue()).toEqual([]);
    enqueue({ path: "/patients", method: "POST", body: { a: 1 } });
    const q = getQueue();
    expect(q).toHaveLength(1);
    expect(q[0].path).toBe("/patients");
    expect(q[0].id).toBeTruthy();
    clearQueue();
  });
});
