// Icon paths copied from docs/design/icons.svg (24 x 24 viewBox, stroke only).
const PATHS = {
  check: <path d="M4 12.5l5 5L20 6.5" />,
  cross: <path d="M6 6l12 12M18 6L6 18" />,
  split: <path d="M4 8h14m0 0l-3.5-3.5M18 8l-3.5 3.5M20 16H6m0 0l3.5-3.5M6 16l3.5 3.5" />,
  question: <path d="M8.5 9a3.5 3.5 0 1 1 5.3 3c-1.1.7-1.8 1.3-1.8 2.7M12 19v.01" />,
  minus: <path d="M6 12h12" />,
  alert: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.5v.01" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M15.5 15.5L21 21" />
    </>
  ),
  external: <path d="M7 17L17 7M9 7h8v8" />,
  chevron: <path d="M6 9l6 6 6-6" />,
  link: <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1" />,
}

/**
 * One icon from the Graphite set. Decorative by default (aria-hidden), because a
 * word always sits next to it.
 * @param {{name: string, size?: number, stroke?: number, className?: string}} props
 */
export default function Icon({ name, size = 16, stroke = 2.4, className = "" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      {PATHS[name]}
    </svg>
  )
}
