// The Marginalia Corpus as tool answers. Every number comes out of mcp/index.json.gz,
// which mcp/build_index.py writes from _data/ with the rights gate applied at build time:
// passage and reference text exists in the index only for sources whose rights.py entry
// sets emit_text. This file adds a second gate at answer time (quotable()), and never
// emits an image URL (the index carries none; safeLink() refuses one anyway).
//
// Tiers are different kinds of evidence and are never added together:
//   own_words   T1, the reader's own words in the margin
//   bare_marks  T2, a score, underline, bracket or checkmark, no words
//   attested    T3, the reader demonstrably held or borrowed the copy; no surviving mark
// "marks" below means T1 + T2 (both locate a passage), as the README uses it. T3 is never
// called a mark.
import fs from "node:fs";
import zlib from "node:zlib";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const SITE = "https://marginalia-corpus.vercel.app";
export const REPO = "https://github.com/2016judea/marginalia-corpus";
const LENDING = "shakeco";
const fmt = (n) => Number(n).toLocaleString("en-US");
const MAX_LIMIT = 30;
const IMAGE_URL = /iiif|\/loris\/|figgy|\.(jpe?g|jp2|png|gif|tiff?|webp)(\?|$)|\/full\/\d|default\.jpg/i;

export const tag = (url) => {
  url = String(url);
  if (!url.startsWith(SITE) || /[?&]src=/.test(url)) return url;
  return url + (url.includes("?") ? "&" : "?") + "src=mcp";
};
const safeLink = (u) => (u && !IMAGE_URL.test(u) ? u : undefined);

// ---------- names ----------

export const norm = (s) => String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

function osa(a, b) {   // edit distance counting a transposition as one edit ("Neitzsche")
  const m = a.length, n = b.length, d = Array.from({ length: m + 1 }, (_, i) => [i, ...Array(n).fill(0)]);
  for (let j = 1; j <= n; j++) d[0][j] = j;
  for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) {
    const c = a[i - 1] === b[j - 1] ? 0 : 1;
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
    if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
  }
  return d[m][n];
}
const ratio = (a, b) => 1 - osa(a, b) / Math.max(a.length, b.length, 1);

export function nameScore(query, name) {
  const q = norm(query), n = norm(name);
  if (!q || !n) return 0;
  if (q === n) return 1;
  const qt = q.split(" "), nt = n.split(" ");
  if (qt.every((t) => nt.includes(t))) return 0.95 - 0.01 * Math.min(5, nt.length - qt.length);
  if (qt.every((t) => t.length >= 3 && nt.some((x) => x.startsWith(t)))) return 0.88;
  const per = qt.map((t) => Math.max(...nt.map((x) => ratio(t, x))));
  return 0.85 * Math.max(per.reduce((a, b) => a + b, 0) / per.length, ratio(q, n));
}
const ACCEPT = 0.72;

// candidates: [{name, weight}] -> {hit, also, closest}
function resolve(query, candidates) {
  const scored = candidates.map((c) => ({ c, s: nameScore(query, c.name) })).sort((a, b) => b.s - a.s || b.c.weight - a.c.weight);
  const ok = scored.filter((x) => x.s >= ACCEPT);
  if (!ok.length) return { hit: null, closest: scored.slice(0, 5).map((x) => x.c.name) };
  const top = ok[0].s;
  const tied = ok.filter((x) => top - x.s < 0.005).sort((a, b) => b.c.weight - a.c.weight);
  const rest = ok.filter((x) => !tied.includes(x));
  return { hit: tied[0].c, also: [...tied.slice(1), ...rest].slice(0, 5).map((x) => x.c.name) };
}

// ---------- data ----------

