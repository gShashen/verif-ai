import Icon from "./Icon.jsx"
import { VERDICTS, STANCES, CONFIDENCE, TIER_HINT } from "../lib/verdicts.js"

/**
 * Solid verdict chip: filled with the verdict colour, dark icon and text.
 * @param {{verdict: string}} props
 */
export function VerdictBadge({ verdict }) {
  const meta = VERDICTS[verdict] || VERDICTS.insufficient_evidence
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm py-[3px] pr-2.5 pl-1.5 text-[13px] font-medium text-on-verdict ${meta.fill}`}
    >
      <Icon name={meta.icon} size={16} stroke={3} />
      {meta.label}
    </span>
  )
}

/**
 * Three rising bars plus a word. Never a percentage.
 * @param {{confidence: string}} props
 */
export function ConfidenceMeter({ confidence }) {
  const meta = CONFIDENCE[confidence] || CONFIDENCE.low
  const heights = ["h-1.5", "h-2.5", "h-3.5"]
  return (
    <span className="inline-flex min-w-[140px] items-end gap-[3px] whitespace-nowrap text-xs text-mu">
      {heights.map((h, i) => (
        <b
          key={h}
          className={`w-1 rounded-[1px] ${h} ${i < meta.level ? "bg-fg" : "bg-line-strong"}`}
        />
      ))}
      <em className="ml-1.5 self-center not-italic">{meta.label}</em>
    </span>
  )
}

/**
 * "Tier N" in mono plus three pips (Tier 1 fills 3, Tier 2 fills 2, Tier 3 fills 1).
 * @param {{tier: 1|2|3}} props
 */
export function TierBadge({ tier }) {
  const filled = 4 - tier
  let tone = "border-line-strong text-fg-2"
  if (tier === 1) {
    tone = "border-fg-2 text-fg"
  } else if (tier === 3) {
    tone = "border-line text-mu"
  }
  return (
    <span
      title={TIER_HINT[tier]}
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-xs border py-0.5 pr-2 pl-1.5 font-mono text-[11px] font-medium ${tone}`}
    >
      <span className="flex gap-0.5" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <i
            key={i}
            className={`size-[5px] rounded-full border ${i < filled ? "border-fg bg-fg" : "border-mu"}`}
          />
        ))}
      </span>
      Tier {tier}
    </span>
  )
}

/**
 * Small coloured square with an icon plus the stance word.
 * @param {{stance: string}} props
 */
export function StanceChip({ stance }) {
  const meta = STANCES[stance] || STANCES.not_addressed
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium text-fg">
      <i className={`grid size-4 place-items-center rounded-[4px] text-on-verdict not-italic ${meta.fill}`}>
        <Icon name={meta.icon} size={10} stroke={3.4} />
      </i>
      {meta.label}
    </span>
  )
}
