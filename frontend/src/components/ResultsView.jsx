import { useState } from "react"
import Icon from "./Icon.jsx"
import ClaimAccordion from "./ClaimAccordion.jsx"
import { VERDICTS, VERDICT_ORDER } from "../lib/verdicts.js"
import { validateInput } from "../lib/validate.js"

/** Count claims per verdict, in the fixed display order, skipping verdicts with none. */
function countVerdicts(claims) {
  return VERDICT_ORDER.map((verdict) => ({
    verdict,
    count: claims.filter((c) => c.verdict === verdict).length,
  })).filter((row) => row.count > 0)
}

/** Distribution bar plus a row of "N Verdict" chips. */
function Summary({ claims }) {
  const rows = countVerdicts(claims)
  return (
    <div className="grid gap-3">
      <div className="flex h-2 gap-[3px]" aria-hidden="true">
        {rows.map((row) => (
          <i
            key={row.verdict}
            style={{ flex: row.count }}
            className={`rounded-[2px] ${VERDICTS[row.verdict].fill}`}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-2">
        {rows.map((row) => (
          <li
            key={row.verdict}
            className={`inline-flex items-center gap-1.5 rounded-sm py-[3px] pr-2.5 pl-1.5 text-[13px] font-medium text-on-verdict ${VERDICTS[row.verdict].fill}`}
          >
            <Icon name={VERDICTS[row.verdict].icon} size={16} stroke={3} />
            <span className="font-mono tabular-nums">{row.count}</span> {VERDICTS[row.verdict].label}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Muted row for a claim that failed in search or evaluate. The API does not return its text. */
function FailedRow({ error }) {
  return (
    <div className="grid gap-1.5 rounded-lg border border-l-2 border-line border-l-contradicted bg-surface p-4">
      <p className="flex items-center gap-2 font-medium">
        <Icon name="alert" size={16} className="text-contradicted" />
        Claim {error.claim_id} could not be checked
      </p>
      <p className="flex flex-wrap items-center gap-2 text-[12.5px] text-error-text">
        <span className="rounded-[5px] border border-line px-1.5 font-mono text-[11.5px] text-mu">
          {error.stage}
        </span>
        {error.message}
      </p>
    </div>
  )
}

/**
 * "Check another" field with a Link / Paste text switch and a Check button; used on
 * results and the no-claims state. Calls onCheck with {url} or {text}.
 */
function RetryField({ onCheck }) {
  const [mode, setMode] = useState("link")
  const [value, setValue] = useState("")
  const [error, setError] = useState(null)

  function switchMode(next) {
    setMode(next)
    setValue("")
    setError(null)
  }

  function handleSubmit(event) {
    event.preventDefault()
    const problem = validateInput(mode, value, value)
    if (problem) {
      setError(problem)
    } else {
      setError(null)
      if (mode === "link") {
        onCheck({ url: value.trim() })
      } else {
        onCheck({ text: value.trim() })
      }
    }
  }

  const fieldClass = `min-w-0 rounded-sm border bg-surface px-3.5 py-3 transition-[border-color,box-shadow] hover:border-line-strong focus:border-white focus:shadow-focus focus:outline-none ${
    error ? "border-contradicted" : "border-line"
  }`
  const tabBase = "pb-0.5 text-[13px] transition-colors hover:text-fg"
  const submitButton = (
    <button
      type="submit"
      className="rounded-sm bg-fg px-4 py-3 text-[13px] font-medium text-on-verdict transition-[background,transform] hover:bg-white active:scale-[0.98]"
    >
      Check claims
    </button>
  )

  return (
    <form onSubmit={handleSubmit} noValidate className="grid gap-2">
      <div className="flex items-center justify-between gap-4">
        <label
          htmlFor="retry-field"
          className="font-mono text-[11px] font-medium tracking-[0.08em] text-mu uppercase"
        >
          {mode === "link" ? "Try another link" : "Try other text"}
        </label>
        <div role="tablist" aria-label="Input type" className="flex gap-4">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "link"}
            onClick={() => switchMode("link")}
            className={`${tabBase} ${mode === "link" ? "border-b border-fg text-fg" : "text-mu"}`}
          >
            Link
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "text"}
            onClick={() => switchMode("text")}
            className={`${tabBase} ${mode === "text" ? "border-b border-fg text-fg" : "text-mu"}`}
          >
            Paste text
          </button>
        </div>
      </div>
      {mode === "link" ? (
        <div className="flex gap-2">
          <input
            id="retry-field"
            type="url"
            inputMode="url"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="https://..."
            aria-invalid={error ? "true" : "false"}
            className={`flex-1 ${fieldClass}`}
          />
          {submitButton}
        </div>
      ) : (
        <div className="grid gap-2">
          <textarea
            id="retry-field"
            rows={5}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Paste the article or transcript here."
            aria-invalid={error ? "true" : "false"}
            className={`w-full resize-none leading-normal ${fieldClass}`}
          />
          <div className="flex items-center justify-between gap-3">
            <span className="font-mono text-xs text-mu tabular-nums">
              {value.trim().length} characters
            </span>
            {submitButton}
          </div>
        </div>
      )}
      {error ? (
        <p role="alert" className="flex items-start gap-2 text-[13px] text-error-text">
          <Icon name="alert" size={16} className="mt-0.5 text-contradicted" />
          {error}
        </p>
      ) : null}
    </form>
  )
}

/**
 * Results, summary first: source chip, summary, claim accordion in response order,
 * muted rows for failed claims, then a retry field.
 * @param {{result: object, sourceLabel: string, onCheck: Function}} props
 */
export default function ResultsView({ result, sourceLabel, onCheck }) {
  const failed = result.errors.filter((e) => e.claim_id !== null && e.claim_id !== undefined)
  const hasClaims = result.claims.length > 0

  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <span className="inline-flex max-w-full items-center gap-2 self-start font-mono text-xs text-mu">
          <Icon name="link" size={13} />
          <span className="min-w-0 [overflow-wrap:anywhere]">{sourceLabel}</span>
        </span>
        <p className="font-mono text-xs text-mu tabular-nums">
          {result.claims.length} {result.claims.length === 1 ? "claim" : "claims"}
        </p>
      </div>

      {hasClaims ? (
        <>
          <Summary claims={result.claims} />
          <div className="grid gap-2">
            {result.claims.map((claim, i) => (
              <ClaimAccordion key={claim.id} claim={claim} defaultOpen={i === 0} />
            ))}
            {failed.map((error) => (
              <FailedRow key={`${error.stage}-${error.claim_id}`} error={error} />
            ))}
          </div>
        </>
      ) : (
        <div className="grid gap-2 rounded-xl border border-dashed border-line-strong p-7 text-center">
          <h2 className="text-base font-medium">No checkable claims in this text</h2>
          <p className="mx-auto max-w-[34ch] text-[13.5px] text-mu">
            Opinions, jokes and plain descriptions do not count.
          </p>
        </div>
      )}

      <RetryField onCheck={onCheck} />
    </div>
  )
}