let D;
export function loadData() {
  if (D) return D;
  const here = path.dirname(fileURLToPath(import.meta.url));
  const file = [path.join(here, "..", "mcp", "index.json.gz"), path.join(process.cwd(), "mcp", "index.json.gz")].find((p) => fs.existsSync(p));
  const raw = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)).toString("utf8"));
  const readers = raw.readers.map(([id, name, birth, death, note], i) => ({ i, id, name, birth, death, note }));
  const volumes = raw.volumes.map((v, i) => ({ i, r: v[0], src: v[1], author: v[2], title: v[3], date: v[4], repo: v[5], shelf: v[6], url: v[7], from: v[8], to: v[9], evidence: v[10],
    n1: v[11], n2: v[12], n3: v[13], o1: v[14], o2: v[15], o3: v[16], withheld: v[17], types: v[18] }));
  const passages = raw.passages.map((p) => ({ v: p[0], tier: p[1], type: p[2], page: p[3], marked: p[4], said: p[5], trans: p[6], hand: p[7], own: !!p[8], lang: p[9], url: p[10], cut: !!p[11] }));
  const refs = raw.refs.map((r) => ({ r: r[0], src: r[1], kind: r[2], work: r[3], vol: r[4], target: r[5], author: r[6], text: r[7], page: r[8], url: r[9], cut: !!r[10] }));
  const edges = raw.edges.map((e) => ({ r: e[0], author: e[1], nvol: e[2], n1: e[3], n2: e[4], n3: e[5], own: e[6], anchored: !!e[7], datasets: e[8] }));
  const refEdges = raw.ref_edges.map((e) => ({ r: e[0], author: e[1], n: e[2], kinds: e[3], works: e[4], inWorks: e[5], datasets: e[6] }));
  const personEdges = raw.person_edges.map((e) => ({ r: e[0], person: e[1], n: e[2], nvol: e[3], datasets: e[4] }));

  const group = (rows, key) => { const m = new Map(); for (const x of rows) { const k = key(x); if (!m.has(k)) m.set(k, []); m.get(k).push(x); } return m; };
  const volsByReader = group(volumes, (v) => v.r), passByVol = group(passages, (p) => p.v);
  const refsByReader = group(refs, (x) => x.r);
  const edgesByReader = group(edges, (e) => e.r), edgesByAuthor = group(edges, (e) => e.author);
  const refEdgesByReader = group(refEdges, (e) => e.r), refEdgesByAuthor = group(refEdges, (e) => e.author);
  const personByReader = group(personEdges, (e) => e.r), personByName = group(personEdges, (e) => norm(e.person));

  // One person can hold several reader ids (Samuel Beckett: his own library, and a Paris lending card).
  const persons = new Map();
  for (const r of readers) {
    const k = norm(r.name);
    if (!persons.has(k)) persons.set(k, { name: r.name, ids: [], weight: 0 });
    const p = persons.get(k);
    p.ids.push(r.i);
    for (const v of volsByReader.get(r.i) || []) p.weight += v.n1 + v.n2 + v.n3;
    p.weight += (refsByReader.get(r.i) || []).length + (refEdgesByReader.get(r.i) || []).reduce((a, e) => a + e.n, 0);
  }
  const personOf = (ri) => persons.get(norm(readers[ri].name));

  const authors = new Map();   // canonical name -> weight (distinct readers)
  const bump = (name, r) => { if (!name) return; if (!authors.has(name)) authors.set(name, new Set()); authors.get(name).add(r); };
  for (const e of edges) bump(e.author, e.r);
  for (const e of refEdges) bump(e.author, e.r);
  for (const e of personEdges) bump(e.person, e.r);
  const authorCands = [...authors].map(([name, s]) => ({ name, weight: s.size }));

  D = { raw, sources: raw.sources, totals: raw.totals, notes: raw.notes, dataBuilt: raw.data_built, readers, volumes, passages, refs, edges, refEdges, personEdges,
    volsByReader, passByVol, refsByReader, edgesByReader, edgesByAuthor, refEdgesByReader, refEdgesByAuthor, personByReader, personByName,
    persons, personOf, personCands: [...persons.values()], authorCands };
  return D;
}

// Second gate: never trust the index alone. Text leaves only for an emit_text source.
export const quotable = (d, src) => !!(d.sources[src] && d.sources[src].emit_text);

const yearOf = (s) => { const m = String(s || "").match(/\b(1[2-9]\d\d|20[0-2]\d)\b/); return m ? +m[1] : null; };
const span = (ys) => { ys = ys.filter(Boolean); return ys.length ? { earliest: Math.min(...ys), latest: Math.max(...ys) } : null; };
const isLending = (d, ri) => d.readers[ri].id.startsWith(LENDING + ":");
const lim = (n, dflt) => Math.max(1, Math.min(MAX_LIMIT, Number.isFinite(+n) && +n > 0 ? Math.floor(+n) : dflt));
const limBig = (n, dflt, max) => Math.max(1, Math.min(max, Number.isFinite(+n) && +n > 0 ? Math.floor(+n) : dflt));

function attribution(d, srcs) {
  return [...new Set(srcs)].sort().map((k) => {
    const s = d.sources[k];
    return { source: s.name, site: s.url, cite_as: s.citation, text: s.emit_text ? "quotable with attribution" : "withheld: counts, metadata and links only", terms: s.terms };
  });
}

