// Run: npm test (from the repo root). Drives the MCP server against the committed index.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import zlib from "node:zlib";
import handler, { handleOne, callTool, TOOLS, INSTRUCTIONS } from "../api/mcp.js";
import { loadData, nameScore } from "../lib/marginalia.js";

process.env.MARGINALIA_NO_ANALYTICS = "1";
const d = loadData();
const edgesJson = JSON.parse(fs.readFileSync(new URL("../_data/edges.json", import.meta.url)));
const manifest = JSON.parse(fs.readFileSync(new URL("../_data/manifest.json", import.meta.url)));
const WITHHELD = ["aor", "whitman", "beckett"];
const WITHHELD_NAMES = WITHHELD.map((k) => d.sources[k].name);
const TEXT_KEYS = ["marked_passage", "reader_wrote", "translation", "their_words", "marked_text", "reader_text", "anchor_text"];
const IMAGE = /iiif|\/loris\/|figgy|\.(jpe?g|jp2|png|gif|tiff?|webp)(\?|$)|\/full\/\d|default\.jpg/i;

const rpc = (method, params) => handleOne({ jsonrpc: "2.0", id: 1, method, params }, { test: true });
const walk = (o, fn) => { if (Array.isArray(o)) o.forEach((x) => walk(x, fn)); else if (o && typeof o === "object") { fn(o); Object.values(o).forEach((x) => walk(x, fn)); } };
const urlsIn = (o) => JSON.stringify(o).match(/https?:\/\/[^"\s]+/g) || [];

test("initialize names the server and carries the instructions", async () => {
  const r = await rpc("initialize", { protocolVersion: "2025-06-18" });
  assert.equal(r.result.serverInfo.name, "marginalia-corpus");
  assert.equal(r.result.protocolVersion, "2025-06-18");
  assert.ok(r.result.capabilities.tools);
  assert.match(r.result.instructions, /never add them together/);
});

test("tools/list: six tools, each with a title and every annotation an explicit boolean, all read-only", async () => {
  const r = await rpc("tools/list");
  const tools = r.result.tools;
  assert.deepEqual(tools.map((t) => t.name).sort(), ["about_the_corpus", "authors_read_by_many", "reader_marks", "reader_profile", "search_marginalia", "who_read_author"]);
  for (const t of tools) {
    assert.ok(t.title && t.description && t.inputSchema, t.name);
    for (const k of ["readOnlyHint", "destructiveHint", "openWorldHint", "idempotentHint"]) assert.equal(typeof t.annotations[k], "boolean", `${t.name}.${k}`);
    assert.equal(t.annotations.readOnlyHint, true, t.name);
    assert.equal(t.annotations.destructiveHint, false, t.name);
    assert.ok(t.annotations.title, t.name);
  }
});

test("tool descriptions describe; instructions to the model live only in the server instructions", () => {
  const steer = /\b(you should|you must|make sure|be sure to|remember to|always (say|quote|give|tell|cite|use|call)|do not (say|quote|reconstruct|paraphrase|add)|don't|never (say|tell|ask|add|attribute)|use this tool|call this tool|the model should|quote (counts|them) exactly)\b/i;
  for (const t of TOOLS) {
    assert.doesNotMatch(t.description, steer, t.name);
    for (const [k, p] of Object.entries(t.inputSchema.properties)) assert.doesNotMatch(p.description || "", steer, `${t.name}.${k}`);
  }
  assert.match(INSTRUCTIONS, /Quote counts exactly/);
});

test("reader_marks: Melville in Shakespeare, counts by tier and quotable passages with the required citation", () => {
  const o = callTool("reader_marks", { reader: "Herman Melville", author: "Shakespeare", limit: 30 }).out;
  assert.equal(o.found, true);
  assert.equal(o.author, "William Shakespeare");
  assert.equal(o.counts.own_words, 48);
  assert.equal(o.counts.bare_marks, 713);
  assert.equal(o.volumes_total, 8);
  const edge = edgesJson.edges.find((e) => e.reader_id === "melville" && e.source_author === "William Shakespeare");
  assert.equal(o.counts.own_words, edge.n_T1);
  assert.equal(o.counts.bare_marks, edge.n_T2);
  assert.ok(o.passages.length === 30 && o.passages_matching > 30);
  for (const p of o.passages) {
    assert.equal(p.source, "Melville's Marginalia Online");
    assert.match(p.cite, /Herman Melville, marginalia in William Shakespeare, .+Melville's Marginalia Online\. Steven Olsen-Smith and Peter Norberg, eds\..+Accessed \d{4}-\d\d-\d\d/);
  }
  assert.ok(o.passages.some((p) => p.reader_wrote));
  // marked_passage is Shakespeare's line, never put in Melville's mouth
  const lear = callTool("reader_marks", { reader: "Melville", author: "Shakespeare", contains: "nothing can come of nothing" }).out.passages;
  assert.ok(lear.length >= 1 && lear.every((p) => p.marked_passage && !p.reader_wrote && p.kind === "bare mark"));
  assert.ok(o.attribution.some((a) => a.cite_as.includes("Olsen-Smith")));
});

test("reader_marks: a title, own_words only, and loose names", () => {
  const o = callTool("reader_marks", { reader: "Melvile", title: "sperm whale", kind: "own_words", limit: 5 }).out;
  assert.equal(o.reader, "Herman Melville");
  assert.equal(o.volumes[0].author, "Thomas Beale");
  assert.ok(o.passages.length && o.passages.every((p) => p.kind === "own words"));
  assert.equal(callTool("reader_marks", { reader: "melvile", author: "Shakspeare" }).out.author, "William Shakespeare");
  assert.ok(nameScore("Neitzsche", "Friedrich Nietzsche") >= 0.72);
});

test("who_read_author: Shakespeare, with the evidence sets kept apart", () => {
  const o = callTool("who_read_author", { author: "Shakespeare", limit: 300 }).out;
  assert.equal(o.author, "William Shakespeare");
  const mel = o.marked.readers.find((r) => r.reader === "Herman Melville");
  assert.equal(mel.own_words + mel.bare_marks, 761);
  assert.ok(o.marked.readers.some((r) => r.reader === "Samuel Beckett"));
  assert.ok(o.named_in_their_writing.readers.some((r) => r.reader === "Friedrich Nietzsche"));
  assert.ok(o.held_or_borrowed.total > 0 && o.held_or_borrowed.readers.every((r) => r.attested_copies > 0 && r.own_words === undefined));
  const shared = edgesJson.shared_authors.find((a) => a.author === "William Shakespeare");
  assert.equal(o.distinct_readers, shared.n_readers);
  const noLending = callTool("who_read_author", { author: "Shakespeare", include_lending_library: false }).out;
  assert.ok(noLending.held_or_borrowed.total < o.held_or_borrowed.total);
});

test("reader_profile: Melville matches the manifest, Beckett's two records are one person", () => {
  const o = callTool("reader_profile", { reader: "Melville" }).out;
  assert.equal(o.volumes, manifest.monline.n_volumes);
  assert.equal(o.counts.own_words, manifest.monline.n_autograph);
  assert.equal(o.counts.bare_marks, manifest.monline.n_mark);
  assert.equal(o.top_authors[0].author, "William Shakespeare");
  assert.equal(o.dates.life.birth, 1819);
  const b = callTool("reader_profile", { reader: "Samuel Beckett" }).out;
  assert.equal(b.notes.length, 2);            // his library and his Paris lending card, one reader
  assert.ok(b.notes.some((n) => n.includes("Shakespeare and Company")));
});

test("authors_read_by_many: reproduces the corpus's own 858, and filters by readers", () => {
  const o = callTool("authors_read_by_many", { limit: 5 }).out;
  assert.equal(o.authors_total, edgesJson.n_authors_reached_by_multiple_readers);
  assert.equal(o.authors[0].author, edgesJson.shared_authors[0].author);
  assert.equal(o.authors[0].readers_count, edgesJson.shared_authors[0].n_readers);
  const both = callTool("authors_read_by_many", { readers: ["Melville", "Beckett"], evidence: "marked" }).out;
  assert.ok(both.authors.some((a) => a.author === "William Shakespeare"));
  for (const a of both.authors) for (const name of ["Herman Melville", "Samuel Beckett"]) assert.ok(a.readers.find((r) => r.reader === name).marked, a.author);
});

test("search_marginalia: finds the Lear line Melville marked, and Nietzsche's prose", () => {
  const o = callTool("search_marginalia", { query: "Nothing can come of nothing" }).out;
  assert.ok(o.hits.some((h) => h.reader === "Herman Melville" && /Nothing can come of nothing/.test(h.marked_passage)));
  const n = callTool("search_marginalia", { query: "Wagner", reader: "Nietzsche", limit: 3 }).out;
  assert.ok(n.hits.length === 3 && n.hits.every((h) => h.their_words && h.source.startsWith("Friedrich Nietzsche")));
  assert.equal(callTool("search_marginalia", { query: "xq" }).isError, true);
});

test("about_the_corpus: totals and eight sources with their terms", () => {
  const o = callTool("about_the_corpus").out;
  assert.equal(o.totals.marks, 216552);
  assert.equal(o.totals.readers, 555);
  assert.equal(o.sources.length, 8);
  assert.ok(o.sources.every((s) => s.terms && s.cite_as));
  assert.match(o.page, /src=mcp/);
});

test("not found says so, with the closest names", () => {
  const r = callTool("reader_marks", { reader: "Zzyzx Qwerty" }).out;
  assert.equal(r.found, false);
  assert.match(r.answer, /No reader named "Zzyzx Qwerty"/);
  assert.equal(r.closest_readers.length, 5);
  const a = callTool("who_read_author", { author: "Qqqq Zzzz" }).out;
  assert.equal(a.found, false);
  assert.equal(a.closest_authors.length, 5);
  const m = callTool("reader_marks", { reader: "Melville", author: "Proust" }).out;
  assert.equal(m.found, false);
  assert.match(m.answer, /no marks in, and held or borrowed no copy of, Marcel Proust/);
  assert.equal(callTool("reader_marks", {}).isError, true);
});

// The rule the server exists under: an MCP response is republication.
const WITHHELD_CALLS = [
  ["reader_marks", { reader: "Gabriel Harvey", limit: 30 }], ["reader_marks", { reader: "Gabriel Harvey", author: "Livy", kind: "own_words", limit: 30 }],
  ["reader_marks", { reader: "John Dee", limit: 30 }], ["reader_marks", { reader: "John Winthrop", limit: 30 }],
  ["reader_marks", { reader: "Walt Whitman", limit: 30 }], ["reader_marks", { reader: "Whitman", kind: "own_words", limit: 30 }],
  ["reader_marks", { reader: "Samuel Beckett", limit: 30 }], ["reader_marks", { reader: "Beckett", author: "Dante", kind: "own_words", limit: 30 }],
  ["reader_marks", { reader: "Beckett", author: "Shakespeare", title: "Macbeth" }],
  ["reader_profile", { reader: "Beckett" }], ["reader_profile", { reader: "Harvey" }], ["reader_profile", { reader: "Whitman" }],
  ["who_read_author", { author: "Dante" }], ["who_read_author", { author: "Livy" }],
  ["search_marginalia", { query: "the", reader: "Beckett", limit: 30 }], ["search_marginalia", { query: "the", reader: "Whitman", limit: 30 }],
  ["search_marginalia", { query: "et", reader: "Harvey", limit: 30 }], ["search_marginalia", { query: "Kant", limit: 30 }],
  ["about_the_corpus", {}],
];

test("no text field is ever returned for Archaeology of Reading, Whitman or Beckett", () => {
  for (const [tool, args] of WITHHELD_CALLS) {
    const o = callTool(tool, args).out;
    walk(o, (x) => {
      if (WITHHELD_NAMES.includes(x.source) || /Archaeology of Reading|Whitman Archive|Beckett Digital/.test(x.cite || "")) {
        for (const k of TEXT_KEYS) assert.ok(!x[k], `${tool} ${JSON.stringify(args)} returned ${k} for ${x.source}`);
        assert.ok(!("passages" in x) || x.passages.length === 0);
      }
    });
    for (const p of [...(o.passages || []), ...(o.hits || [])]) assert.ok(!WITHHELD_NAMES.includes(p.source), `${tool} ${JSON.stringify(args)} quoted ${p.source}`);
  }
  const b = callTool("reader_marks", { reader: "Beckett", limit: 30 }).out;
  assert.equal(b.passages.length, 0);
  assert.ok(b.counts.own_words > 2000 && b.text_withheld_for[0].why.includes("2059"));
  const dee = callTool("reader_marks", { reader: "John Dee", limit: 30 }).out;   // ABO text is quotable, AOR's is not
  assert.ok(dee.passages.length > 0 && dee.passages.every((p) => p.source === "Annotated Books Online"));
});

test("the index carries no withheld text, and the answer-time gate holds even if it did", () => {
  const raw = JSON.parse(zlib.gunzipSync(fs.readFileSync(new URL("../mcp/index.json.gz", import.meta.url))).toString("utf8"));
  for (const p of raw.passages) assert.ok(!WITHHELD.includes(raw.volumes[p[0]][1]));
  for (const r of raw.refs) assert.ok(!WITHHELD.includes(r[1]));
  for (const k of WITHHELD) assert.equal(raw.sources[k].emit_text, false);
  // Poison the loaded index with a Beckett passage: the second gate must still refuse it.
  const v = d.volumes.find((x) => x.src === "beckett" && x.n1 > 0);
  const fake = { v: v.i, tier: 1, type: "marginalia", page: "1", marked: "", said: "POISON", trans: "", hand: "Samuel Beckett", own: true, lang: "", url: "", cut: false };
  const had = d.passByVol.has(v.i);
  if (!had) d.passByVol.set(v.i, []);
  d.passages.push(fake); d.passByVol.get(v.i).push(fake);
  try {
    const o = callTool("reader_marks", { reader: "Beckett", title: v.title, limit: 30 }).out;
    assert.doesNotMatch(JSON.stringify(o), /POISON/);
    assert.ok(o.counts.own_words > 0);
  } finally { d.passages.pop(); d.passByVol.get(v.i).pop(); if (!had) d.passByVol.delete(v.i); }
});

test("no image is ever linked", () => {
  const calls = [...WITHHELD_CALLS, ["reader_marks", { reader: "Derrida", limit: 30 }], ["reader_marks", { reader: "Derrida", author: "Rousseau", limit: 30, volumes_limit: 100 }],
    ["who_read_author", { author: "James Joyce", limit: 300 }], ["reader_profile", { reader: "James Joyce" }], ["reader_marks", { reader: "James Joyce", volumes_limit: 100 }],
    ["search_marginalia", { query: "ecriture", limit: 30 }], ["reader_marks", { reader: "Erasmus", limit: 30 }]];
  for (const [tool, args] of calls) for (const u of urlsIn(callTool(tool, args).out)) assert.doesNotMatch(u, IMAGE, `${tool} linked ${u}`);
  const raw = fs.readFileSync(new URL("../mcp/index.json.gz", import.meta.url));
  for (const u of zlib.gunzipSync(raw).toString("utf8").match(/https?:\/\/[^"\s]+/g)) assert.doesNotMatch(u, IMAGE);
});

test("the HTTP handler answers a POST and refuses a GET body", async () => {
  const mk = (method, body) => {
    const res = { headers: {}, statusCode: 200, body: "", setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = b || ""; } };
    return [{ method, headers: { "x-marginalia-test": "1" }, body }, res];
  };
  const [req, res] = mk("POST", { jsonrpc: "2.0", id: 7, method: "tools/call", params: { name: "about_the_corpus", arguments: {} } });
  await handler(req, res);
  const j = JSON.parse(res.body);
  assert.equal(j.id, 7);
  assert.equal(j.result.structuredContent.totals.volumes, 9303);
  const [g, gr] = mk("GET");
  await handler(g, gr);
  assert.equal(gr.statusCode, 405);
});

test("the pages carry the analytics tag, every tool, and the corpus's own totals", () => {
  const read = (p) => fs.readFileSync(new URL("../public/" + p, import.meta.url), "utf8");
  const pages = { home: read("index.html"), connect: read("connect/index.html"), privacy: read("privacy/index.html") };
  for (const [k, h] of Object.entries(pages)) assert.match(h, /\/_vercel\/insights\/script\.js/, k);
  for (const t of TOOLS) { assert.ok(pages.home.includes(t.name), t.name); assert.ok(pages.connect.includes(t.name), t.name); }
  assert.ok(pages.home.includes(d.totals.marks.toLocaleString("en-US")));
  for (const s of Object.values(d.sources)) assert.ok(pages.connect.includes(s.citation.replace(/&/g, "&amp;").replace(/'/g, "'")), s.name);
  assert.match(pages.privacy, /which tool ran, whether it worked, and how long it took/);
  assert.match(fs.readFileSync(new URL("../public/icon-composer.svg", import.meta.url), "utf8"), /stroke="currentColor"/);
});
