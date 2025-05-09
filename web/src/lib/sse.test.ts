import { describe, expect, it } from "vitest";
import { sse } from "./api";

function response(chunks: string[]): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream({
    start(c) { for (const ch of chunks) c.enqueue(enc.encode(ch)); c.close(); },
  });
  return new Response(stream, { status: 200 });
}

describe("sse parser", () => {
  it("parses events split across chunk boundaries", async () => {
    const out = [];
    for await (const e of sse(response(['event: token\ndata: "he', 'llo"\n\nevent: done\ndata: {}\n\n']))) out.push(e);
    expect(out).toEqual([{ event: "token", data: "hello" }, { event: "done", data: {} }]);
  });
  it("throws on http error", async () => {
    await expect(async () => { for await (const _ of sse(new Response("x", { status: 500 }))) void _; }).rejects.toThrow();
  });
});