const tierCounts = (vols) => {
  const c = { own_words: 0, bare_marks: 0, attested_copies: 0, in_readers_own_hand: { own_words: 0, bare_marks: 0, attested_copies: 0 }, own_words_text_withheld: 0 };
  for (const v of vols) {
    c.own_words += v.n1; c.bare_marks += v.n2; c.attested_copies += v.n3;
    c.in_readers_own_hand.own_words += v.o1; c.in_readers_own_hand.bare_marks += v.o2; c.in_readers_own_hand.attested_copies += v.o3;
    c.own_words_text_withheld += v.withheld;
  }
  return c;
};

function volumeOut(d, v) {
  const s = d.sources[v.src];
  return {
    title: v.title, author: v.author, edition: v.date || undefined, held_at: v.repo || undefined, shelfmark: v.shelf || undefined,
    own_words: v.n1, bare_marks: v.n2, attested_copies: v.n3 || undefined,
    in_readers_own_hand: v.n1 + v.n2 + v.n3 ? { own_words: v.n1 ? v.o1 : undefined, bare_marks: v.n2 ? v.o2 : undefined, attested_copies: v.n3 ? v.o3 : undefined } : undefined,
    mark_types: v.types ? Object.fromEntries(v.types.split("|").map((t) => { const i = t.lastIndexOf(":"); return [t.slice(0, i), +t.slice(i + 1)]; })) : undefined,
    read: v.from || v.to ? (v.from === v.to || !v.to ? v.from : `${v.from} to ${v.to}`) : undefined,
    attested_by: v.n3 && v.evidence ? v.evidence : undefined,
    source: s.name, link: safeLink(v.url),
  };
}

function passageOut(d, p) {
  const v = d.volumes[p.v], who = d.readers[v.r].name;
  if (!quotable(d, v.src)) return null;
  return {
    reader: who, source: d.sources[v.src].name, book: v.title, author: v.author, page: p.page || undefined,
    kind: p.tier === 1 ? "own words" : "bare mark", mark_type: p.type,
    marked_passage: p.marked || undefined,              // the AUTHOR's printed words the mark sits on
    reader_wrote: p.said || undefined,                   // the READER's own words (T1 only)
    translation: p.trans || undefined,
    hand: p.hand || undefined, hand_is_reader: p.own,
    truncated: p.cut || undefined,
    link: safeLink(p.url),
    cite: `${who}, marginalia in ${v.author}, ${v.title}. ${d.sources[v.src].citation}`,
  };
}

function refOut(d, x) {
  if (!quotable(d, x.src)) return null;
  const who = d.readers[x.r].name, s = d.sources[x.src];
  return {
    reader: who, source: s.name, kind: x.kind, in_their_work: x.work || undefined, names: x.target, author_named: x.author || undefined,
    their_words: x.text || undefined, page: x.page || undefined, truncated: x.cut || undefined,
    in_annotated_copy: x.vol >= 0 ? d.volumes[x.vol].title : undefined,
    link: safeLink(x.url), cite: `${who}${x.work ? ", " + x.work : ""}. ${s.citation}`,
  };
}

function findPerson(d, q) {
  const r = resolve(q, d.personCands);
  return r.hit ? { person: r.hit, also: r.also } : { person: null, closest: r.closest };
}

function notFoundReader(d, q, closest) {
  return { out: { found: false, answer: `No reader named "${q}" in the Marginalia Corpus (${d.totals.readers} readers). Closest names: ${closest.join("; ")}.`, closest_readers: closest }, log: { found: false } };
}

// ---------- tools ----------

