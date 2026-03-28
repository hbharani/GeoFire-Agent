import { useState } from "react";

export default function Dashboard({ projects, setActiveProjectId, createProject, newProjectName, setNewProjectName, renameProject, deleteProject }) {
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editName, setEditName] = useState("");

  const startEdit = (e, p) => {
    e.stopPropagation();
    setEditingProjectId(p.id);
    setEditName(p.name);
  };

  const handleEditSubmit = (e) => {
    e.preventDefault();
    renameProject(editingProjectId, editName);
    setEditingProjectId(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 relative">
      <div className="bg-white max-w-4xl w-full shadow-2xl rounded-3xl overflow-hidden">
        <div className="bg-gray-900 p-8 text-white flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black mb-1">GeoFire Projects</h1>
            <p className="text-gray-400 font-medium">Select a geospatial asset environment or create a new one.</p>
          </div>
          <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-indigo-400 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        
        <div className="p-8">
          <h2 className="text-sm uppercase tracking-widest font-bold text-gray-500 mb-4">Your Deployments</h2>
          {projects.length === 0 ? (
            <div className="text-center p-12 bg-gray-50 rounded-xl border border-dashed border-gray-300">
               <p className="text-gray-500">No projects found. Create one below to deploy the DB workspace.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
              {projects.map(p => (
                <div key={p.id} onClick={() => setActiveProjectId(p.id)} className="group border border-gray-200 rounded-xl p-5 hover:border-indigo-500 hover:shadow-lg cursor-pointer transition-all bg-white relative overflow-hidden flex flex-col justify-between min-h-[140px]">
                  <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div>
                    <h3 className="font-bold text-lg text-gray-800 mb-1 truncate pr-2">{p.name}</h3>
                    <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-1 rounded inline-block">ID: {p.id.slice(0, 8)}</span>
                  </div>
                  <div className="flex gap-2 justify-end opacity-0 group-hover:opacity-100 transition-opacity mt-4 border-t pt-2">
                     <button onClick={(e) => startEdit(e, p)} className="text-xs font-bold text-gray-500 hover:text-indigo-600 px-3 py-1.5 bg-gray-50 hover:bg-indigo-50 rounded transition-colors border shadow-sm">Rename</button>
                     <button onClick={(e) => deleteProject(e, p.id)} className="text-xs font-bold text-red-500 hover:text-white px-3 py-1.5 bg-red-50 hover:bg-red-500 rounded transition-colors border border-red-200 shadow-sm">Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="bg-indigo-50 rounded-xl p-6 border border-indigo-100 mt-6">
            <h3 className="font-bold text-indigo-900 mb-3">Initialize New Workspace</h3>
            <form onSubmit={createProject} className="flex gap-3">
              <input required type="text" placeholder="Project Title (e.g. California North Route)..." value={newProjectName} onChange={e => setNewProjectName(e.target.value)} className="flex-1 px-4 py-3 rounded-lg border border-indigo-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <button type="submit" className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-lg shadow-md transition-colors">Create</button>
            </form>
          </div>
        </div>
      </div>

      {/* Custom Rename Modal */}
      {editingProjectId && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-[2000] p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full animate-in fade-in zoom-in duration-200">
            <h3 className="text-lg font-black text-gray-800 mb-4">Rename Project</h3>
            <form onSubmit={handleEditSubmit} className="flex flex-col gap-4">
              <input 
                autoFocus
                required 
                type="text" 
                value={editName} 
                onChange={(e) => setEditName(e.target.value)} 
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500" 
              />
              <div className="flex justify-end gap-3 mt-2">
                <button type="button" onClick={() => setEditingProjectId(null)} className="px-4 py-2 rounded-lg font-bold text-gray-500 hover:bg-gray-100 transition-colors">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold shadow-md transition-colors">Save Name</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
