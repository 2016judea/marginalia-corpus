// MCP server over the Marginalia Corpus. Streamable HTTP, stateless JSON responses, no auth.
// Pattern from breach-to-claim api/mcp.js: one PostHog event per tool call carrying only the
// tool, whether it worked and how long it took. What was asked is never logged or stored.
// The corpus is static: mcp/index.json.gz, built once by mcp/build_index.py from _data/, with
// rights.py's emit_text gate applied at build time. Nothing here calls a source archive.
import crypto from "node:crypto";
import { SITE, readerMarks, whoReadAuthor, readerProfile, authorsReadByMany, searchMarginalia, aboutTheCorpus, didReaderReadAuthor, shakespeareAndCompanyBorrowing } from "../lib/marginalia.js";

const VERSION = "0.1.0";
const PH_KEY = "phc_yFgRGppL6H7DvhgZTQKbHdrY5oqnpLT482rrNYtLqnAx"; // public project key, same block as the pages
// Every tool reads one static file bundled with the function: nothing is written, nothing
// outside is reached, the same arguments give the same answer.
const ANN = { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true };

export const TOOLS = [
  {
    name: "reader_marks",
    title: "What a reader marked in an author or a book",
    description: "The marks one reader left in the books of one author, or in one title, from the Marginalia Corpus. Answers questions like 'what did Melville mark in Shakespeare?', 'what did Derrida write in the margins of Rousseau?', 'show me Melville's notes in Beale's Natural History of the Sperm Whale', 'how much did Gabriel Harvey annotate his Livy?'. Returns counts by kind of evidence, kept separate: own_words (the reader's own words in the margin), bare_marks (a score, underline, bracket or checkmark), attested_copies (the reader held or borrowed the copy, no surviving mark), each also counted in the reader's certain own hand. Lists the volumes (edition, library, shelfmark, link) and, where the source's terms permit quotation, the passages: marked_passage is the book author's printed words under the mark, reader_wrote is the reader's own words, each with a citation line. For Archaeology of Reading (Harvey, Dee, Winthrop), the Walt Whitman Archive and the Beckett Digital Library the text is withheld under their terms and only counts, pages and metadata are returned. Reader, author and title names are matched loosely; a name that matches nothing comes back with the closest names.",
    inputSchema: { type: "object", properties: {
      reader: { type: "string", description: "The reader, e.g. 'Herman Melville', 'Melville', 'Gabriel Harvey', 'Derrida', 'Beckett'." },
      author: { type: "string", description: "Optional: the author whose books were marked, e.g. 'Shakespeare', 'Homer', 'Rousseau'." },
      title: { type: "string", description: "Optional: words from the book's title, e.g. 'Sperm Whale', 'Paradise Lost', 'Macbeth'." },
      kind: { type: "string", enum: ["all", "own_words", "bare_marks"], description: "Optional: which passages to list. own_words = the reader wrote something; bare_marks = a mark with no words. Default all." },
      own_hand_only: { type: "boolean", description: "Optional: true lists only passages the source attributes to the reader's own hand with certainty (Melville's Channing volumes, for instance, are mostly his wife's or uncertain)." },
      contains: { type: "string", description: "Optional: only passages whose text contains these words, e.g. 'whale'." },
      limit: { type: "integer", minimum: 1, maximum: 30, description: "How many passages (default 10)." },
      volumes_limit: { type: "integer", minimum: 1, maximum: 100, description: "How many volumes to list (default 15)." },
    }, required: ["reader"], additionalProperties: false },
    annotations: { title: "Reader's marks in an author", ...ANN },
  },
  {
    name: "who_read_author",
    title: "Who read an author: marked, held or borrowed, or named",
    description: "Every reader in the Marginalia Corpus with documented evidence of reading one author, in separate groups that are never merged: marked (left own words or bare marks in a copy of the author), held_or_borrowed (owned or borrowed a copy, no surviving mark, including Shakespeare and Company lending-card borrows in Paris 1919-1941, dated to the day), named_in_their_writing (named the author in their own published work or a marginal note: Nietzsche's prose, Derrida's De la grammatologie, Harvey's and Dee's notes), and named_as_a_person_in_a_note. Answers questions like 'who read Homer?', 'which writers borrowed Joyce from Sylvia Beach?', 'who marked Shakespeare?', 'did anyone annotate Montaigne?'. Each reader comes with counts per kind of evidence, life dates and source. include_lending_library=false leaves out the 253 lending-library members and keeps the annotators.",
    inputSchema: { type: "object", properties: {
      author: { type: "string", description: "The author read, e.g. 'Shakespeare', 'Homer', 'James Joyce', 'Plato'." },
      include_lending_library: { type: "boolean", description: "Optional: false leaves out Shakespeare and Company lending-card members. Default true." },
      limit: { type: "integer", minimum: 1, maximum: 300, description: "Most readers to list per group (default 25)." },
    }, required: ["author"], additionalProperties: false },
    annotations: { title: "Who read an author", ...ANN },
  },
  {
    name: "reader_profile",
    title: "A reader's profile: volumes, most-marked authors, dates",
    description: "One reader's whole record in the Marginalia Corpus: volumes held, volumes with marks, counts by kind of evidence (own words, bare marks, attested copies, and how many are certainly in the reader's own hand), a per-source breakdown with whether its text is quotable, the most-marked authors, the authors the reader names in their own writing, the people named in their notes, and a date span (life, edition years of the copies held, and reading dates where the source attests them). Answers questions like 'what did Melville read?', 'tell me about John Dee's library', 'who did Nietzsche name most?', 'what did Hemingway borrow from Shakespeare and Company?'. One person with two records (Samuel Beckett: his own library and a Paris lending card) is returned as one reader.",
    inputSchema: { type: "object", properties: {
      reader: { type: "string", description: "The reader, e.g. 'Melville', 'John Dee', 'Nietzsche', 'Ernest Hemingway'." },
      top: { type: "integer", minimum: 1, maximum: 50, description: "How many authors to list (default 12)." },
    }, required: ["reader"], additionalProperties: false },
    annotations: { title: "Reader profile", ...ANN },
  },
  {
    name: "authors_read_by_many",
    title: "Authors reached by more than one reader",
    description: "Authors that two or more readers in the Marginalia Corpus have evidence of reading, most readers first, each with the readers and their evidence kept per kind (marks, attested copies, references). Answers questions like 'which authors did the most readers mark?', 'what did Melville and Beckett both read?', 'which authors did three or more annotators physically mark?', 'who are the most borrowed authors at Shakespeare and Company?'. evidence picks the kind that counts: any, marked (own words or bare marks only), held_or_borrowed, or named. readers keeps only authors that every named reader reached.",
    inputSchema: { type: "object", properties: {
      evidence: { type: "string", enum: ["any", "marked", "held_or_borrowed", "named"], description: "Which kind of evidence counts a reader in. Default any." },
      min_readers: { type: "integer", minimum: 2, maximum: 100, description: "At least this many readers (default 2)." },
      readers: { type: "array", items: { type: "string" }, maxItems: 6, description: "Optional: only authors reached by every one of these readers, e.g. ['Melville', 'Beckett']." },
      exclude_lending_library: { type: "boolean", description: "Optional: true leaves out Shakespeare and Company lending-card members. Default false." },
      limit: { type: "integer", minimum: 1, maximum: 200, description: "How many authors (default 20)." },
    }, additionalProperties: false },
    annotations: { title: "Authors read by many", ...ANN },
  },
  {
    name: "search_marginalia",
    title: "Search the quotable marginalia and marked passages",
    description: "Full-text search over the marginalia text that the sources permit quoting: Melville's Marginalia Online (Melville's notes and the lines he marked), Derrida's Margins (his annotations and the passages he marked, plus his quotations of other authors in De la grammatologie), Annotated Books Online (notes by Dee, Luther, Erasmus, Scaliger and others, with translations), and Nietzsche naming other authors in his published works. Answers questions like 'did Melville mark \"nothing can come of nothing\"?', 'which marginal notes mention the whale?', 'where does Derrida quote Saussure on writing?', 'what does Nietzsche say about Wagner?'. Accent- and case-insensitive; phrase match first, then all words. Archaeology of Reading, Walt Whitman Archive and Beckett Digital Library text is not in the searchable set, under their terms.",
    inputSchema: { type: "object", properties: {
      query: { type: "string", description: "Words or a phrase to find, e.g. 'whale', 'nothing can come of nothing', 'écriture'." },
      reader: { type: "string", description: "Optional: only this reader's marks, e.g. 'Melville'." },
      author: { type: "string", description: "Optional: only marks in this author's books, or references to this author." },
      where: { type: "string", enum: ["all", "reader_words", "marked_passages"], description: "reader_words = what the reader wrote (notes, translations, their own published prose); marked_passages = the printed lines they marked. Default all." },
      limit: { type: "integer", minimum: 1, maximum: 30, description: "How many hits (default 10)." },
    }, required: ["query"], additionalProperties: false },
    annotations: { title: "Search marginalia", ...ANN },
  },
  {
    name: "about_the_corpus",
    title: "What is in the Marginalia Corpus, its sources and terms",
    description: "The Marginalia Corpus at a glance: totals (555 readers, 9,303 volumes, 216,552 marks, 11,774 references), the three kinds of evidence, each of the eight source archives with its counts, whether its text is quotable, its terms and the citation it asks for, every annotating reader with their counts, and the most frequent Shakespeare and Company lending-library borrowers. Answers questions like 'what's in the marginalia corpus?', 'which readers are covered?', 'where does this data come from?', 'how should I cite it?'.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { title: "About the corpus", ...ANN },
  },
  // ---- theme doors (QUESTIONS.md, 2026-11-22): one named tool per kind of question ----
  {
    name: "did_reader_read_author",
    title: "Did this reader read that author?",
    description: "A yes or no, with the evidence, for whether one reader in the Marginalia Corpus read one author: marks they left in a copy (own words and bare marks), copies they held or borrowed with no surviving mark (including Shakespeare and Company lending-card borrows), references to the author in their own writing, and mentions of the author as a person in their notes. Each kind is reported on its own and never added together. A no means the surviving record holds no evidence, not that the reading never happened.\n\nExample questions:\n- \"Did Melville read Shakespeare?\"\n- \"Did Beckett read Proust?\"\n- \"Did Nietzsche ever mention Schopenhauer?\"",
    inputSchema: { type: "object", properties: {
      reader: { type: "string", description: "The reader, e.g. 'Melville', 'Samuel Beckett', 'Nietzsche'." },
      author: { type: "string", description: "The author, e.g. 'Shakespeare', 'Proust', 'Emerson'." },
    }, required: ["reader", "author"], additionalProperties: false },
    annotations: { title: "Did a reader read an author", ...ANN },
  },
  {
    name: "what_reader_wrote_in_margins",
    title: "What a reader wrote in the margins",
    description: "Only the notes one reader wrote in their own words in the margins of their books (not bare underlines or scores), from the Marginalia Corpus, optionally narrowed to one author, one title or a word. Each note comes with the printed passage it sits beside, the page, whether the source attributes the hand to the reader with certainty, and its cite line. Text a source withholds under its terms is counted, not quoted.\n\nExample questions:\n- \"What did Melville write in the margins of his Milton?\"\n- \"What notes did John Dee leave in his books?\"\n- \"Derrida's handwritten notes on Rousseau\"",
    inputSchema: { type: "object", properties: {
      reader: { type: "string", description: "The reader, e.g. 'Melville', 'John Dee', 'Derrida'." },
      author: { type: "string", description: "Optional: the author whose books carry the notes, e.g. 'Milton'." },
      title: { type: "string", description: "Optional: words from the book's title." },
      contains: { type: "string", description: "Optional: only notes or passages containing these words." },
      own_hand_only: { type: "boolean", description: "Optional: true keeps only notes the source attributes to the reader's own hand with certainty." },
      limit: { type: "integer", minimum: 1, maximum: 30, description: "How many notes (default 10)." },
    }, required: ["reader"], additionalProperties: false },
    annotations: { title: "What a reader wrote in the margins", ...ANN },
  },
  {
    name: "what_reader_said_about",
    title: "What a reader said about a subject",
    description: "Search one reader's own words in the Marginalia Corpus for a subject: their marginal notes, translations they wrote in, and (for Nietzsche and Derrida) their own published prose. The book author's printed lines are left out, so every hit is the reader speaking. Each hit carries the book, the page and its cite line.\n\nExample questions:\n- \"What did Melville say about God in his margins?\"\n- \"What did Nietzsche write about Wagner?\"\n- \"What did Luther write about Christ in his books?\"",
    inputSchema: { type: "object", properties: {
      reader: { type: "string", description: "The reader, e.g. 'Melville', 'Nietzsche', 'John Dee'." },
      subject: { type: "string", description: "Words or a phrase to find in what they wrote, e.g. 'God', 'Wagner', 'whale'." },
      limit: { type: "integer", minimum: 1, maximum: 30, description: "How many hits (default 10)." },
    }, required: ["reader", "subject"], additionalProperties: false },
    annotations: { title: "What a reader said about a subject", ...ANN },
  },
  {
    name: "what_readers_both_read",
    title: "Authors two or more readers both read",
    description: "The authors that every one of two to six named readers has evidence of reading in the Marginalia Corpus, most readers first, with each reader's evidence kept by kind (marks, attested copies or borrows, references in their writing). Narrow to one kind of evidence with evidence.\n\nExample questions:\n- \"What did Melville and Beckett both read?\"\n- \"Which authors did John Dee and Gabriel Harvey both read?\"\n- \"Authors Gertrude Stein and Hemingway both borrowed\"",
    inputSchema: { type: "object", properties: {
      readers: { type: "array", items: { type: "string" }, minItems: 2, maxItems: 6, description: "Two to six readers, e.g. ['Melville', 'Beckett']." },
      evidence: { type: "string", enum: ["any", "marked", "held_or_borrowed", "named"], description: "Which kind of evidence counts. Default any." },
      limit: { type: "integer", minimum: 1, maximum: 200, description: "How many authors (default 20)." },
    }, required: ["readers"], additionalProperties: false },
    annotations: { title: "Authors readers both read", ...ANN },
  },
  {
    name: "shakespeare_and_company_borrowing",
    title: "Shakespeare and Company lending library: who borrowed what",
    description: "Sylvia Beach's Shakespeare and Company lending cards (Paris, 1919-1941): who borrowed an author, with the most-borrowed titles and each member's dates; or, for one member, every author and title on their card. A borrow is attested contact with a copy, dated on the card, not proof of reading.\n\nExample questions:\n- \"What did Hemingway borrow from Shakespeare and Company?\"\n- \"Who borrowed Joyce from Sylvia Beach's library?\"\n- \"What did Gertrude Stein borrow from Sylvia Beach?\"",
    inputSchema: { type: "object", properties: {
      author: { type: "string", description: "The author borrowed, e.g. 'Joyce', 'D. H. Lawrence'. With reader, narrows that member's card to this author." },
      reader: { type: "string", description: "A lending-library member, e.g. 'Hemingway', 'Gertrude Stein', 'Walter Benjamin'." },
      limit: { type: "integer", minimum: 1, maximum: 200, description: "How many borrowers or authors to list (default 25)." },
    }, additionalProperties: false },
    annotations: { title: "Shakespeare and Company borrowing", ...ANN },
  },
];

