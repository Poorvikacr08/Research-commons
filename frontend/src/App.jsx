// Which page shows for which URL.
import { Navigate, Route, Routes } from "react-router-dom";
import { lazy, Suspense, useEffect } from "react";
import { useAuth } from "./auth.jsx";
import Navbar from "./components/Navbar.jsx";
import ResearchChat from "./components/ResearchChat.jsx";

const Admin = lazy(() => import("./pages/Admin.jsx"));
const Ask = lazy(() => import("./pages/Ask.jsx"));
const CollectionDetail = lazy(() => import("./pages/CollectionDetail.jsx"));
const EditProfile = lazy(() => import("./pages/EditProfile.jsx"));
const Home = lazy(() => import("./pages/Home.jsx"));
const Library = lazy(() => import("./pages/Library.jsx"));
const Login = lazy(() => import("./pages/Login.jsx"));
const NewPost = lazy(() => import("./pages/NewPost.jsx"));
const PaperDetail = lazy(() => import("./pages/PaperDetail.jsx"));
const People = lazy(() => import("./pages/People.jsx"));
const PostDetail = lazy(() => import("./pages/PostDetail.jsx"));
const Profile = lazy(() => import("./pages/Profile.jsx"));
const Register = lazy(() => import("./pages/Register.jsx"));
const Search = lazy(() => import("./pages/Search.jsx"));
const Settings = lazy(() => import("./pages/Settings.jsx"));
const TagPage = lazy(() => import("./pages/TagPage.jsx"));
const Welcome = lazy(() => import("./pages/Welcome.jsx"));

// Wrap a page with this to make it "logged-in only".
function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted center">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  useEffect(() => {
    const theme = localStorage.getItem("rc_theme") || "light";
    const textSize = localStorage.getItem("rc_text_size") || "normal";
    const reduceMotion = localStorage.getItem("rc_reduce_motion") === "true";
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.textSize = textSize;
    document.documentElement.dataset.reduceMotion = String(reduceMotion);
  }, []);
  return (
    <>
      <Navbar />
      <main className="container">
        <Suspense fallback={<p className="muted center">Loading page…</p>}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={loading ? <p className="muted center">Loading…</p> : user ? <Home /> : <Welcome />} />
            <Route path="/people" element={<Protected><People /></Protected>} />
            <Route path="/users/:id" element={<Protected><Profile /></Protected>} />
            <Route path="/profile/edit" element={<Protected><EditProfile /></Protected>} />
            <Route path="/settings" element={<Protected><Settings /></Protected>} />
            <Route path="/posts/new" element={<Protected><NewPost /></Protected>} />
            <Route path="/posts/:id" element={<Protected><PostDetail /></Protected>} />
            <Route path="/tags/:tag" element={<Protected><TagPage /></Protected>} />
            <Route path="/library" element={<Protected><Library /></Protected>} />
            <Route path="/papers/:id" element={<Protected><PaperDetail /></Protected>} />
            <Route path="/collections/:id" element={<Protected><CollectionDetail /></Protected>} />
            <Route path="/search" element={<Protected><Search /></Protected>} />
            <Route path="/ask" element={<Protected><Ask /></Protected>} />
            <Route path="/admin" element={<Protected><Admin /></Protected>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
      {!loading && user && <ResearchChat />}
    </>
  );
}
