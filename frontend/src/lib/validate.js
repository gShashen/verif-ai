// Client-side input checks. They mirror the backend (MIN_TEXT_CHARS = 100) so
// obvious mistakes are caught before a 20 to 50 s request is sent.

export const MIN_TEXT_CHARS = 100

export const LINK_ERROR = "That does not look like a link. Start with https:// and paste the full address."
export const TEXT_ERROR = "That is too short to hold checkable claims. Paste at least 100 characters."

/**
 * True when `value` parses as an http or https URL.
 * @param {string} value
 * @returns {boolean}
 */
export function isValidUrl(value) {
  try {
    const parsed = new URL(value.trim())
    return parsed.protocol === "http:" || parsed.protocol === "https:"
  } catch {
    return false
  }
}

/**
 * Check the form input for the current mode.
 * @param {"link"|"text"} mode
 * @param {string} url
 * @param {string} text
 * @returns {string|null} an error message, or null when the input is fine
 */
export function validateInput(mode, url, text) {
  if (mode === "link") {
    if (isValidUrl(url)) {
      return null
    } else {
      return LINK_ERROR
    }
  } else if (text.trim().length >= MIN_TEXT_CHARS) {
    return null
  } else {
    return TEXT_ERROR
  }
}