export function readerMarks(args = {}) {
  const d = loadData();
  const q = String(args.reader || "").trim();
  if (!q) return { out: { ok: false, error: "Pass the reader's name as reader, e.g. 'Herman Melville'." }, isError: true };
  const f = findPerson(d, q);
  if (!f.person) return notFoundReader(d, q, f.closest);
  const P = f.person;
  let vols = P.ids.flatMap((ri) => d.volsByReader.get(ri) || []);
  let authorMatched;
  if (args.author) {
    const own = [...new Set(vols.map((v) => v.author))].map((name) => ({ name, weight: vols.filter((v) => v.author === name).reduce((a, v) => a + v.n1 + v.n2 + v.n3, 0) }));
    const r = resolve(args.author, own);
    if (!r.hit) {
      const g = resolve(args.author, d.authorCands);
      const top = own.sort((a, b) => b.weight - a.weight).slice(0, 8).map((x) => x.name);
      const msg = g.hit
        ? `${P.name} left no marks in, and held or borrowed no copy of, ${g.hit.name} in this corpus. ${g.hit.weight} reader${g.hit.weight === 1 ? "" : "s"} did: who_read_author has them.`
        : `No author like "${args.author}" anywhere in the corpus.`;
      return { out: { found: false, reader: P.name, answer: msg, closest_authors_in_this_readers_books: resolve(args.author, own).closest, this_readers_most_marked_authors: top }, log: { found: false } };
    }
    authorMatched = r.hit.name;
    vols = vols.filter((v) => v.author === authorMatched);
  }
  if (args.title) {
    const t = norm(args.title);
    const hit = vols.filter((v) => norm(v.title).includes(t) || nameScore(args.title, v.title) >= ACCEPT);
    if (!hit.length) {
      const closest = resolve(args.title, vols.map((v) => ({ name: v.title, weight: v.n1 + v.n2 + v.n3 }))).closest;
      return { out: { found: false, reader: P.name, answer: `No volume titled like "${args.title}" among ${P.name}'s ${vols.length} volumes${authorMatched ? " of " + authorMatched : ""}.`, closest_titles: closest }, log: { found: false } };
    }
    vols = hit;
  }
  if (!vols.length) return { out: { found: false, reader: P.name, answer: `${P.name} is in the corpus through references only (naming authors in their own work), with no annotated volumes. reader_profile and who_read_author show those.` }, log: { found: false } };

  const counts = tierCounts(vols);
  const srcs = [...new Set(vols.map((v) => v.src))];
  const volIdx = new Map(vols.map((v, k) => [v.i, k]));
  const kind = args.kind || "all";
  const needle = args.contains ? norm(args.contains) : "";
  let ps = vols.filter((v) => quotable(d, v.src)).flatMap((v) => d.passByVol.get(v.i) || []);
  if (kind === "own_words") ps = ps.filter((p) => p.tier === 1);
  if (kind === "bare_marks") ps = ps.filter((p) => p.tier === 2);
  if (args.own_hand_only) ps = ps.filter((p) => p.own);
  if (needle) ps = ps.filter((p) => norm(p.marked + " " + p.said + " " + p.trans).includes(needle));
  ps.sort((a, b) => a.tier - b.tier || (b.own - a.own) || volIdx.get(a.v) - volIdx.get(b.v) || String(a.page).localeCompare(String(b.page), "en", { numeric: true }));
  const n = lim(args.limit, 10);

  const withheld = srcs.filter((s) => !quotable(d, s)).map((s) => {
    const vv = vols.filter((v) => v.src === s);
    return { source: d.sources[s].name, own_words: vv.reduce((a, v) => a + v.n1, 0), bare_marks: vv.reduce((a, v) => a + v.n2, 0), why: d.sources[s].terms };
  });
  const marks = counts.own_words + counts.bare_marks;
  const sortedVols = [...vols].sort((a, b) => b.n1 + b.n2 - (a.n1 + a.n2) || b.n3 - a.n3);
  const nv = limBig(args.volumes_limit, 15, 100);
  const parts = [`${fmt(counts.own_words)} in their own words`, `${fmt(counts.bare_marks)} bare marks`];
  const answer = `${P.name}${authorMatched ? " in " + authorMatched : ""}: ${fmt(marks)} marks across ${vols.length} volume${vols.length === 1 ? "" : "s"} (${parts.join(", ")}; ${fmt(counts.in_readers_own_hand.own_words + counts.in_readers_own_hand.bare_marks)} certainly in ${P.name}'s own hand)` +
    (counts.attested_copies ? `, plus ${fmt(counts.attested_copies)} attested cop${counts.attested_copies === 1 ? "y" : "ies"} or borrows with no surviving mark` : "") + "." +
    (withheld.length ? ` Text withheld by the source's terms for ${withheld.map((w) => w.source).join(" and ")}.` : "");
  return {
    out: {
      found: true, reader: P.name, author: authorMatched, also_matched_readers: f.also && f.also.length ? f.also : undefined,
      answer, counts,
      volumes: sortedVols.slice(0, nv).map((v) => volumeOut(d, v)), volumes_total: vols.length,
      passages: ps.slice(0, n).map((p) => passageOut(d, p)).filter(Boolean), passages_matching: ps.length,
      text_withheld_for: withheld.length ? withheld : undefined,
      attribution: attribution(d, srcs),
    },
    log: { found: true },
  };
}