export const INSTRUCTIONS = "The Marginalia Corpus is the physical evidence of reading: the marks famous readers left in their own books (Melville's scores in Shakespeare, Gabriel Harvey's and John Dee's notes, Whitman, Derrida, Beckett, Luther, Erasmus), Nietzsche naming authors in his prose, and Sylvia Beach's Shakespeare and Company lending cards. reader_marks answers what one reader marked in one author or book; who_read_author answers who read an author; reader_profile summarises one reader; authors_read_by_many finds authors several readers reached; search_marginalia searches the quotable text; about_the_corpus describes the sources and their terms. Shortcuts for common questions: did_reader_read_author (a yes or no with the evidence), what_reader_wrote_in_margins, what_reader_said_about, what_readers_both_read, shakespeare_and_company_borrowing. Quote counts exactly as returned. Own words, bare marks, attested copies and references are different kinds of evidence: report them separately and never add them together. marked_passage is the book author's printed words and reader_wrote is the reader's own words; never attribute one to the other. Where a source's text is withheld (Archaeology of Reading, Walt Whitman Archive, Beckett Digital Library), say it is withheld under that source's terms and do not reconstruct or paraphrase it. When quoting a passage, give its cite line, which carries the attribution the source requires. hand_is_reader false means the source does not attribute the mark to the reader with certainty; say so before crediting it to them.";

