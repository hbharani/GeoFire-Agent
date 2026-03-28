import { useState, useRef, useEffect } from "react";
import { MapContainer, TileLayer, ZoomControl, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";

import FileField from "./ui/FileField";
import StatusBadge from "./ui/StatusBadge";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const BASE_MAPS = {
  dark: { name: "Dark Matter", url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" },
  light: { name: "Light Grayscale", url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" },
  satellite: { name: "Satellite Terrain", url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" }
};

function MapEffects({ geoData, utilityData }) {
  const map = useMap();
  useEffect(() => {
    try {
      let bounds = null;
      if (geoData && geoData.features && geoData.features.length > 0) {
        bounds = L.geoJSON(geoData).getBounds();
      } else if (utilityData && utilityData.features && utilityData.features.length > 0) {
        bounds = L.geoJSON(utilityData).getBounds();
      }
      if (bounds && bounds.isValid()) {
        map.flyToBounds(bounds, { padding: [50, 50], duration: 1.5 });
      }
    } catch(e) { console.error("Could not fly to bounds", e) }
  }, [geoData, utilityData, map]);
  return null;
}

export default function MapWorkspace({ activeProjectId, activeProjectEntry, setActiveProjectId }) {
  const [redFile, setRedFile] = useState(null);
  const [nirFile, setNirFile] = useState(null);
  const [canopyFile, setCanopyFile] = useState(null);
  const [utilityFile, setUtilityFile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [panelOpen, setPanelOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("history"); // 'history' or 'upload'
  
  const [geoData, setGeoData] = useState(null);
  const [utilityData, setUtilityData] = useState(null);
  const [loadingResults, setLoadingResults] = useState(false);
  
  const [activeBaseMap, setActiveBaseMap] = useState("dark");
  const [showRisk, setShowRisk] = useState(true);
  const [showLines, setShowLines] = useState(true);

  // History Tracking
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [runningJobId, setRunningJobId] = useState(null);
  
  const formRef = useRef(null);

  const fetchRuns = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects/${activeProjectId}/runs`);
      if (res.ok) {
        const data = await res.json();
        setRuns(data);
        if (data.length > 0 && !selectedRunId) {
          setSelectedRunId(data[0].id);
        }
      }
    } catch (e) { console.error("Could not fetch runs", e); }
  };

  useEffect(() => {
    if (activeProjectId) {
        setSelectedRunId(null);
        fetchRuns();
    }
  }, [activeProjectId]);

  const loadRunData = async (runId) => {
    if (!runId) return;
    setLoadingResults(true);
    setUtilityData(null);
    setGeoData(null);
    try {
      const lineRes = await fetch(`${API_BASE}/runs/${runId}/utility-lines`);
      if (lineRes.ok) {
        const lineData = await lineRes.json();
        if (lineData.features && lineData.features.length > 0) setUtilityData(lineData);
      }
      const riskRes = await fetch(`${API_BASE}/runs/${runId}/results`);
      if (riskRes.ok) {
        const riskData = await riskRes.json();
        if (riskData.features && riskData.features.length > 0) setGeoData(riskData);
      }
    } catch (err) {
      console.error(err.message);
    } finally {
      setLoadingResults(false);
    }
  };

  useEffect(() => {
    if (selectedRunId) loadRunData(selectedRunId);
  }, [selectedRunId]);

  useEffect(() => {
    if (!runningJobId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/status/${runningJobId}?db_run_id=${selectedRunId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "SUCCESS") {
            clearInterval(interval);
            setRunningJobId(null);
            setStatus("success");
            setStatusMsg("✅ Map Generated natively via PostGIS!");
            await fetchRuns();
            await loadRunData(selectedRunId);
          } else if (data.status === "FAILURE" || data.status === "CANCELED") {
            clearInterval(interval);
            setRunningJobId(null);
            setStatus("error");
            setStatusMsg(`❌ Pipeline ${data.status.toLowerCase()}. Check Dagster.`);
            await fetchRuns();
          } else {
            setStatusMsg(`⚙️ Computing Buffer Vector: ${data.status}...`);
          }
        }
      } catch (err) { console.error("Polling error", err); }
    }, 2000);
    return () => clearInterval(interval);
  }, [runningJobId, selectedRunId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeProjectId) return;
    if (!redFile || !nirFile || !utilityFile) {
      setStatus("error"); setStatusMsg("Please select Red, NIR, and Utility files."); return;
    }
    setStatus("loading");
    setStatusMsg("Uploading geometries securely...");

    const formData = new FormData();
    formData.append("project_id", activeProjectId);
    formData.append("red_band", redFile);
    formData.append("nir_band", nirFile);
    formData.append("utility_lines", utilityFile);
    if (canopyFile) formData.append("canopy_height", canopyFile);

    try {
      const response = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail ?? "Upload failed");
      }
      const data = await response.json();
      const runId = data.dagster?.data?.launchRun?.run?.runId;
      const historyRunId = data.run_id;
      
      if (runId) {
        setRunningJobId(runId);
        setSelectedRunId(historyRunId);
        setActiveTab("history"); // Swap back to history viewer automatically
        fetchRuns();
        setStatus("loading");
        setStatusMsg("🚀 Pipeline triggered! Offloading compute to Postgres...");
      } else {
        setStatus("success");
      }
      setRedFile(null); setNirFile(null); setCanopyFile(null); setUtilityFile(null);
      formRef.current?.reset();
    } catch (err) {
      setStatus("error"); setStatusMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <MapContainer center={[33.68, -116.17]} zoom={11} zoomControl={false} className="absolute inset-0 z-0 bg-gray-900" style={{ width: "100%", height: "100%" }}>
        <TileLayer key={activeBaseMap} url={BASE_MAPS[activeBaseMap].url} maxZoom={19} />
        <ZoomControl position="bottomright" />
        <MapEffects geoData={geoData} utilityData={utilityData} />
        
        {showLines && utilityData && (
          <GeoJSON 
            key={`lines-${selectedRunId}-${JSON.stringify(utilityData).length}`} 
            data={utilityData} 
            style={{ color: "#3b82f6", weight: 3, opacity: 0.8, dashArray: "4 4" }}
          />
        )}
        
        {showRisk && geoData && (
          <GeoJSON 
            key={`risk-${selectedRunId}-${JSON.stringify(geoData).length}`} 
            data={geoData} 
            style={(feature) => {
              const risk = feature.properties?.risk_level;
              let color = "#fbbf24";
              if (risk === "Medium") color = "#f97316";
              if (risk === "High") color = "#ef4444";
              return { color: color, weight: 1, fillColor: color, fillOpacity: 0.65 };
            }}
            onEachFeature={(feature, layer) => {
              const risk = feature.properties?.risk_level || 'Unknown';
              layer.bindPopup(`<strong>Risk Level:</strong> <span style="color: ${risk === 'High' ? 'red' : risk === 'Medium' ? 'orange' : 'goldenrod'}">${risk}</span>`);
            }}
          />
        )}
      </MapContainer>

      {/* Main Consolidated Bottom Bar */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1000] flex items-center bg-white/95 backdrop-blur shadow-2xl rounded-full p-1.5 border border-gray-200">
        
        {/* Base Maps Segment */}
        <div className="flex bg-gray-100 rounded-full p-1 border border-gray-200 shadow-inner mr-4">
          {Object.entries(BASE_MAPS).map(([key, map]) => (
            <button key={key} onClick={() => setActiveBaseMap(key)} className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${activeBaseMap === key ? "bg-white text-gray-800 shadow-md"  : "text-gray-500 hover:text-gray-700 hover:bg-gray-200"}`}>
              {map.name}
            </button>
          ))}
        </div>
        
        <div className="w-px h-6 bg-gray-200 shadow-sm mr-4"></div>
        
        {/* Overlays Segment */}
        <div className="flex items-center gap-3 pr-2 pl-2">
          <button onClick={() => setShowLines(!showLines)} className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all border shadow-sm flex items-center gap-2 ${showLines ? "bg-blue-500 text-white border-blue-600" : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"}`}>
            {showLines && <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
            UTILITY NETWORK
          </button>
          <button onClick={() => setShowRisk(!showRisk)} className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all border shadow-sm flex items-center gap-2 ${showRisk ? "bg-orange-500 text-white border-orange-600" : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"}`}>
            {showRisk && <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
            THREAT POLYGONS
          </button>
        </div>
        
      </div>

      <div className="absolute top-4 left-4 z-[1000] w-[350px] max-w-[calc(100vw-2rem)] flex flex-col gap-3">
        
        {/* Main Panel */}
        <div className="bg-white shadow-2xl rounded-2xl flex flex-col border border-gray-100 overflow-hidden">
            <div className={`flex items-center justify-between px-4 py-3 bg-gray-900 text-white cursor-pointer ${panelOpen ? 'border-b border-gray-800' : ''}`} onClick={() => setPanelOpen((o) => !o)}>
                <div className="flex items-center gap-2">
                    <button onClick={(e) => { e.stopPropagation(); setActiveProjectId(null); }} className="mr-1 p-1 rounded hover:bg-gray-700 text-gray-400 transition-colors" title="Back to Dashboard">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" /></svg>
                    </button>
                    <span className="font-extrabold tracking-tight text-lg truncate w-48">{activeProjectEntry?.name}</span>
                </div>
                <svg xmlns="http://www.w3.org/2000/svg" className={`h-4 w-4 text-gray-500 transition-transform ${panelOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
            </div>

            {panelOpen && (
            <div className="flex flex-col bg-white">
                {/* Tabs */}
                <div className="flex border-b border-gray-100 text-xs font-bold tracking-wide uppercase">
                    <button onClick={() => setActiveTab("history")} className={`flex-1 py-3 text-center transition-colors ${activeTab === 'history' ? 'border-b-2 border-indigo-500 text-indigo-700 bg-indigo-50/50' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'}`}>Analysis History</button>
                    <button onClick={() => setActiveTab("upload")} className={`flex-1 py-3 text-center transition-colors ${activeTab === 'upload' ? 'border-b-2 border-indigo-500 text-indigo-700 bg-indigo-50/50' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-50'}`}>New Analysis</button>
                </div>
                
                <div className="px-5 py-4 pb-5">
                    {/* Tab 1: Configuration Upload */}
                    {activeTab === 'upload' && (
                        <form ref={formRef} onSubmit={handleSubmit} className="flex flex-col gap-3">
                            <FileField id="red_band" label="Red Band (B04)" accept=".tif,.tiff,.geotiff,.jp2" file={redFile} onChange={(e) => setRedFile(e.target.files[0] ?? null)} />
                            <FileField id="nir_band" label="NIR Band (B08)" accept=".tif,.tiff,.geotiff,.jp2" file={nirFile} onChange={(e) => setNirFile(e.target.files[0] ?? null)} />
                            <FileField id="canopy" label="Canopy Height (Optional)" accept=".tif,.tiff,.geotiff" file={canopyFile} onChange={(e) => setCanopyFile(e.target.files[0] ?? null)} />
                            <FileField id="utility" label="Infrastructure Network" accept=".zip,.geojson,.json,.shp" file={utilityFile} onChange={(e) => setUtilityFile(e.target.files[0] ?? null)} />
                            <button type="submit" disabled={runningJobId !== null} className="mt-2 w-full rounded-lg bg-indigo-600 py-3 text-sm font-bold text-white shadow-lg  hover:bg-indigo-700 hover:shadow-xl disabled:opacity-50 transition-all cursor-pointer">
                                {runningJobId ? "Pipeline Processing..." : "Launch Analysis Sequence"}
                            </button>
                            <StatusBadge status={status} message={statusMsg} />
                        </form>
                    )}
                    
                    {/* Tab 2: Run History Context Switcher */}
                    {activeTab === 'history' && (
                        <div className="flex flex-col">
                            {runs.length === 0 ? (
                                <div className="text-xs text-center p-3 py-10 bg-gray-50 border border-dashed border-gray-200 rounded-lg text-gray-400">
                                    No runs recorded. Navigate to the tracking tab to launch a sequence.
                                </div>
                            ) : (
                            <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
                                {runs.map(r => (
                                    <div key={r.id} onClick={() => setSelectedRunId(r.id)} className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedRunId === r.id ? 'bg-indigo-50 border-indigo-400 border-l-[6px] shadow-sm' : 'bg-white hover:bg-gray-50 border-gray-200'} flex flex-col`}>
                                        <div className="flex justify-between items-center mb-1">
                                            <span className={`text-xs font-bold truncate mr-2 flex-1 ${selectedRunId === r.id ? 'text-indigo-800' : 'text-gray-700'}`}>{r.name}</span>
                                            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded shadow-[0_1px_2px_rgba(0,0,0,0.05)] ${r.status === 'SUCCESS' ? 'bg-green-100 text-green-700 border border-green-200' : r.status === 'RUNNING' ? 'bg-orange-100 text-orange-700 animate-pulse border border-orange-200' : r.status === 'FAILED' ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-gray-200 text-gray-600 border border-gray-300'}`}>{r.status}</span>
                                        </div>
                                        <div className="text-[10px] text-gray-500 font-mono tracking-tighter">
                                            {new Date(r.created_at).toLocaleDateString()} at {new Date(r.created_at).toLocaleTimeString()}
                                        </div>
                                    </div>
                                ))}
                            </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
            )}
        </div>
      </div>
    </div>
  );
}
