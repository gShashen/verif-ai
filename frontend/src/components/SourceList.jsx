import Icon from "./Icon.jsx"
import { TierBadge, StanceChip } from "./badges.jsx"
import { STANCES } from "../lib/verdicts.js"

/**
 * One numbered source. The number is the source's position in the full list,
 * because explanations say "Source 2" and must still match when the list is filtered.
 * @param {{source: object, number: number}} props
 */
export function SourceRow({ source, number }) {
  const meta = STANCES[source.stance] || STANCES.not_addressed
  return (
    <li className="grid grid-cols-[22px_minmax(0,1fr)] gap-2.5 border-b border-line py-2.5 last:border-b-0 last:pb-0">
      <span className="grid size-5 place-items-center rounded-full border border-line-strong font-mono text-[10px] font-medium text-fg-2">
        {number}
      </span>
      <div className="grid min-w-0 gap-1.5">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-start gap-1 text-sm leading-snug font-medium [overflow-wrap:anywhere] hover:underline hover:underline-offset-[3px]"
        >
          {source.title || source.domain}
          <Icon name="external" size={13} className="mt-[3px] text-mu" />
        </a>
        <span className="font-mono text-xs text-mu">{source.domain}</span>
        <div className="flex flex-wrap items-center gap-2.5">
          <TierBadge tier={source.tier} />
          <StanceChip stance={source.stance} />
        </div>
        {source.evidence ? (
          <p className={`border-l-2 pl-2.5 text-[13px] leading-normal text-fg-2 ${meta.rule}`}>
            {source.evidence}
          </p>
        ) : null}
      </div>
    </li>
  )
}

/**
 * The numbered source list. `entries` is [{source, number}] so callers can filter
 * without losing the original numbers.
 * @param {{entries: Array<{source: object, number: number}>}} props
 */
export default function SourceList({ entries }) {
  if (entries.length === 0) {
    return <p className="border-t border-line pt-3 text-[13px] text-mu">No sources in this view.</p>
  } else {
    return (
      <ol className="grid border-t border-line">
        {entries.map(({ source, number }) => (
          <SourceRow key={number} source={source} number={number} />
        ))}
      </ol>
    )
  }
}