const HANDLERS = { reader_marks: readerMarks, who_read_author: whoReadAuthor, reader_profile: readerProfile, authors_read_by_many: authorsReadByMany, search_marginalia: searchMarginalia, about_the_corpus: aboutTheCorpus,
  did_reader_read_author: didReaderReadAuthor,
  what_reader_wrote_in_margins: (a) => readerMarks({ ...a, kind: "own_words" }),
  what_reader_said_about: (a) => searchMarginalia({ query: a.subject, reader: a.reader, where: "reader_words", limit: a.limit }),
  what_readers_both_read: (a) => authorsReadByMany({ readers: a.readers, evidence: a.evidence, limit: a.limit, min_readers: 2 }),
  shakespeare_and_company_borrowing: shakespeareAndCompanyBorrowing,
};

export function callTool(name, args = {}) {
  const h = HANDLERS[name];
  if (!h) return { out: { ok: false, error: "Unknown tool " + name }, isError: true };
  return h(args || {});
}

// One event per call: tool, ok, duration. distinct_id is random per call, so no person is
// profiled. The calling app's name (its user-agent) is logged; the caller's address and words are not.
// attempted: a tool name a caller reached for that does not exist (letters, digits, _.- only, 60 chars).
// The calling app, from its user-agent (Claude-User, openai-mcp, a crawler's name): no person, only the app.
const clientOf = (ua) => (/claude/i.test(ua) ? "claude" : /openai|chatgpt/i.test(ua) ? "chatgpt" : /grok|xai/i.test(ua) ? "grok" : /cursor/i.test(ua) ? "cursor" : /node|undici|python|curl/i.test(ua) ? "script" : "other");
const clientProps = (ua = "") => ({ client: clientOf(ua), client_ua: ua.split(/[\/\s]/)[0].slice(0, 40), client_ua_full: ua.slice(0, 120) });

