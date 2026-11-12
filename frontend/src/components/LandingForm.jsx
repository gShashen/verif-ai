import { useEffect, useRef } from "react"
import Icon from "./Icon.jsx"

const HINT_LINK = "Paste a YouTube or article link."
const HINT_TEXT = "Paste at least 100 characters so there are claims to check."

const FIELD =
  "block w-full rounded-sm border bg-surface px-4 py-[15px] transition-[border-color,box-shadow] hover:border-line-strong focus:border-white focus:shadow-focus focus:outline-none"

/**
 * Link / Paste text form. Controlled: the parent owns mode, url, text and the error,
 * so it can switch to Paste text and focus it after an extraction failure.
 * @param {{mode: string, onModeChange: Function, url: string, onUrlChange: Function,
 *   text: string, onTextChange: Function, error: string|null, onSubmit: Function}} props
 */
export default function LandingForm({
  mode,
  onModeChange,
  url,
  onUrlChange,
  text,
  onTextChange,
  error,
  onSubmit,
}) {
  const urlRef = useRef(null)
  const textRef = useRef(null)
  const firstRender = useRef(true)

  // Focus the active field whenever the tab changes (not on first load).
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
    } else if (mode === "text") {
      textRef.current?.focus()
    } else {
      urlRef.current?.focus()
    }
  }, [mode])

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit()
  }

  const borderTone = error ? "border-contradicted" : "border-line"
  const tabBase = "pb-0.5 text-[13px] transition-colors hover:text-fg"

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="grid gap-3.5 rounded-xl border border-line bg-surface p-4 sm:rounded-none sm:border-0 sm:bg-transparent sm:p-0"
    >
      <div role="tablist" aria-label="Input type" className="flex gap-4">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "link"}
          onClick={() => onModeChange("link")}
          className={`${tabBase} ${mode === "link" ? "border-b border-fg text-fg" : "text-mu"}`}
        >
          Link
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "text"}
          onClick={() => onModeChange("text")}
          className={`${tabBase} ${mode === "text" ? "border-b border-fg text-fg" : "text-mu"}`}
        >
          Paste text
        </button>
      </div>

      {mode === "link" ? (
        <label className="grid gap-2">
          <span className="font-mono text-[11px] font-medium tracking-[0.08em] text-mu uppercase">
            Video or article link
          </span>
          <input
            ref={urlRef}
            type="url"
            inputMode="url"
            autoComplete="off"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            aria-invalid={error ? "true" : "false"}
            className={`${FIELD} ${borderTone}`}
          />
        </label>
      ) : (
        <label className="grid gap-2">
          <span className="font-mono text-[11px] font-medium tracking-[0.08em] text-mu uppercase">
            Text to check
          </span>
          <textarea
            ref={textRef}
            rows={6}
            value={text}
            onChange={(e) => onTextChange(e.target.value)}
            placeholder="Paste the article or transcript here."
            aria-invalid={error ? "true" : "false"}
            className={`${FIELD} resize-none leading-normal ${borderTone}`}
          />
          <span className="text-right font-mono text-xs text-mu tabular-nums">
            {text.trim().length} characters
          </span>
        </label>
      )}

      {/* Hint and inline error share one slot with a reserved height so the layout never jumps. */}
      <div className="min-h-5 text-[13px]">
        {error ? (
          <p role="alert" className="flex items-start gap-2 text-error-text">
            <Icon name="alert" size={16} className="mt-0.5 text-contradicted" />
            {error}
          </p>
        ) : (
          <p className="text-mu">{mode === "link" ? HINT_LINK : HINT_TEXT}</p>
        )}
      </div>

      <button
        type="submit"
        className="w-full rounded-sm bg-fg px-[22px] py-[15px] font-medium text-on-verdict transition-[background,transform] hover:bg-white active:scale-[0.98] sm:w-auto sm:justify-self-start sm:py-3"
      >
        Check claims
      </button>
    </form>
  )
}
