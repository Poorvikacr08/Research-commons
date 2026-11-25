// Which page shows for which URL.
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Navbar from "./components/Navbar.jsx";
import Admin from "./pages/Admin.jsx";
import Ask from "./pages/Ask.jsx";
import CollectionDetail from "./pages/CollectionDetail.jsx";
import EditProfile from "./pages/EditProfile.jsx";
import Home from "./pages/Home.jsx";
import Library from "./pages/Library.jsx";
import Login from "./pages/Login.jsx";
import NewPost from "./pages/NewPost.jsx";
import PaperDetail from "./pages/PaperDetail.jsx";
import People from "./pages/People.jsx";
import PostDetail from "./pages/PostDetail.jsx";
import Profile from "./pages/Profile.jsx";
import Register from "./pages/Register.jsx";
import Search from "./pages/Search.jsx";
import TagPage from "./pages/TagPage.jsx";
import Welcome from "./pages/Welcome.jsx";

// Wrap a page with this to make it "logged-in only".
function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted center">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={loading ? <p className="muted center">Loading…</p> : user ? <Home /> : <Welcome />} />
          <Route path="/people" element={<Protected><People /></Protected>} />
          <Route path="/users/:id" element={<Protected><Profile /></Protected>} />
          <Route path="/profile/edit" element={<Protected><EditProfile /></Protected>} />
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
      </main>
    </>
  );
}
