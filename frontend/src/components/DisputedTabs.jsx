import { useState } from "react"
import SourceList from "./SourceList.jsx"

const TAB_IDS = ["all", "support", "contradict"]

/**
 * Filter tabs for a disputed claim: All / Supporting / Contradicting. Sources keep
 * their original numbers. not_addressed sources only show under All.
 * @param {{sources: object[], claimId: number}} props
 */
export default function DisputedTabs({ sources, claimId }) {
  const [active, setActive] = useState("all")

  const entries = sources.map((source, i) => ({ source, number: i + 1 }))
  const supporting = entries.filter((e) => e.source.stance === "support")
  const contradicting = entries.filter((e) => e.source.stance === "contradict")

  const tabs = [
    { id: "all", label: "All", list: entries },
    { id: "support", label: "Supporting", list: supporting },
    { id: "contradict", label: "Contradicting", list: contradicting },
  ]
  const shown = tabs.find((t) => t.id === active).list

  function handleKeyDown(event) {
    const index = TAB_IDS.indexOf(active)
    let next = null
    if (event.key === "ArrowRight") {
      next = TAB_IDS[(index + 1) % TAB_IDS.length]
    } else if (event.key === "ArrowLeft") {
      next = TAB_IDS[(index + TAB_IDS.length - 1) % TAB_IDS.length]
    }
    if (next) {
      event.preventDefault()
      setActive(next)
      document.getElementById(`tab-${claimId}-${next}`)?.focus()
    }
  }

  return (
    <div className="grid gap-3">
      <div
        role="tablist"
        aria-label="Filter sources by stance"
        onKeyDown={handleKeyDown}
        className="flex gap-1 rounded-full border border-line bg-surface p-[3px]"
      >
        {tabs.map((tab) => {
          const isActive = tab.id === active
          return (
            <button
              key={tab.id}
              id={`tab-${claimId}-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${claimId}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setActive(tab.id)}
              className={`flex-1 rounded-full px-2 py-[7px] text-[13px] transition-colors ${
                isActive ? "bg-fg font-medium text-on-verdict" : "text-mu hover:text-fg"
              }`}
            >
              {tab.label} <span className="font-mono tabular-nums">{tab.list.length}</span>
            </button>
          )
        })}
      </div>
      <div id={`panel-${claimId}`} role="tabpanel" aria-labelledby={`tab-${claimId}-${active}`}>
        <SourceList entries={shown} />
      </div>
    </div>
  )
}
