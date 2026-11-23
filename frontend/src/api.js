// One place for talking to the FastAPI back end.
// - adds the login token to every request
// - turns { error: { code, message } } replies into a thrown Error with that message

const TOKEN_KEY = "rc_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// For teammates' features that may not be built yet.
// Returns { data } on success, { notReady: true } if the route doesn't exist (404), or { error }.
export async function apiOptional(path, options) {
  try {
    return { data: await api(path, options) };
  } catch (err) {
    if (err.status === 404 && (!err.code || err.code === "http_404")) return { notReady: true };
    return { error: err.message };
  }
}

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    // login uses form fields (username, password)
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const message = data?.error?.message || `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    err.code = data?.error?.code;
    throw err;
  }
  return data;
}
