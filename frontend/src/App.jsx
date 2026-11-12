import { useState } from "react"
import { verify, ApiError } from "./api.js"
import { validateInput } from "./lib/validate.js"
import LandingForm from "./components/LandingForm.jsx"
import LoadingStage from "./components/LoadingStage.jsx"
import ResultsView from "./components/ResultsView.jsx"
import Toast from "./components/Toast.jsx"

/** Turn an ApiError (or any thrown value) into the toast the design calls for. */
function toastForError(error) {
  if (error instanceof ApiError && error.status === 0) {
    return { title: "We could not reach VerifAI", body: "Check your connection and try again." }
  } else if (error instanceof ApiError && error.status === 422) {
    return {
      title: "We could not read that page",
      body: error.message || "The page may block automated readers or need a login.",
    }
  } else if (error instanceof ApiError) {
    return { title: "Something went wrong", body: error.message }
  } else {
    return { title: "Something went wrong", body: "Try again in a moment." }
  }
}

/** Toast for a 200 response that still carries problems, or null when all is well. */
function toastForResult(result) {
  const failedIds = new Set(
    result.errors.filter((e) => e.claim_id !== null && e.claim_id !== undefined).map((e) => e.claim_id),
  )
  const checked = result.claims.length
  if (checked === 0) {
    return {
      title: "No checkable claims in this text",
      body: "Opinions, jokes and plain descriptions do not count.",
    }
  } else if (failedIds.size > 0) {
    return {
      title: `${checked} of ${checked + failedIds.size} claims were checked`,
      body: `The other ${failedIds.size === 1 ? "one" : failedIds.size} hit a problem.`,
    }
  } else {
    return null
  }
}

/**
 * Root component. One view state: idle, loading or results. Errors never get their
 * own view; they appear as a toast and the page content stays put.
 */
export default function App() {
  const [view, setView] = useState("idle")
  const [mode, setMode] = useState("link")
  const [url, setUrl] = useState("")
  const [text, setText] = useState("")
  const [formError, setFormError] = useState(null)
  const [toast, setToast] = useState(null)
  const [result, setResult] = useState(null)
  const [sourceLabel, setSourceLabel] = useState("")
  const [loadingIsText, setLoadingIsText] = useState(false)

  /** Send one request. `input` is {url} or {text}. */
  async function run(input) {
    setToast(null)
    setFormError(null)
    setLoadingIsText(input.text !== undefined)
    setView("loading")
    try {
      const data = await verify(input)
      setResult(data)
      setSourceLabel(input.url ? input.url : "Pasted text")
      setToast(toastForResult(data))
      setView("results")
    } catch (error) {
      setToast(toastForError(error))
      setView("idle")
      // An unreadable page: offer the paste-text fallback right away.
      if (error instanceof ApiError && error.status === 422 && input.url !== undefined) {
        setMode("text")
      }
    }
  }

  /** Validate the landing form, then run. */
  function handleSubmit() {
    const problem = validateInput(mode, url, text)
    if (problem) {
      setFormError(problem)
      setToast(
        mode === "link"
          ? {
              title: "That does not look like a link",
              body: "Start with https:// and paste the full address of a YouTube video or an article.",
            }
          : { title: "That text is too short", body: problem },
      )
    } else if (mode === "link") {
      run({ url: url.trim() })
    } else {
      run({ text: text.trim() })
    }
  }

  /** Retry field on the results view. */
  function handleCheckUrl(newUrl) {
    setUrl(newUrl)
    setMode("link")
    run({ url: newUrl })
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-[18px] pt-8 pb-16 sm:px-6">
      <header className={view === "idle" ? "hidden sm:block" : ""}>
        <button
          type="button"
          onClick={() => {
            setView("idle")
            setToast(null)
          }}
          className="flex items-center gap-2 text-sm font-medium tracking-[0.02em]"
        >
          <span className="size-2 rounded-full bg-fg" aria-hidden="true" />
          VerifAI
        </button>
      </header>

      {view === "idle" ? (
        <main className="flex flex-1 flex-col justify-end gap-10 sm:gap-16 sm:pt-24">
          <div className="flex flex-1 items-center justify-center sm:hidden">
            <h1 className="text-[34px] leading-none font-normal tracking-[-0.01em]">VerifAI</h1>
          </div>
          <h1 className="hidden max-w-[12em] text-[34px] leading-[1.08] font-light tracking-[-0.03em] sm:block">
            Is it true? Check the sources.
          </h1>
          <LandingForm
            mode={mode}
            onModeChange={setMode}
            url={url}
            onUrlChange={(v) => {
              setUrl(v)
              setFormError(null)
            }}
            text={text}
            onTextChange={(v) => {
              setText(v)
              setFormError(null)
            }}
            error={formError}
            onSubmit={handleSubmit}
          />
        </main>
      ) : null}

      {view === "loading" ? (
        <main className="flex flex-1 flex-col justify-center py-16">
          <LoadingStage isText={loadingIsText} />
        </main>
      ) : null}

      {view === "results" && result ? (
        <main className="pt-8">
          <ResultsView result={result} sourceLabel={sourceLabel} onCheckUrl={handleCheckUrl} />
        </main>
      ) : null}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  )
}
