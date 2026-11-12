import Icon from "./Icon.jsx"
import { VerdictBadge, ConfidenceMeter } from "./badges.jsx"
import SourceList from "./SourceList.jsx"
import DisputedTabs from "./DisputedTabs.jsx"

/**
 * Turn "Source 2" in an explanation into a small mono chip, so it reads as a
 * pointer to the numbered source list.
 * @param {string} text
 */
function renderExplanation(text) {
  return text.split(/(Source \d+)/g).map((part, i) => {
    if (/^Source \d+$/.test(part)) {
      return (
        <span
          key={i}
          className="mx-0.5 whitespace-nowrap rounded-[5px] border border-line bg-surface-2 px-[5px] font-mono text-xs font-medium text-fg"
        >
          {part}
        </span>
      )
    } else {
      return part
    }
  })
}

/**
 * One claim as a native <details>. The header (claim, verdict, confidence) is always
 * visible, so the verdict never hides when the item is collapsed.
 * @param {{claim: object, defaultOpen: boolean}} props
 */
export default function ClaimAccordion({ claim, defaultOpen }) {
  const entries = claim.sources.map((source, i) => ({ source, number: i + 1 }))

  return (
    <details open={defaultOpen} className="overflow-hidden rounded-lg border border-line bg-surface">
      <summary className="grid grid-cols-[minmax(0,1fr)_20px] items-start gap-x-3 gap-y-3 px-4 py-3.5 sm:px-5 sm:py-4">
        <span className="min-h-[28px] text-[15px] leading-[1.35] font-medium tracking-[-0.01em] text-pretty sm:text-lg">
          {claim.text}
        </span>
        <Icon name="chevron" size={20} className="chev mt-0.5 text-white transition-transform" />
        <span className="col-span-2 grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 sm:flex sm:justify-between">
          <VerdictBadge verdict={claim.verdict} />
          <ConfidenceMeter confidence={claim.confidence} />
        </span>
      </summary>
      <div className="grid gap-3 px-4 pb-[18px] sm:px-5 sm:pb-5">
        <p className="text-sm leading-[1.6] text-fg-2">{renderExplanation(claim.explanation)}</p>
        {claim.verdict === "disputed" ? (
          <DisputedTabs sources={claim.sources} claimId={claim.id} />
        ) : (
          <SourceList entries={entries} />
        )}
      </div>
    </details>
  )
}
