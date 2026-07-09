"use client";

/**
 * Lightweight markdown renderer (no dependency).
 * Supports fenced code, inline code, bold/italic, headings, lists, links, [n] cites.
 */
export default function SimpleMarkdown({ text, onCiteClick }) {
  const raw = text || "";
  if (!raw) return null;

  const blocks = splitBlocks(raw);

  return (
    <div className="nf-md space-y-2.5 break-words">
      {blocks.map((block, i) => {
        if (block.type === "code") {
          return (
            <pre
              key={i}
              className="overflow-x-auto rounded-lg bg-neutral-900 px-3 py-2.5 font-mono text-[12px] leading-relaxed text-neutral-100"
            >
              <code>{block.content}</code>
            </pre>
          );
        }
        if (block.type === "ul") {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5 text-neutral-800">
              {block.items.map((item, j) => (
                <li key={j}>{renderInline(item, onCiteClick)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "ol") {
          return (
            <ol key={i} className="list-decimal space-y-1 pl-5 text-neutral-800">
              {block.items.map((item, j) => (
                <li key={j}>{renderInline(item, onCiteClick)}</li>
              ))}
            </ol>
          );
        }
        if (block.type === "h") {
          const Tag = `h${Math.min(block.level, 4)}`;
          const sizes = {
            1: "text-base font-semibold",
            2: "text-[15px] font-semibold",
            3: "text-sm font-semibold",
            4: "text-sm font-semibold",
          };
          return (
            <Tag key={i} className={`${sizes[block.level] || sizes[3]} text-neutral-900`}>
              {renderInline(block.content, onCiteClick)}
            </Tag>
          );
        }
        return (
          <p key={i} className="whitespace-pre-wrap leading-relaxed text-neutral-800">
            {renderInline(block.content, onCiteClick)}
          </p>
        );
      })}
    </div>
  );
}

function splitBlocks(text) {
  const lines = text.split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const fence = line.match(/^```/);
    if (fence) {
      const body = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) {
        body.push(lines[i]);
        i += 1;
      }
      blocks.push({ type: "code", content: body.join("\n") });
      i += 1;
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: "h", level: heading[1].length, content: heading[2] });
      i += 1;
      continue;
    }
    if (/^\s*[-*•]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*•]\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "ul", items });
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "ol", items });
      continue;
    }
    // Paragraph (consume until blank)
    const para = [];
    while (i < lines.length && lines[i].trim() !== "" && !lines[i].startsWith("```") && !/^(#{1,4})\s+/.test(lines[i]) && !/^\s*[-*•]\s+/.test(lines[i]) && !/^\s*\d+\.\s+/.test(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    if (para.length) {
      blocks.push({ type: "p", content: para.join("\n") });
    } else {
      i += 1;
    }
  }
  return blocks;
}

function renderInline(text, onCiteClick) {
  if (!text) return null;
  // Tokenize: code, bold, italic, links, cites
  const parts = [];
  const re =
    /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(\[[^\]]+\]\([^)]+\))|(\[\d+\])/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ t: "text", v: text.slice(last, m.index) });
    if (m[1]) parts.push({ t: "code", v: m[1].slice(1, -1) });
    else if (m[2]) parts.push({ t: "bold", v: m[2].slice(2, -2) });
    else if (m[3]) parts.push({ t: "em", v: m[3].slice(1, -1) });
    else if (m[4]) {
      const lm = m[4].match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      parts.push({ t: "link", v: lm[1], href: lm[2] });
    } else if (m[5]) {
      const n = Number(m[5].slice(1, -1));
      parts.push({ t: "cite", v: n });
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ t: "text", v: text.slice(last) });

  return parts.map((p, i) => {
    if (p.t === "code") {
      return (
        <code
          key={i}
          className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-[12px] text-neutral-800"
        >
          {p.v}
        </code>
      );
    }
    if (p.t === "bold") return <strong key={i}>{p.v}</strong>;
    if (p.t === "em") return <em key={i}>{p.v}</em>;
    if (p.t === "link") {
      return (
        <a
          key={i}
          href={p.href}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-indigo-700 underline-offset-2 hover:underline"
        >
          {p.v}
        </a>
      );
    }
    if (p.t === "cite") {
      return (
        <button
          key={i}
          type="button"
          onClick={() => onCiteClick?.(p.v)}
          className="mx-0.5 inline-flex h-4 min-w-[1rem] items-center justify-center rounded bg-emerald-100 px-1 align-super text-[10px] font-bold text-emerald-800 hover:bg-emerald-200"
          title={`Jump to citation [${p.v}]`}
        >
          {p.v}
        </button>
      );
    }
    return <span key={i}>{p.v}</span>;
  });
}
