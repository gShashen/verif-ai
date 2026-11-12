// Lookup tables that map API values to labels, icons and Tailwind classes.
// Class names are written out in full so Tailwind can see them.

export const VERDICT_ORDER = ["supported", "contradicted", "disputed", "insufficient_evidence"]

export const VERDICTS = {
  supported: { label: "Supported", icon: "check", fill: "bg-supported" },
  contradicted: { label: "Contradicted", icon: "cross", fill: "bg-contradicted" },
  disputed: { label: "Disputed", icon: "split", fill: "bg-disputed" },
  insufficient_evidence: { label: "Not enough evidence", icon: "question", fill: "bg-insufficient" },
}

export const STANCES = {
  support: { label: "Supports", icon: "check", fill: "bg-supported", rule: "border-supported" },
  contradict: { label: "Contradicts", icon: "cross", fill: "bg-contradicted", rule: "border-contradicted" },
  not_addressed: { label: "Not addressed", icon: "minus", fill: "bg-insufficient", rule: "border-line-strong" },
}

export const CONFIDENCE = {
  low: { level: 1, label: "Low confidence" },
  medium: { level: 2, label: "Medium confidence" },
  high: { level: 3, label: "High confidence" },
}

export const TIER_HINT = {
  1: "Government",
  2: "Education, fact-checker or Wikipedia",
  3: "Everything else",
}
