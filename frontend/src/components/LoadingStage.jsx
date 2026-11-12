import { useEffect, useState } from "react"

// The backend does not stream progress, so stages advance on a client timer.
// It is an estimate, not live progress. Seconds at which each stage starts:
const STAGE_STARTS = [0, 6, 16, 34]
const SLOW_AFTER_S = 120

function stagesFor(isText) {
  return [
    {
      name: isText ? "Reading your text" : "Reading the page",
      line: isText ? "Getting your text ready" : "Pulling the transcript or article text",
    },
    { name: "Finding claims", line: "Choosing 3 to 6 checkable claims" },
    { name: "Searching the web", line: "Looking for sources on each claim" },
    { name: "Weighing sources", line: "Labelling what each source says" },
  ]
}

/** Format whole seconds as mm:ss. */
function formatClock(totalSeconds) {
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, "0")
  const s = String(totalSeconds % 60).padStart(2, "0")
  return `${m}:${s}`
}

/** Index of the stage that should be showing after `seconds` seconds. */
function stageIndexAt(seconds) {
  let index = 0
  STAGE_STARTS.forEach((start, i) => {
    if (seconds >= start) {
      index = i
    }
  })
  return index
}

/**
 * One stage at a time, large and light. Holds on the last stage until the
 * response arrives.
 * @param {{isText: boolean}} props
 */
export default function LoadingStage({ isText }) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const startedAt = Date.now()
    const timer = setInterval(() => {
      setSeconds(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const stages = stagesFor(isText)
  const current = stageIndexAt(seconds)
  const stage = stages[current]

  return (
    <div className="grid gap-6" role="status" aria-live="polite">
      <p className="font-mono text-xs font-medium text-mu tabular-nums">
        {current + 1} / {stages.length}
      </p>
      <div className="grid gap-2">
        <h2 className="text-[34px] leading-[1.08] font-light tracking-[-0.03em]">{stage.name}</h2>
        <p className="text-mu">{stage.line}</p>
      </div>
      <div className="flex gap-2" aria-hidden="true">
        {stages.map((s, i) => (
          <i
            key={s.name}
            className={`h-0.5 w-7 rounded-sm transition-colors ${i <= current ? "bg-fg" : "bg-line-strong"}`}
          />
        ))}
      </div>
      <div className="flex justify-between text-[12.5px] text-mu">
        <span className="font-mono tabular-nums">{formatClock(seconds)}</span>
        <span>Usually 20 to 50 s</span>
      </div>
      {seconds >= SLOW_AFTER_S ? (
        <p className="text-[13px] text-fg-2">This is taking longer than usual.</p>
      ) : null}
    </div>
  )
}
