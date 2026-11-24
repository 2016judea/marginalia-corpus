// Writes public/index.html, public/connect/index.html, public/privacy/index.html,
// public/sitemap.xml from api/mcp.js (the tools) and mcp/index.json.gz (totals, and each
// source's name, editors, terms and citation as rights.py states them). Never hand-edit the
// output: run `node scripts/build_pages.mjs`. test/mcp.test.mjs fails if a page drifts from
// the tools or the totals.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { TOOLS, callTool } from "../api/mcp.js";
import { loadData, SITE, REPO } from "../lib/marginalia.js";

process.env.MARGINALIA_NO_ANALYTICS = "1";
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const PUB = path.join(ROOT, "public");
const d = loadData();
const T = d.totals;
const fmt = (n) => Number(n).toLocaleString("en-US");
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const MCP = SITE + "/mcp";
const SUPPORT = "https://brickandmortar.dev/contact";
const TODAY = new Date().toISOString().slice(0, 10);

const POSTHOG = fs.readFileSync(path.join(process.env.HOME, ".claude/skills/site-analytics/posthog_snippet.html"), "utf8").replace("__SITE__", "marginalia-corpus").trim();

const head = (title, desc, url) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${esc(title)}</title><meta name="description" content="${esc(desc)}"><link rel="canonical" href="${url}">
<meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${url}"><meta property="og:type" content="website">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/icon.png"><link rel="stylesheet" href="/style.css">
<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)}</script><script defer src="/_vercel/insights/script.js"></script>
${POSTHOG}
</head><body>
<header class="top"><div class="wrap"><a class="brand" href="/">Marginalia Corpus</a><nav><a href="/connect/">Connect</a><a href="/privacy/">Privacy</a><a href="${REPO}">Source</a></nav></div></header>`;

const foot = `<footer><div class="wrap">
<p>Built once from eight public scholarly archives and served as a static file. Text is quoted only where the archive's own terms allow it, with the citation it asks for. No images from any archive are served or linked.</p>
<p><a href="/">Home</a> · <a href="/connect/">Use it in Claude</a> · <a href="/privacy/">Privacy</a> · <a href="${REPO}">Code and data</a> · <a href="${SUPPORT}">Support</a></p>
</div></footer>
<script>(function(){try{var s=new URLSearchParams(location.search).get("src");if(s&&window.posthog)posthog.register({src:s});}catch(e){}
var b=document.querySelector("[data-copy]");if(b)b.addEventListener("click",function(){var t=document.getElementById(b.getAttribute("data-copy")).textContent;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){b.textContent="Copied";setTimeout(function(){b.textContent="Copy"},1600)},function(){});try{window.va&&va("event",{name:"copy_mcp_url"})}catch(e){}});})();</script>
</body></html>
`;

const urlBox = `<div class="url"><code id="mcp-url">${MCP}</code><button type="button" data-copy="mcp-url">Copy</button></div>`;

// One real answer, pulled through the tool itself so the page shows what the connector returns.
const ex = callTool("reader_marks", { reader: "Melville", author: "Shakespeare", contains: "Miranda", limit: 1 }).out;
const p = ex.passages[0];
const example = `<figure class="mark">
<p class="ask">“What did Melville write in his Shakespeare?”</p>
<blockquote>${esc(p.reader_wrote)}</blockquote>
<figcaption>${esc(p.reader)}, in his own hand, beside <i>The Tempest</i>: ${esc(p.book.replace(/ \[Vol\. (\d+) of (\d+)\]$/, ", vol. $1 of $2"))}, p. ${esc(p.page)}. One of ${fmt(ex.counts.own_words)} notes and ${fmt(ex.counts.bare_marks)} bare marks in his ${ex.volumes_total} volumes of Shakespeare.</figcaption>
<p class="cite">${esc(p.cite)}</p>
</figure>`;

const EXAMPLES = {
  reader_marks: "What did Melville mark in Shakespeare?",
  who_read_author: "Who read Homer, and what is the evidence?",
  reader_profile: "Tell me about John Dee's library.",
  authors_read_by_many: "Which authors did both Melville and Beckett read?",
  search_marginalia: "Did Melville mark “Nothing can come of nothing”?",
  about_the_corpus: "Where does this data come from?",
};
const toolList = `<ul class="tools">${TOOLS.map((t) => `<li><code>${t.name}</code><span>${esc(t.title)}</span><em>“${esc(EXAMPLES[t.name])}”</em></li>`).join("")}</ul>`;

const sources = Object.entries(d.sources).sort((a, b) => (b[1].counts.n_marks || 0) - (a[1].counts.n_marks || 0));
const credits = `<ul class="credits">${sources.map(([, s]) => `<li><a href="${esc(s.url)}">${esc(s.name)}</a>. ${esc(s.editors)}. <b>${s.emit_text ? "Text quoted with attribution." : "Counts and metadata only; text withheld under its terms."}</b><br><span class="cite">${esc(s.citation)}</span></li>`).join("")}</ul>`;

const STARTERS = ["What did Melville mark in Shakespeare?", "Who read Homer, and what kind of evidence is there?", "Which authors did both Melville and Beckett read?"];

const pages = {
  "index.html": head("Marginalia Corpus: what famous readers marked in their books", `The real marks ${fmt(T.readers)} readers left in ${fmt(T.volumes)} books, from Melville to Beckett, as a Claude connector.`, SITE + "/") + `
