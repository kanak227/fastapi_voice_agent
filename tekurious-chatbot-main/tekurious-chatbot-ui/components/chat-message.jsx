'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * ChatMessage — renders bot responses with full Markdown support
 * (headings, bold, italic, lists, tables, code blocks, links)
 * and a premium, ChatGPT‑style look.
 *
 * User messages are rendered as plain text.
 */
export function ChatMessage({ content, isBot = false }) {
  if (!isBot) {
    // User messages — plain text, no markdown
    return (
      <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
        {content}
      </p>
    );
  }

  return (
    <div className="chat-markdown text-[15px] leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // — Headings —
          h1: ({ children }) => (
            <h3 className="text-lg font-bold mt-4 mb-2 text-zinc-900 first:mt-0">
              {children}
            </h3>
          ),
          h2: ({ children }) => (
            <h4 className="text-base font-bold mt-3.5 mb-1.5 text-zinc-900 first:mt-0">
              {children}
            </h4>
          ),
          h3: ({ children }) => (
            <h5 className="text-[15px] font-semibold mt-3 mb-1 text-zinc-800 first:mt-0">
              {children}
            </h5>
          ),

          // — Paragraphs —
          p: ({ children }) => (
            <p className="my-2 first:mt-0 last:mb-0 leading-relaxed">
              {children}
            </p>
          ),

          // — Bold & italic —
          strong: ({ children }) => (
            <strong className="font-semibold text-zinc-900">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-zinc-700">{children}</em>
          ),

          // — Lists —
          ul: ({ children }) => (
            <ul className="my-2 ml-1 space-y-1 list-none first:mt-0 last:mb-0">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2 ml-1 space-y-1 list-none counter-reset-item first:mt-0 last:mb-0">
              {children}
            </ol>
          ),
          li: ({ children, ordered, index }) => (
            <li className="flex items-start gap-2 text-zinc-800">
              <span className="shrink-0 mt-0.5 text-zinc-400 select-none" aria-hidden>
                {ordered ? `${(index ?? 0) + 1}.` : '•'}
              </span>
              <span className="flex-1">{children}</span>
            </li>
          ),

          // — Code —
          code: ({ inline, className, children, ...props }) => {
            if (inline) {
              return (
                <code
                  className="rounded bg-zinc-100 border border-zinc-200/80 px-1.5 py-0.5 text-[13px] font-mono text-pink-600"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <div className="my-3 rounded-xl overflow-hidden border border-zinc-200/60 bg-zinc-900 first:mt-0 last:mb-0">
                <div className="flex items-center justify-between px-4 py-2 bg-zinc-800/80 border-b border-zinc-700/50">
                  <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">
                    {className?.replace('language-', '') || 'code'}
                  </span>
                </div>
                <pre className="overflow-x-auto p-4">
                  <code
                    className={`text-[13px] font-mono leading-relaxed text-zinc-100 ${className || ''}`}
                    {...props}
                  >
                    {children}
                  </code>
                </pre>
              </div>
            );
          },

          // — Blockquotes —
          blockquote: ({ children }) => (
            <blockquote className="my-3 border-l-[3px] border-zinc-300 pl-4 text-zinc-600 italic first:mt-0 last:mb-0">
              {children}
            </blockquote>
          ),

          // — Links —
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700 underline decoration-blue-300 hover:decoration-blue-500 underline-offset-2 transition-colors"
            >
              {children}
            </a>
          ),

          // — Horizontal rules —
          hr: () => <hr className="my-4 border-zinc-200" />,

          // — Tables —
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-zinc-200/80 first:mt-0 last:mb-0">
              <table className="w-full text-sm">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-zinc-50/80 border-b border-zinc-200/80">
              {children}
            </thead>
          ),
          tbody: ({ children }) => <tbody className="divide-y divide-zinc-100">{children}</tbody>,
          tr: ({ children }) => <tr className="hover:bg-zinc-50/50 transition-colors">{children}</tr>,
          th: ({ children }) => (
            <th className="px-3 py-2 text-left text-[12px] font-semibold text-zinc-600 uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-zinc-700">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