async function logCall(tool, ok, ms, meta, attempted) {
  if (process.env.MARGINALIA_NO_ANALYTICS || meta.test) return;
  try {
    await fetch("https://us.i.posthog.com/capture/", { method: "POST", headers: { "content-type": "application/json" }, signal: AbortSignal.timeout(1500),
      body: JSON.stringify({ api_key: PH_KEY, event: "mcp_tool_call", distinct_id: "mcp_" + crypto.randomUUID(),
        properties: { tool, ok, ms, ...(attempted ? { attempted } : {}), ...clientProps(meta.ua), site: "marginalia-corpus", $process_person_profile: false, $lib: "marginalia-corpus-mcp" } }) });
  } catch {}
}

const text = (obj) => ({ content: [{ type: "text", text: JSON.stringify(obj, null, 1) }], structuredContent: obj });

export async function handleOne(msg, meta = {}) {
  const { id, method, params } = msg || {};
  const ok = (result) => ({ jsonrpc: "2.0", id, result });
  if (method === "initialize") return ok({ protocolVersion: (params && params.protocolVersion) || "2025-06-18", capabilities: { tools: { listChanged: false } }, serverInfo: { name: "marginalia-corpus", title: "Marginalia Corpus: what famous readers marked", version: VERSION, websiteUrl: SITE + "/connect/" }, instructions: INSTRUCTIONS });
  if (method === "ping") return ok({});
  if (method === "tools/list") return ok({ tools: TOOLS });
  if (method === "tools/call") {
    const t0 = Date.now(), tool = String((params && params.name) || "");
    let r;
    try { r = callTool(tool, (params && params.arguments) || {}); }
    catch (e) { r = { out: { ok: false, error: "Error: " + e.message }, isError: true }; }
    await logCall(HANDLERS[tool] ? tool : "unknown", !r.isError, Date.now() - t0, meta, HANDLERS[tool] ? undefined : tool.replace(/[^A-Za-z0-9_.-]/g, "").slice(0, 60));
    return ok({ ...text(r.out), ...(r.isError ? { isError: true } : {}) });
  }
  if (method === "resources/list") return ok({ resources: [] });
  if (method === "prompts/list") return ok({ prompts: [] });
  if (method && method.startsWith("notifications/")) return null;
  return { jsonrpc: "2.0", id, error: { code: -32601, message: "Method not found: " + method } };
}

