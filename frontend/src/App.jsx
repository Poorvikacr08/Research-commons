// Which page shows for which URL.
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Navbar from "./components/Navbar.jsx";
import EditProfile from "./pages/EditProfile.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import NewPost from "./pages/NewPost.jsx";
import People from "./pages/People.jsx";
import PostDetail from "./pages/PostDetail.jsx";
import Profile from "./pages/Profile.jsx";
import Register from "./pages/Register.jsx";
import TagPage from "./pages/TagPage.jsx";

// Wrap a page with this to make it "logged-in only".
function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted center">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Protected><Home /></Protected>} />
          <Route path="/people" element={<Protected><People /></Protected>} />
          <Route path="/users/:id" element={<Protected><Profile /></Protected>} />
          <Route path="/profile/edit" element={<Protected><EditProfile /></Protected>} />
          <Route path="/posts/new" element={<Protected><NewPost /></Protected>} />
          <Route path="/posts/:id" element={<Protected><PostDetail /></Protected>} />
          <Route path="/tags/:tag" element={<Protected><TagPage /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
