import { Navigate, Route, Routes } from "react-router-dom";
import Assignments from "@/pages/Assignments";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import Documents from "@/pages/Documents";
import History from "@/pages/History";
import Layout from "@/pages/Layout";
import Results from "@/pages/Results";
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
        <Route path="providers" element={<Navigate to="/app/workspace" replace />} />
        <Route path="conversations" element={<Navigate to="/app/workspace" replace />} />
        <Route path="documents" element={<Documents />} />
        <Route path="history" element={<History />} />
        <Route path="competency" element={<Navigate to="/app/history" replace />} />
        <Route path="results" element={<Results />} />
        <Route path="assignments" element={<Assignments />} />
        <Route path="assessment" element={<Navigate to="/app/assignments" replace />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}