<main class="wrap">
<h1>The marks famous readers left in their books.</h1>
<p class="lede">${fmt(T.marks)} marks by ${fmt(T.readers)} readers in ${fmt(T.volumes)} volumes. Melville, Harvey, Dee, Whitman, Derrida, Beckett, Nietzsche, and the Shakespeare and Company lending cards. Ask Claude about them.</p>
${example}
<h2>Add it to Claude</h2>
${urlBox}
<p class="small">Settings → Connectors → Add custom connector → paste the URL. No account, no key. <a href="/connect/">Full setup</a>.</p>
<h2>${TOOLS.length} tools</h2>
${toolList}
<h2>Three kinds of evidence, never added together</h2>
<p><b>Own words</b>: the reader wrote in the margin. <b>Bare marks</b>: a score, underline or checkmark beside a passage. <b>Attested copies</b>: the reader owned or borrowed the book and no mark survives. A reader naming an author in their own prose is a fourth thing, a reference, and is counted apart.</p>
</main>` + foot,

  "connect/index.html": head("Marginalia Corpus connector for Claude (MCP)", "Add the Marginalia Corpus MCP server to Claude: ask what Melville marked in Shakespeare, who read Homer, or what Derrida wrote beside Rousseau.", SITE + "/connect/") + `
<main class="wrap">
<h1>Use the Marginalia Corpus in Claude</h1>
<p class="lede">A read-only MCP server over the marks famous readers left in their books. Ask a question in plain words; Claude calls the tools and quotes the source.</p>
<h2>Server URL</h2>
${urlBox}
<p class="small">Streamable HTTP. No account, no key, no sign-in. Every tool is read-only.</p>
<h2>Add it</h2>
<ol><li>In Claude, open <b>Settings → Connectors</b>.</li><li>Choose <b>Add custom connector</b>.</li><li>Name it <i>Marginalia Corpus</i>, paste the URL above, and save. No authentication.</li><li>In a chat, turn the connector on from the tools menu and ask.</li></ol>
<h2>Try</h2>
<ul class="starters">${STARTERS.map((s) => `<li>“${esc(s)}”</li>`).join("")}</ul>
<h2>Tools</h2>
${toolList}
<h2>What comes back</h2>
<p>Counts of each kind of evidence, kept separate; the volumes, with edition, library and shelfmark; and, where the archive allows quotation, the passage itself with the citation it asks for. For the Archaeology of Reading, the Walt Whitman Archive and the Beckett Digital Library the connector returns counts and metadata only: their terms do not permit republishing the transcriptions. No archive images are ever served or linked.</p>
<h2>Sources and credits</h2>
${credits}
</main>` + foot,

  "privacy/index.html": head("Privacy | Marginalia Corpus", "The Marginalia Corpus connector logs which tool ran, whether it worked, how long it took and which app called it. Nothing identifying, and never what was asked.", SITE + "/privacy/") + `
<main class="wrap">
<h1>Privacy</h1>
<p class="lede">Last updated November 22, 2026. The Marginalia Corpus is run by Brick and Mortar AI LLC, Saint Paul, Minnesota, which is responsible for the connector and this site. It needs nothing about you: there is no account and nothing to sign in to.</p>
<p><b>What the connector receives.</b> Only what your assistant (Claude, ChatGPT or another app) sends with a tool call: a reader's name, an author or book title, or a few search words. It does not receive your conversation, your name, your email or your account with that app.</p>
<p><b>What it does with it.</b> Those words are matched against a static file and then dropped when the call ends. They are not stored, logged, used to train any model, sold or shared. No model runs on our side.</p>
<p><b>What is counted.</b> For each call we send one event to PostHog with four things: which tool ran, whether it worked, how long it took, and the name of the app that called it (its user agent, such as Claude or ChatGPT). No IP address, no account, nothing that identifies you or your words. These events are kept while the connector runs, to see which tools are used and which fail.</p>
<p><b>This website.</b> We count visits with Vercel Web Analytics (no cookies) and PostHog: pages viewed, the copy button, and whether a visit came from the connector (<code>src=mcp</code> in the link).</p>
<p><b>Who else handles it.</b> Vercel hosts the connector and this site and keeps short-lived request logs (time, path, IP address) under its own privacy policy. PostHog stores the counts above. Nothing is shared with anyone else, and nothing is sold.</p>
<p><b>The data.</b> The corpus is a static file built from public scholarly archives (credited on the <a href="/connect/">connect page</a>). The connector does not call those archives and sends them nothing.</p>
<p><b>Your choices.</b> You can disconnect the connector in your app's settings at any time. Because nothing kept here identifies you, there is no personal data held to access, export or delete; write to us if you want that confirmed.</p>
<p><b>Children.</b> The connector is not directed at children under 13 and does not knowingly receive their information.</p>
<p><b>Changes.</b> If this policy changes, the date at the top changes with it.</p>
<p>Questions or privacy requests: <a href="${SUPPORT}">brickandmortar.dev/contact</a>.</p>
</main>` + foot,
};

for (const [rel, html] of Object.entries(pages)) {
  const f = path.join(PUB, rel);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, html);
}
fs.writeFileSync(path.join(PUB, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${["/", "/connect/", "/privacy/"].map((u) => `<url><loc>${SITE}${u}</loc><lastmod>${TODAY}</lastmod></url>`).join("\n")}
</urlset>
`);
console.log("wrote", Object.keys(pages).join(", "), "+ sitemap.xml");
