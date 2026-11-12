import Icon from "./Icon.jsx"

/**
 * Dismissible message pinned to the bottom of the viewport. Stays until dismissed
 * or the next submit. Orange alert icon marks an error; blue check marks success.
 * @param {{toast: {title: string, body: string, kind?: "bad"|"ok"}|null, onDismiss: () => void}} props
 */
export default function Toast({ toast, onDismiss }) {
  if (!toast) {
    return null
  } else {
    const isBad = toast.kind !== "ok"
    return (
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-10 flex justify-center px-4 pb-[max(16px,env(safe-area-inset-bottom))]"
      >
        <div
          role="alert"
          className="pointer-events-auto flex w-full max-w-md animate-[toast-in_200ms_ease] items-start gap-3 rounded-sm border border-line-strong bg-surface-2 px-4 py-3.5 shadow-toast"
        >
          <Icon
            name={isBad ? "alert" : "check"}
            size={18}
            className={`mt-0.5 ${isBad ? "text-contradicted" : "text-supported"}`}
          />
          <div className="min-w-0">
            <b className="block text-sm font-medium">{toast.title}</b>
            {toast.body ? <p className="text-[13px] text-fg-2">{toast.body}</p> : null}
          </div>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss message"
            className="ml-auto p-0.5 text-mu transition-colors hover:text-fg"
          >
            <Icon name="cross" size={16} />
          </button>
        </div>
      </div>
    )
  }
}
