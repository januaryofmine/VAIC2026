import { IncomingMessage, ServerResponse } from "node:http";
import { Socket } from "node:net";

import { createEvent, getResponseHeader, type H3Event } from "h3";
import { describe, expect, it } from "vitest";

import { formatServerTiming, setServerTiming } from "./server-timing";

/** A real h3 event backed by a real Node ServerResponse (no live server needed). */
function makeEvent(): H3Event {
  const req = new IncomingMessage(new Socket());
  const res = new ServerResponse(req);
  return createEvent(req, res);
}

describe("formatServerTiming", () => {
  it("formats a single metric without a description", () => {
    expect(formatServerTiming([{ name: "owner", dur: 477.23 }])).toBe("owner;dur=477.2");
  });

  it("includes a quoted description when given", () => {
    expect(formatServerTiming([{ name: "fetch", dur: 523, desc: "HF status" }])).toBe(
      'fetch;dur=523;desc="HF status"',
    );
  });

  it("joins multiple metrics with a comma and space", () => {
    expect(
      formatServerTiming([
        { name: "owner", dur: 477.2 },
        { name: "fetch", dur: 523.1 },
      ]),
    ).toBe("owner;dur=477.2, fetch;dur=523.1");
  });

  it("returns an empty string for no metrics", () => {
    expect(formatServerTiming([])).toBe("");
  });

  it("keeps a zero duration", () => {
    expect(formatServerTiming([{ name: "x", dur: 0 }])).toBe("x;dur=0");
  });

  it("drops metrics with a non-finite duration", () => {
    expect(
      formatServerTiming([
        { name: "bad", dur: Number.NaN },
        { name: "ok", dur: 5 },
      ]),
    ).toBe("ok;dur=5");
  });

  it("sanitizes an unsafe metric name to a token", () => {
    // spaces / delimiters would break the header grammar → replaced with '-'
    expect(formatServerTiming([{ name: "owner check;x", dur: 1 }])).toBe("owner-check-x;dur=1");
  });

  it("escapes quotes/backslashes in the description", () => {
    expect(formatServerTiming([{ name: "n", dur: 1, desc: 'a"b\\c' }])).toBe(
      'n;dur=1;desc="a\\"b\\\\c"',
    );
  });
});

describe("setServerTiming", () => {
  it("sets the Server-Timing header on a real h3 event", () => {
    const event = makeEvent();
    setServerTiming(event, [
      { name: "owner", dur: 12.34 },
      { name: "fetch", dur: 56 },
    ]);
    expect(getResponseHeader(event, "Server-Timing")).toBe("owner;dur=12.3, fetch;dur=56");
  });

  it("is a no-op (no header) when there are no metrics", () => {
    const event = makeEvent();
    setServerTiming(event, []);
    expect(getResponseHeader(event, "Server-Timing")).toBeUndefined();
  });

  it("never throws even if the event is unusable (observability must not break the response)", () => {
    const broken = {} as H3Event; // no node.res → setResponseHeader would throw, but we swallow
    expect(() => setServerTiming(broken, [{ name: "x", dur: 1 }])).not.toThrow();
  });
});
