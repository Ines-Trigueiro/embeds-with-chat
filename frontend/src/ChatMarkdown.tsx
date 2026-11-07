import Markdown, { type Components } from "react-markdown";

// The model's replies render on the editor origin, so this stays strict: no raw HTML
// (react-markdown drops it unless rehype-raw is added, and it must not be), no images
// (they would load from anywhere), and javascript: URLs are removed by the default urlTransform.
const COMPONENTS: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

/** A model reply in the Conversation, as light Markdown. */
export function ChatMarkdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      <Markdown components={COMPONENTS} skipHtml disallowedElements={["img"]} unwrapDisallowed>
        {text}
      </Markdown>
    </div>
  );
}
