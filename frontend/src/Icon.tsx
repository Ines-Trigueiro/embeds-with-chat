// A small inline icon set: 24×24 strokes in currentColor, so icons follow the text colour.

const PATHS = {
  send: "M5 12h13M13 6l6 6-6 6",
  attach: "M20 11.5 12.4 19a5 5 0 0 1-7.1-7.1L13 4.3a3.3 3.3 0 0 1 4.7 4.7L10 16.6a1.7 1.7 0 0 1-2.4-2.4l7-7",
  copy: "M9 9h10v10H9zM5 15V5h10",
  check: "M5 12.5 10 17.5 19 7",
  pencil: "M4 20h4L19 9l-4-4L4 16v4zM13.5 6.5l4 4",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4",
  plus: "M12 5v14M5 12h14",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 7.5v.5",
  warning: "M12 4 2.5 20h19L12 4zM12 10v4M12 17v.5",
  blocker: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8.5 8.5l7 7M15.5 8.5l-7 7",
  desktop: "M3 5h18v11H3zM9 20h6M12 16v4",
  mobile: "M8 3h8v18H8zM11.5 18h1",
  sidebar: "M4 4h16v16H4zM9 4v16",
  chevronDown: "M6 9l6 6 6-6",
  close: "M6 6l12 12M18 6 6 18",
  external: "M14 4h6v6M20 4l-9 9M18 14v6H4V6h6",
  publish: "M12 16V4M7 9l5-5 5 5M5 20h14",
  code: "M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14",
  logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
  sparkle: "M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6",
  menu: "M4 7h16M4 12h16M4 17h16",
  chat: "M4 5h16v11H9l-5 4V5z",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  table: "M4 5h16v14H4zM4 10h16M4 14.5h16M10 5v14",
  image: "M4 5h16v14H4zM4 16l5-5 4 4 2-2 5 5M15.5 9.5h.5",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
