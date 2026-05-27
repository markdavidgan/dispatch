import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import BriefingsPage from "./pages/BriefingsPage";
import BriefingDetailPage from "./pages/BriefingDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsArchivePage from "./pages/ProjectsArchivePage";
import PodcastsPage from "./pages/PodcastsPage";
import PodcastDetailPage from "./pages/PodcastDetailPage";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminSettingsPage from "./pages/admin/AdminSettingsPage";
import AdminRunsPage from "./pages/admin/AdminRunsPage";
import SetupPage from "./pages/SetupPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Public routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/briefings" element={<BriefingsPage />} />
        <Route path="/briefings/:date" element={<BriefingDetailPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:slug" element={<ProjectDetailPage />} />
        <Route path="/projects/archive" element={<ProjectsArchivePage />} />
        {/* /podcast (singular) is the canonical route — focuses on the
            dispatch-wide weekly. /podcasts/* kept as legacy aliases. */}
        <Route path="/podcast" element={<PodcastsPage />} />
        <Route path="/podcast/:slug" element={<PodcastDetailPage />} />
        <Route path="/podcasts" element={<PodcastsPage />} />
        <Route path="/podcasts/:slug" element={<PodcastDetailPage />} />

        {/* Admin routes */}
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/admin/settings" element={<AdminSettingsPage />} />
        <Route path="/admin/runs" element={<AdminRunsPage />} />

        {/* Setup */}
        <Route path="/setup" element={<SetupPage />} />
      </Route>
    </Routes>
  );
}