export function whoReadAuthor(args = {}) {
  const d = loadData();
  const q = String(args.author || "").trim();
  if (!q) return { out: { ok: false, error: "Pass the author's name as author, e.g. 'Shakespeare'." }, isError: true };
  const r = resolve(q, d.authorCands);
  if (!r.hit) return { out: { found: false, answer: `No author like "${q}" in the corpus. Closest names: ${r.closest.join("; ")}.`, closest_authors: r.closest }, log: { found: false } };
  const A = r.hit.name;
  const lendingOk = args.include_lending_library !== false;
  const n = limBig(args.limit, 25, 300);
  const keep = (ri) => lendingOk || !isLending(d, ri);
  const E = (d.edgesByAuthor.get(A) || []).filter((e) => keep(e.r));
  const marked = E.filter((e) => e.n1 + e.n2 > 0).sort((a, b) => b.n1 + b.n2 - (a.n1 + a.n2));
  const held = E.filter((e) => e.n1 + e.n2 === 0 && e.n3 > 0).sort((a, b) => b.n3 - a.n3 || d.readers[a.r].name.localeCompare(d.readers[b.r].name));
  const named = (d.refEdgesByAuthor.get(A) || []).filter((e) => keep(e.r)).sort((a, b) => b.n - a.n);
  const persons = (d.personByName.get(norm(A)) || []).filter((e) => keep(e.r)).sort((a, b) => b.n - a.n);
  const srcOf = (ri, ds) => ds.map((k) => (d.sources[k] ? d.sources[k].name : k));
  const readersHere = new Set([...E, ...named].map((e) => norm(d.readers[e.r].name)));
  const allSrcs = [...E, ...named, ...persons].flatMap((e) => e.datasets).filter((k) => d.sources[k]);
  const lifeOf = (ri) => { const x = d.readers[ri]; return x.birth || x.death ? `${x.birth || "?"}–${x.death || "?"}` : undefined; };
  return {
    out: {
      found: true, author: A, also_matched: r.also && r.also.length ? r.also : undefined,
      answer: `${A}: ${readersHere.size} reader${readersHere.size === 1 ? "" : "s"} documented${lendingOk ? "" : " (lending-library members left out)"}. ${marked.length} left marks in a copy, ${held.length} held or borrowed a copy with no surviving mark, ${named.length} named ${A} in their own writing or notes${persons.length ? `, ${persons.length} mention ${A} as a person inside a marginal note` : ""}. These are different kinds of evidence and are kept apart.`,
      distinct_readers: readersHere.size,
      marked: { total: marked.length, readers: marked.slice(0, n).map((e) => ({ reader: d.readers[e.r].name, life: lifeOf(e.r), own_words: e.n1, bare_marks: e.n2, attested_copies: e.n3 || undefined, in_readers_own_hand: e.own, volumes: e.nvol, sources: srcOf(e.r, e.datasets) })) },
      held_or_borrowed: { total: held.length, readers: held.slice(0, n).map((e) => {
        const vv = (d.volsByReader.get(e.r) || []).filter((v) => v.author === A);
        const ys = span(vv.flatMap((v) => [yearOf(v.from), yearOf(v.to)]));
        return { reader: d.readers[e.r].name, life: lifeOf(e.r), attested_copies: e.n3, titles: [...new Set(vv.map((v) => v.title))].slice(0, 5), when: ys ? (ys.earliest === ys.latest ? `${ys.earliest}` : `${ys.earliest}–${ys.latest}`) : undefined, sources: srcOf(e.r, e.datasets) };
      }) },
      named_in_their_writing: { total: named.length, readers: named.slice(0, n).map((e) => ({ reader: d.readers[e.r].name, references: e.n, kinds: e.kinds, works_named: e.works.length ? e.works : undefined, in_their_works: e.inWorks.length ? e.inWorks : undefined, sources: srcOf(e.r, e.datasets) })) },
      named_as_a_person_in_a_note: persons.length ? { total: persons.length, readers: persons.slice(0, n).map((e) => ({ reader: d.readers[e.r].name, mentions: e.n, volumes: e.nvol, sources: srcOf(e.r, e.datasets) })) } : undefined,
      lending_library_note: lendingOk && E.some((e) => isLending(d, e.r)) ? "Shakespeare and Company (Paris, 1919-1941) lending-card borrows are attested contact with a copy, dated to the day, not proof of reading and never a passage. include_lending_library=false leaves them out." : undefined,
      attribution: attribution(d, allSrcs),
    },
    log: { found: true },
  };
}

