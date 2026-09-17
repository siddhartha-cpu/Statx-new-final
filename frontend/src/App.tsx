import { Navigate, Route, Routes } from "react-router-dom";
import Assessment from "@/pages/Assessment";
import Auth from "@/pages/Auth";
import Conversations from "@/pages/Conversations";
import Dashboard from "@/pages/Dashboard";
import Layout from "@/pages/Layout";
import ModulePage from "@/pages/ModulePage";
import Providers from "@/pages/Providers";
import Settings from "@/pages/Settings";
import Workspace from "@/pages/Workspace";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Auth />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/app" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="workspace" element={<Workspace />} />
        <Route path="providers" element={<Providers />} />
        <Route path="conversations" element={<Conversations />} />
        <Route path="documents" element={<ModulePage kind="documents" title="Documents" eyebrow="Knowledge layer" description="Keep the references and working material your team returns to." />} />
        <Route path="competency" element={<ModulePage kind="competency" title="Competency" eyebrow="Signal mapping" description="Track capability themes across your work and conversations." />} />
        <Route path="results" element={<ModulePage kind="results" title="Results" eyebrow="Outcome review" description="Review the decisions and outputs your AI workspace is producing." />} />
        <Route path="assessment" element={<Assessment />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}