async function readBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") return JSON.parse(req.body);
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "null");
}

export default async function handler(req, res) {
  res.setHeader("access-control-allow-origin", "*");
  res.setHeader("access-control-allow-headers", "content-type, mcp-session-id, mcp-protocol-version, authorization, x-marginalia-test");
  res.setHeader("access-control-allow-methods", "POST, GET, OPTIONS, DELETE");
  if (req.method === "OPTIONS") { res.statusCode = 204; return res.end(); }
  if (req.method === "GET") { res.statusCode = 405; res.setHeader("allow", "POST"); res.setHeader("content-type", "application/json"); return res.end(JSON.stringify({ name: "Marginalia Corpus MCP", transport: "streamable-http", url: SITE + "/mcp", docs: SITE + "/connect/" })); }
  if (req.method === "DELETE") { res.statusCode = 204; return res.end(); }
  let body;
  try { body = await readBody(req); } catch { res.statusCode = 400; res.setHeader("content-type", "application/json"); return res.end(JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } })); }
  const ua = String(req.headers["user-agent"] || "");
  const meta = { test: !!req.headers["x-marginalia-test"], ua };
  const batch = Array.isArray(body);
  const out = (await Promise.all((batch ? body : [body]).map((m) => handleOne(m, meta)))).filter(Boolean);
  if (!out.length) { res.statusCode = 202; return res.end(); }
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify(batch ? out : out[0]));
}