export function readerProfile(args = {}) {
  const d = loadData();
  const q = String(args.reader || "").trim();
  if (!q) return { out: { ok: false, error: "Pass the reader's name as reader." }, isError: true };
  const f = findPerson(d, q);
  if (!f.person) return notFoundReader(d, q, f.closest);
  const P = f.person, ids = P.ids, R = ids.map((i) => d.readers[i]);
  const vols = ids.flatMap((ri) => d.volsByReader.get(ri) || []);
  const top = limBig(args.top, 12, 50);
  const byAuthor = new Map();
  for (const e of ids.flatMap((ri) => d.edgesByReader.get(ri) || [])) {
    const a = byAuthor.get(e.author) || { author: e.author, own_words: 0, bare_marks: 0, attested_copies: 0, in_readers_own_hand: 0, volumes: 0 };
    a.own_words += e.n1; a.bare_marks += e.n2; a.attested_copies += e.n3; a.in_readers_own_hand += e.own; a.volumes += e.nvol;
    byAuthor.set(e.author, a);
  }
  const authors = [...byAuthor.values()].sort((a, b) => b.own_words + b.bare_marks - (a.own_words + a.bare_marks) || b.attested_copies - a.attested_copies);
  const named = ids.flatMap((ri) => d.refEdgesByReader.get(ri) || []).sort((a, b) => b.n - a.n);
  const persons = ids.flatMap((ri) => d.personByReader.get(ri) || []).sort((a, b) => b.n - a.n);
  const srcs = [...new Set([...vols.map((v) => v.src), ...named.flatMap((e) => e.datasets), ...ids.flatMap((ri) => (d.refsByReader.get(ri) || []).map((x) => x.src))])].filter((k) => d.sources[k]);
  const bySource = srcs.map((s) => {
    const vv = vols.filter((v) => v.src === s);
    return { source: d.sources[s].name, volumes: vv.length, ...(vv.length ? tierCounts(vv) : {}), references: ids.reduce((a, ri) => a + (d.refsByReader.get(ri) || []).filter((x) => x.src === s).length, 0) || undefined, text: quotable(d, s) ? "quotable" : "withheld by the source's terms" };
  });
  const c = tierCounts(vols);
  const editions = span(vols.map((v) => yearOf(v.date)));
  const reading = span(vols.flatMap((v) => [yearOf(v.from), yearOf(v.to)]));
  const life = R.find((x) => x.birth || x.death);
  const marks = c.own_words + c.bare_marks;
  return {
    out: {
      found: true, reader: P.name, also_matched_readers: f.also && f.also.length ? f.also : undefined,
      life: life ? `${life.birth || "?"}–${life.death || "?"}` : undefined,
      notes: [...new Set(R.map((x) => x.note).filter(Boolean))],
      answer: `${P.name}: ${fmt(vols.length)} volume${vols.length === 1 ? "" : "s"}, ${fmt(marks)} marks (${fmt(c.own_words)} in their own words, ${fmt(c.bare_marks)} bare marks)` + (c.attested_copies ? `, ${fmt(c.attested_copies)} attested copies or borrows` : "") + (named.length ? `, names ${named.length} authors in their own writing or notes` : "") + (authors.length ? `. ${marks ? "Most marked" : "Most held or borrowed"}: ${authors.slice(0, 3).map((a) => a.author).join(", ")}.` : "."),
      volumes: vols.length, volumes_with_marks: vols.filter((v) => v.n1 + v.n2 > 0).length, counts: c,
      dates: { life: life ? { birth: life.birth, death: life.death } : undefined, editions_held: editions || undefined, reading_attested: reading || undefined },
      by_source: bySource,
      top_authors: authors.slice(0, top), authors_total: authors.length,
      authors_named_in_their_writing: named.length ? named.slice(0, top).map((e) => ({ author: e.author, references: e.n, kinds: e.kinds, in_their_works: e.inWorks.length ? e.inWorks : undefined })) : undefined,
      people_named_in_notes: persons.length ? persons.slice(0, top).map((e) => ({ person: e.person, mentions: e.n })) : undefined,
      attribution: attribution(d, srcs),
    },
    log: { found: true },
  };
}

// author -> person name -> {marked:{own_words,bare_marks}, attested, named}
function sharedTable(d, lendingOk) {
  const T = new Map();
  const cell = (a, ri) => { if (!T.has(a)) T.set(a, new Map()); const m = T.get(a), k = d.personOf(ri).name; if (!m.has(k)) m.set(k, { own_words: 0, bare_marks: 0, attested: 0, named: 0 }); return m.get(k); };
  for (const e of d.edges) { if (!lendingOk && isLending(d, e.r)) continue; const c = cell(e.author, e.r); c.own_words += e.n1; c.bare_marks += e.n2; c.attested += e.n3; }
  for (const e of d.refEdges) { if (!lendingOk && isLending(d, e.r)) continue; cell(e.author, e.r).named += e.n; }
  return T;
}

