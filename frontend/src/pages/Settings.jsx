import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

const NOTIFICATION_OPTIONS = [
  ["replies", "Replies and comments", "When someone replies to your post or comment."],
  ["follows", "New followers", "When another member follows you."],
  ["recommendations", "Paper recommendations", "Occasional paper suggestions based on your interests."],
  ["trends", "Topic activity", "When a topic you follow has an unusual activity spike."],
];

function readNotifications(userId) {
  try {
    const stored = JSON.parse(localStorage.getItem(`rc_notifications_${userId}`) || "null");
    return Object.fromEntries(NOTIFICATION_OPTIONS.map(([key]) => [key, stored?.[key] ?? true]));
  } catch {
    return Object.fromEntries(NOTIFICATION_OPTIONS.map(([key]) => [key, true]));
  }
}

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [theme, setTheme] = useState(() => localStorage.getItem("rc_theme") || "light");
  const [textSize, setTextSize] = useState(() => localStorage.getItem("rc_text_size") || "normal");
  const [reduceMotion, setReduceMotion] = useState(() => localStorage.getItem("rc_reduce_motion") === "true");
  const [notifications, setNotifications] = useState(() => readNotifications(user.id));
  const [saved, setSaved] = useState("");
  const [password, setPassword] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);

  useEffect(() => {
    localStorage.setItem(`rc_notifications_${user.id}`, JSON.stringify(notifications));
  }, [notifications, user.id]);

  function updateAppearance(key, value, setter) {
    setter(value);
    localStorage.setItem(key, value);
    if (key === "rc_theme") document.documentElement.dataset.theme = value;
    if (key === "rc_text_size") document.documentElement.dataset.textSize = value;
    if (key === "rc_reduce_motion") document.documentElement.dataset.reduceMotion = value;
  }

  function toggleNotification(key) {
    setNotifications((current) => ({ ...current, [key]: !current[key] }));
    setSaved("Preferences saved on this browser.");
    window.setTimeout(() => setSaved(""), 1800);
  }

  async function changePassword(event) {
    event.preventDefault();
    setPasswordError("");
    setPasswordMessage("");
    if (password.new_password !== password.confirm_password) {
      setPasswordError("The new passwords don’t match.");
      return;
    }
    setPasswordBusy(true);
    try {
      await api("/auth/password", {
        method: "PUT",
        body: { current_password: password.current_password, new_password: password.new_password },
      });
      setPassword({ current_password: "", new_password: "", confirm_password: "" });
      setPasswordMessage("Password changed successfully.");
    } catch (error) {
      setPasswordError(error.message);
    } finally {
      setPasswordBusy(false);
    }
  }

  function signOut() {
    logout();
    navigate("/login");
  }

  return (
    <section className="settings-page">
      <header className="settings-heading">
        <span className="eyebrow">YOUR SPACE · YOUR PREFERENCES</span>
        <h1>Settings</h1>
        <p>Shape how ScholarSphere looks and how you use your account.</p>
      </header>

      <section className="card settings-card" aria-labelledby="settings-profile">
        <div className="settings-section-heading">
          <span className="settings-icon" aria-hidden="true">◉</span>
          <div><h2 id="settings-profile">Profile</h2><p>Keep your research identity up to date.</p></div>
        </div>
        <div className="settings-row">
          <div><strong>{user.name}</strong><p>{user.department || "Add a department"} · {user.email}</p></div>
          <div className="settings-actions">
            <Link className="button secondary" to={`/users/${user.id}`}>View profile</Link>
            <Link className="button" to="/profile/edit">Edit profile</Link>
          </div>
        </div>
      </section>

      <section className="card settings-card" aria-labelledby="settings-appearance">
        <div className="settings-section-heading">
          <span className="settings-icon" aria-hidden="true">◐</span>
          <div><h2 id="settings-appearance">Appearance & accessibility</h2><p>Adjust the reading experience on this device.</p></div>
        </div>
        <div className="settings-control-grid">
          <label>Color theme
            <select value={theme} onChange={(event) => updateAppearance("rc_theme", event.target.value, setTheme)}>
              <option value="light">Light</option><option value="dark">Dark</option>
            </select>
          </label>
          <label>Text size
            <select value={textSize} onChange={(event) => updateAppearance("rc_text_size", event.target.value, setTextSize)}>
              <option value="normal">Standard</option><option value="large">Larger text</option>
            </select>
          </label>
        </div>
        <label className="settings-toggle-row">
          <span><strong>Reduce motion</strong><small>Turn off decorative movement and transitions.</small></span>
          <input type="checkbox" checked={reduceMotion} onChange={(event) => updateAppearance("rc_reduce_motion", String(event.target.checked), setReduceMotion)} />
        </label>
      </section>

      <section className="card settings-card" aria-labelledby="settings-notifications">
        <div className="settings-section-heading">
          <span className="settings-icon" aria-hidden="true">♧</span>
          <div><h2 id="settings-notifications">Notifications</h2><p>Choose the updates you’d like to receive.</p></div>
        </div>
        {NOTIFICATION_OPTIONS.map(([key, title, description]) => (
          <label className="settings-toggle-row" key={key}>
            <span><strong>{title}</strong><small>{description}</small></span>
            <input type="checkbox" checked={notifications[key]} onChange={() => toggleNotification(key)} />
          </label>
        ))}
        <p className="settings-note">These preferences are saved in this browser. In-app notification delivery is not enabled yet.</p>
        {saved && <p className="settings-saved" role="status">{saved}</p>}
      </section>

      <section className="card settings-card" aria-labelledby="settings-privacy">
        <div className="settings-section-heading">
          <span className="settings-icon" aria-hidden="true">◇</span>
          <div><h2 id="settings-privacy">Privacy</h2><p>How profile and activity data currently work.</p></div>
        </div>
        <div className="settings-privacy-item"><strong>Profile visibility</strong><p>Your profile is visible to signed-in ScholarSphere members. Per-profile visibility controls are not available yet.</p></div>
        <div className="settings-privacy-item"><strong>Research activity</strong><p>Searches and interactions help power recommendations and project analytics.</p></div>
      </section>

      <section className="card settings-card" aria-labelledby="settings-account">
        <div className="settings-section-heading">
          <span className="settings-icon" aria-hidden="true">⌘</span>
          <div><h2 id="settings-account">Account & security</h2><p>Manage your sign-in credentials.</p></div>
        </div>
        <form className="settings-password-form" onSubmit={changePassword}>
          <label>Current password<input type="password" autoComplete="current-password" value={password.current_password} onChange={(event) => setPassword({ ...password, current_password: event.target.value })} required /></label>
          <label>New password<input type="password" autoComplete="new-password" minLength={8} value={password.new_password} onChange={(event) => setPassword({ ...password, new_password: event.target.value })} required /><small>Use at least 8 characters.</small></label>
          <label>Confirm new password<input type="password" autoComplete="new-password" minLength={8} value={password.confirm_password} onChange={(event) => setPassword({ ...password, confirm_password: event.target.value })} required /></label>
          {passwordError && <p className="error" role="alert">{passwordError}</p>}
          {passwordMessage && <p className="success" role="status">{passwordMessage}</p>}
          <button type="submit" disabled={passwordBusy}>{passwordBusy ? "Updating…" : "Change password"}</button>
        </form>
        <div className="settings-signout"><div><strong>Sign out</strong><p>End your session on this device.</p></div><button type="button" className="secondary" onClick={signOut}>Log out</button></div>
      </section>

      <section className="card settings-card" aria-labelledby="settings-about">
        <div className="settings-section-heading">
          <span className="settings-icon" aria-hidden="true">✦</span>
          <div><h2 id="settings-about">About ScholarSphere</h2><p>A research community for discovering papers and connecting ideas.</p></div>
        </div>
        <div className="settings-privacy-item"><strong>Chanakya ScholarSphere</strong><p>Research Commons · Version 0.1.0</p></div>
      </section>
    </section>
  );
}
