import { Link } from "react-router-dom";

const CAMPUS_IMAGE = "https://chanakyauniversity.edu.in/wp-content/uploads/2024/06/Central-Vista1.jpg";

export default function Welcome() {
  return (
    <section className="welcome-page">
      <div className="welcome-kicker"><span /> CHANAKYA UNIVERSITY · RESEARCH COMMUNITY</div>
      <div className="welcome-grid">
        <div className="welcome-copy">
          <p className="eyebrow">Rooted in ideals · Ascending with ideas</p>
          <h1>Knowledge grows when we share it.</h1>
          <p className="welcome-lede">
            Discover thoughtful research, meet the people behind it, and bring new ideas into conversation.
          </p>
          <div className="welcome-actions">
            <Link className="button" to="/register">Join the community <span aria-hidden="true">↗</span></Link>
            <Link className="welcome-login" to="/login">I already have an account <span aria-hidden="true">→</span></Link>
          </div>
          <div className="welcome-index" aria-label="Community features">
            <div><span>01</span><strong>Discover</strong><small>Research worth reading</small></div>
            <div><span>02</span><strong>Connect</strong><small>Scholars across disciplines</small></div>
            <div><span>03</span><strong>Discuss</strong><small>Ideas in good company</small></div>
          </div>
        </div>
        <figure className="welcome-campus">
          <img
            src={CAMPUS_IMAGE}
            alt="Central campus vista at Chanakya University"
            loading="eager"
            onError={(event) => { event.currentTarget.classList.add("image-unavailable"); }}
          />
          <div className="campus-image-fallback" aria-hidden="true"><span>CU</span></div>
          <figcaption><span>01 / A place for ideas</span><a href="https://chanakyauniversity.edu.in/campus-infrastructure/campus-architecture/" target="_blank" rel="noreferrer">Chanakya University · Global Campus ↗</a></figcaption>
          <span className="campus-seal" aria-hidden="true">ज्ञान<br />विचार<br />कर्म</span>
        </figure>
      </div>
      <div className="welcome-footnote"><span>CHANAKYA SCHOLARSPHERE</span><span>A meeting place for scholarship and community</span></div>
    </section>
  );
}