const qualifies = (c, ev) => (ev === "marked" ? c.own_words + c.bare_marks > 0 : ev === "held_or_borrowed" ? c.attested > 0 : ev === "named" ? c.named > 0 : c.own_words + c.bare_marks + c.attested + c.named > 0);

export function authorsReadByMany(args = {}) {
  const d = loadData();
  const ev = ["any", "marked", "held_or_borrowed", "named"].includes(args.evidence) ? args.evidence : "any";
  const lendingOk = !args.exclude_lending_library;
  const minR = Math.max(2, Math.min(100, Math.floor(+args.min_readers || 2)));
  const n = limBig(args.limit, 20, 200);
  const want = [];
  for (const name of Array.isArray(args.readers) ? args.readers.slice(0, 6) : args.readers ? [args.readers] : []) {
    const f = findPerson(d, String(name));
    if (!f.person) return notFoundReader(d, String(name), f.closest);
    want.push(f.person.name);
  }
  const T = sharedTable(d, lendingOk);
  const rows = [];
  for (const [author, m] of T) {
    const qual = [...m].filter(([, c]) => qualifies(c, ev));
    if (qual.length < minR) continue;
    if (want.some((w) => !qual.some(([k]) => k === w))) continue;
    rows.push({ author, qual });
  }
  rows.sort((a, b) => b.qual.length - a.qual.length || a.author.localeCompare(b.author));
  const strength = (c) => (c.own_words + c.bare_marks) * 1e6 + c.attested * 1e3 + c.named;
  const out = rows.slice(0, n).map(({ author, qual }) => {
    const rs = qual.sort((a, b) => (want.includes(b[0]) - want.includes(a[0])) || strength(b[1]) - strength(a[1])).slice(0, 15).map(([k, c]) => ({
      reader: k,
      marked: c.own_words + c.bare_marks ? { own_words: c.own_words, bare_marks: c.bare_marks } : undefined,
      attested_copies: c.attested || undefined, references: c.named || undefined,
    }));
    return { author, readers_count: qual.length, readers: rs, more_readers: qual.length > 15 ? qual.length - 15 : undefined };
  });
  const evText = { any: "any evidence (marks, held or borrowed copies, or naming them)", marked: "physical marks (own words or bare marks)", held_or_borrowed: "held or borrowed copies", named: "naming them in their own writing or notes" }[ev];
  return {
    out: {
      answer: `${rows.length} author${rows.length === 1 ? "" : "s"} reached by ${minR} or more readers through ${evText}${want.length ? `, including ${want.join(" and ")}` : ""}${lendingOk ? "" : ", lending-library members left out"}.`,
      evidence: ev, min_readers: minR, readers_required: want.length ? want : undefined, lending_library_included: lendingOk,
      authors_total: rows.length, authors: out,
      note: "Per reader, marks, attested copies and references are separate measurements and are not added together. A reader counts once whatever the evidence.",
      attribution: attribution(d, Object.keys(d.sources).filter((k) => k !== "nietzsche" || ev === "any" || ev === "named")),
    },
    log: { found: rows.length > 0 },
  };
}

