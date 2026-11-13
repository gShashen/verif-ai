import fixture01 from "./fixtures/01.json"
import fixture03 from "./fixtures/03.json"
import fixture07 from "./fixtures/07.json"
// Design samples, so every result state is reachable without API cost:
// https://example.com/disputed, /partial, /no-claims
import sampleDisputed from "./fixtures/sample-disputed.json"
import samplePartial from "./fixtures/sample-partial.json"
import sampleNoClaims from "./fixtures/sample-no-claims.json"

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === "true"
const FIXTURES = [fixture01, fixture03, fixture07, sampleDisputed, samplePartial, sampleNoClaims]
const FIXTURE_DELAY_MS = 1500

/**
 * Error thrown by verify(). `message` is safe to show the user.
 * `status` is the HTTP status, or 0 when the server could not be reached.
 */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

/** Resolve after `ms` milliseconds (fakes network time in fixture mode). */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Pick a saved response for the input. Matches on input_url; anything else
 * (including pasted text) gets fixture 01 so the happy path is always testable.
 */
function pickFixture(input) {
  const match = FIXTURES.find((f) => f.input_url === input.url)
  if (match) {
    return match
  } else {
    return fixture01
  }
}

/** Fixture mode: return a saved /verify response with no network and no API cost. */
async function verifyFromFixture(input) {
  await sleep(FIXTURE_DELAY_MS)
  const saved = pickFixture(input)
  if (saved.status === 200) {
    return saved.response
  } else {
    throw new ApiError(saved.response.detail, saved.status)
  }
}

/** Live mode: POST the input to the FastAPI /verify endpoint. */
async function verifyFromApi(input) {
  let response
  try {
    response = await fetch(`${API_URL}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    })
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0)
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (response.ok) {
    return body
  } else if (typeof body?.detail === "string") {
    throw new ApiError(body.detail, response.status)
  } else {
    throw new ApiError("Something went wrong on the server. Try again.", response.status)
  }
}

/**
 * Verify a URL or pasted text.
 * @param {{url?: string, text?: string}} input exactly one of url or text
 * @returns {Promise<object>} the VerifyResponse JSON
 * @throws {ApiError} with a user-facing message
 */
export async function verify(input) {
  if (USE_FIXTURES) {
    return verifyFromFixture(input)
  } else {
    return verifyFromApi(input)
  }
}
