import katex from "katex";
import { marked } from "marked";

// Configure marked for safe, synchronous rendering
marked.setOptions({
  breaks: true,   // GFM line breaks
  gfm: true,      // GitHub Flavored Markdown
  async: false,
});

/**
 * Render a TeX string to HTML via KaTeX.
 */
function renderTex(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex.trim(), {
      displayMode,
      throwOnError: false,
      output: "htmlAndMathml",
    });
  } catch {
    return `<span class="text-red-400">[LaTeX error]</span>`;
  }
}

/**
 * Render Markdown + LaTeX to HTML.
 *
 * Strategy:
 *  1. Extract all math expressions and replace with unique placeholders
 *  2. Run Markdown on the placeholder-substituted text
 *  3. Restore placeholders with rendered KaTeX HTML
 *
 * Supports: $$...$$, $...$, \[...\], \(...\)
 */
export function renderMarkdown(text: string): string {
  const placeholders: Map<string, string> = new Map();
  let counter = 0;

  // Pattern to match math delimiters (order matters: display before inline)
  const mathPattern = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\$([^\s$](?:[^$]*?[^\s$])?)\$|\\\((.+?)\\\)/g;

  // Step 1: Extract math → placeholders
  const withPlaceholders = text.replace(mathPattern, (_match, dd, bs, di, bp) => {
    const id = `%%MATH_${counter++}%%`;
    if (dd !== undefined) {
      placeholders.set(id, renderTex(dd, true));
    } else if (bs !== undefined) {
      placeholders.set(id, renderTex(bs, true));
    } else if (di !== undefined) {
      placeholders.set(id, renderTex(di, false));
    } else if (bp !== undefined) {
      placeholders.set(id, renderTex(bp, false));
    }
    return id;
  });

  // Step 2: Render Markdown
  let html = marked.parse(withPlaceholders) as string;

  // Step 3: Restore math from placeholders
  for (const [id, rendered] of placeholders) {
    html = html.replace(id, rendered);
  }

  return html;
}