let searchIdx;
export function searchMarginalia(args = {}) {
  const d = loadData();
  const q = norm(args.query);
  if (!q || q.length < 3) return { out: { ok: false, error: "Pass at least three letters of text as query, e.g. 'whale' or 'nothing can come of nothing'." }, isError: true };
  if (!searchIdx) searchIdx = {
    p: d.passages.map((p) => ({ p, m: norm(p.marked), s: norm(p.said + " " + p.trans) })),
    r: d.refs.map((x) => ({ x, t: norm(x.text) })),
  };
  const where = ["all", "reader_words", "marked_passages"].includes(args.where) ? args.where : "all";
  let ids = null, author = null;
  if (args.reader) { const f = findPerson(d, args.reader); if (!f.person) return notFoundReader(d, args.reader, f.closest); ids = new Set(f.person.ids); }
  if (args.author) { const r = resolve(args.author, d.authorCands); if (!r.hit) return { out: { found: false, answer: `No author like "${args.author}" in the corpus.`, closest_authors: r.closest }, log: { found: false } }; author = r.hit.name; }
  const words = q.split(" ");
  const run = (test) => {
    const hits = [];
    for (const e of searchIdx.p) {
      const v = d.volumes[e.p.v];
      if (!quotable(d, v.src) || (ids && !ids.has(v.r)) || (author && v.author !== author)) continue;
      if ((where !== "reader_words" && test(e.m)) || (where !== "marked_passages" && test(e.s))) hits.push({ t: "p", e: e.p, own: e.p.tier === 1 });
    }
    if (where !== "marked_passages") for (const e of searchIdx.r) {
      if (!quotable(d, e.x.src) || (ids && !ids.has(e.x.r)) || (author && e.x.author !== author)) continue;
      if (test(e.t)) hits.push({ t: "r", e: e.x, own: true });
    }
    return hits;
  };
  let mode = "phrase", hits = run((s) => s.includes(q));
  if (!hits.length && words.length > 1) { mode = "all words"; hits = run((s) => words.every((w) => s.includes(w))); }
  hits.sort((a, b) => b.own - a.own);
  const n = lim(args.limit, 10);
  const srcs = hits.slice(0, n).map((h) => (h.t === "p" ? d.volumes[h.e.v].src : h.e.src));
  const notSearchable = Object.entries(d.sources).filter(([, s]) => !s.emit_text).map(([, s]) => s.name);
  return {
    out: {
      query: args.query, match: hits.length ? mode : "none", hits_total: hits.length,
      answer: hits.length ? `${fmt(hits.length)} passage${hits.length === 1 ? "" : "s"} matching "${args.query}" (${mode} match).` : `Nothing matching "${args.query}" in the quotable text.`,
      hits: hits.slice(0, n).map((h) => (h.t === "p" ? passageOut(d, h.e) : refOut(d, h.e))).filter(Boolean),
      searched: "Text that the sources permit quoting: Melville's Marginalia Online, Derrida's Margins, Annotated Books Online (marks), and Derrida's and Nietzsche's own published prose (references).",
      not_searchable: `${notSearchable.join("; ")}: their transcriptions are not redistributable under their terms, so they are not here to search. reader_marks gives their counts.`,
      attribution: attribution(d, srcs),
    },
    log: { found: hits.length > 0 },
  };
}

export function aboutTheCorpus() {
  const d = loadData();
  const core = d.readers.filter((r) => !r.id.startsWith(LENDING + ":"));
  const tally = (r) => (d.volsByReader.get(r.i) || []).reduce((a, v) => ({ marks: a.marks + v.n1 + v.n2, attested: a.attested + v.n3, vols: a.vols + 1 }), { marks: 0, attested: 0, vols: 0 });
  const annot = core.map((r) => ({ r, t: tally(r), refs: (d.refsByReader.get(r.i) || []).length + (d.refEdgesByReader.get(r.i) || []).reduce((a, e) => a + e.n, 0) }))
    .sort((a, b) => b.t.marks - a.t.marks || b.refs - a.refs)
    .map(({ r, t }) => ({ reader: r.name, life: r.birth || r.death ? `${r.birth || "?"}–${r.death || "?"}` : undefined, volumes: t.vols, marks: t.marks, attested_copies: t.attested || undefined }));
  const lend = d.readers.filter((r) => r.id.startsWith(LENDING + ":")).map((r) => ({ r, t: tally(r) })).filter((x) => x.t.attested > 0).sort((a, b) => b.t.attested - a.t.attested);
  return {
    out: {
      what: "The real marks famous readers left in books, as physical evidence of reading: Melville's scores in Shakespeare, Harvey's and Dee's notes, Whitman, Derrida, Beckett, Nietzsche naming authors in his prose, and the Shakespeare and Company lending cards.",
      totals: d.totals, data_built: d.dataBuilt,
      evidence_tiers: {
        own_words: "T1: the reader's own words in the margin, beside a locatable passage",
        bare_marks: "T2: a score, underline, bracket, checkmark or X; locates a passage, says nothing",
        attested_copies: "T3: the reader demonstrably owned or borrowed the copy; no surviving mark",
        never_added: "Tiers are different kinds of evidence and are reported separately. References (a reader naming an author) are a separate measurement again.",
      },
      evidence_sets: d.notes,
      sources: Object.entries(d.sources).map(([k, s]) => ({ source: s.name, site: s.url, ...s.counts, text: s.emit_text ? "quotable with attribution" : "withheld: counts, metadata and links only", images: "never served", cite_as: s.citation, terms: s.terms })),
      annotating_readers: annot,
      lending_library: { source: d.sources[LENDING].name, members_with_borrows: lend.length, most_borrows: lend.slice(0, 12).map(({ r, t }) => ({ reader: r.name, borrows: t.attested })) },
      page: tag(SITE + "/"), code_and_data: REPO,
    },
    log: { found: true },
  };
}
