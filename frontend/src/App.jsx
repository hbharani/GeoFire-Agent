import { useState, useEffect } from "react";
import Dashboard from "./components/Dashboard";
import MapWorkspace from "./components/MapWorkspace";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

export default function App() {
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [newProjectName, setNewProjectName] = useState("");

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch(e) { console.error("Could not fetch projects"); }
  };
  
  useEffect(() => { fetchProjects(); }, []);

  const createProject = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newProjectName })
      });
      if (res.ok) {
        const p = await res.json();
        setNewProjectName("");
        await fetchProjects();
        setActiveProjectId(p.id); // instantly enter project view
      }
    } catch(e) { console.error(e); }
  };

  const deleteProject = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Permanently delete this project and its assets?")) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${id}`, { method: "DELETE" });
      if (res.ok) await fetchProjects();
    } catch(e) { console.error(e); }
  };

  const renameProject = async (id, newName) => {
    if (!newName || newName.trim() === "") return;
    try {
      const res = await fetch(`${API_BASE}/projects/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() })
      });
      if (res.ok) await fetchProjects();
    } catch(e) { console.error(e); }
  };

  if (!activeProjectId) {
    return (
      <Dashboard 
        projects={projects}
        setActiveProjectId={setActiveProjectId}
        createProject={createProject}
        newProjectName={newProjectName}
        setNewProjectName={setNewProjectName}
        renameProject={renameProject}
        deleteProject={deleteProject}
      />
    );
  }

  const activeProjectEntry = projects.find(p => p.id === activeProjectId);

  return (
    <MapWorkspace 
      activeProjectId={activeProjectId}
      activeProjectEntry={activeProjectEntry}
      setActiveProjectId={setActiveProjectId}
    />
  );
}
