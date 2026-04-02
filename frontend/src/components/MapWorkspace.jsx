import { useState, useRef, useEffect } from "react";
import { MapContainer, TileLayer, ZoomControl, GeoJSON, Marker, Tooltip, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

import FileField from "./ui/FileField";
import StatusBadge from "./ui/StatusBadge";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const BASE_MAPS = {
  dark: { name: "Dark Matter", url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" },
  light: { name: "Light Grayscale", url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" },
  satellite: { name: "Satellite Terrain", url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" }
};

function MapEffects({ geoData, utilityData, fitTrigger, selectedRunId }) {
  const map = useMap();
  const lastFitRunId = useRef(null);
  const lastManualTrigger = useRef(fitTrigger);

  useEffect(() => {
    // Only fit if data exists and:
    // 1. Trigger changed (manual fit click)
    // 2. OR this is a new runId that hasn't been fitted yet
    const hasData = (geoData && geoData.features?.length > 0) || (utilityData && utilityData.features?.length > 0);
    if (!hasData) return;

    const isManual = fitTrigger !== lastManualTrigger.current;
    const isNewRun = selectedRunId !== lastFitRunId.current;

    if (isManual) {
      try {
        let bounds = null;
        if (geoData && geoData.features?.length > 0) {
          bounds = L.geoJSON(geoData).getBounds();
        } else if (utilityData && utilityData.features?.length > 0) {
          bounds = L.geoJSON(utilityData).getBounds();
        }

        if (bounds && bounds.isValid()) {
          map.flyToBounds(bounds, { padding: [50, 50], duration: 1.5 });
          lastFitRunId.current = selectedRunId;
          lastManualTrigger.current = fitTrigger;
        }
      } catch (err) {
        console.error("Map flyToBounds failed", err);
      }
    }
  }, [geoData, utilityData, fitTrigger, selectedRunId, map]);

  return null;
}

/* 
  NUCLEAR GLASS RESET - Final kill for Leaflet white boxes 
*/
const GlobalPopupStyles = `
  .leaflet-popup.glass-popup-nuclear .leaflet-popup-content-wrapper,
  .leaflet-popup.glass-popup-nuclear .leaflet-popup-tip {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
  }
  .leaflet-popup.glass-popup-nuclear .leaflet-popup-content {
    margin: 0 !important;
    padding: 0 !important;
    width: 260px !important;
    height: 320px !important;
    background: transparent !important;
  }
  .leaflet-popup.glass-popup-nuclear .leaflet-popup-close-button {
    display: none !important;
  }
  
  /* Flip Card 3D Perfect Logic */
  .risk-card {
    perspective: 2000px;
    width: 260px;
    height: 320px;
    position: relative;
    background: transparent !important;
  }
  .risk-card-inner {
    position: absolute;
    width: 100%;
    height: 100%;
    transition: transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
    transform-style: preserve-3d;
  }
  .risk-card.is-flipped .risk-card-inner {
    transform: rotateY(180deg);
  }
  .card-front, .card-back {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    width: 100%;
    height: 100%;
    backface-visibility: hidden;
    border-radius: 1.5rem;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .card-back {
    transform: rotateY(180deg);
  }
`;

function WeatherLayer({ weatherData }) {
  const [zoom, setZoom] = useState(11);
  const map = useMapEvents({
    zoomend: () => setZoom(map.getZoom())
  });

  if (!weatherData || !Array.isArray(weatherData)) return null;

  const showDiamond = zoom >= 11;
  const offset = 0.04; // ~5km

  return (
    <>
      <style>{GlobalPopupStyles}</style>
      <style>{`
        @keyframes windy-wave {
          0% { transform: skewY(-5deg) scaleX(1); }
          100% { transform: skewY(15deg) scaleX(0.85); }
        }
        @keyframes windy-trail {
          0% { transform: translateX(0); opacity: 0; }
          50% { opacity: 0.6; }
          100% { transform: translateX(20px); opacity: 0; }
        }
        .windy-flag .flag-wave {
          animation: windy-wave 0.8s ease-in-out infinite alternate;
          transform-origin: left center;
        }
        .wind-trails .trail {
          position: absolute;
          background: white;
          height: 1px;
          width: 15px;
          animation: windy-trail 1s linear infinite;
        }
      `}</style>
      
      {weatherData.map((w, idx) => {
        if (!w.red_flag) return null;
        
        const basePoints = [{ lat: w.latitude, lon: w.longitude }];
        if (showDiamond) {
          basePoints.push({ lat: w.latitude + offset, lon: w.longitude });
          basePoints.push({ lat: w.latitude - offset, lon: w.longitude });
          basePoints.push({ lat: w.latitude, lon: w.longitude + offset });
          basePoints.push({ lat: w.latitude, lon: w.longitude - offset });
        }

        return basePoints.map((p, pIdx) => {
          const rotation = (w.wind_direction + 90) % 360;
          const getDir = (d) => ['N','NE','E','SE','S','SW','W','NW'][Math.round(d/45)%8];
          const icon = L.divIcon({
            className: 'weather-icon',
            html: `
              <div class="windy-container" style="transform: rotate(${rotation}deg); transform-origin: 5px 35px; position: relative; width: 40px; height: 40px;">
                <svg class="windy-flag" width="40" height="40" viewBox="0 0 40 40" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
                  <path d="M5 4v32" stroke="#4b5563" stroke-width="2" stroke-linecap="round" />
                  <path class="flag-wave" d="M6 4 l28 7.5 L6 19" fill="${w.red_flag ? '#ef4444' : '#3b82f6'}" />
                </svg>
                <div class="wind-trails" style="position: absolute; top: 10px; left: 20px;">
                  <div class="trail" style="top: 0; animation-delay: ${Math.random()}s"></div>
                  <div class="trail" style="top: 8px; animation-delay: ${Math.random() + 0.5}s"></div>
                </div>
              </div>
            `,
            iconSize: [40, 40],
            iconAnchor: [5, 35]
          });

          return (
            <Marker key={`weather-${idx}-${pIdx}`} position={[p.lat, p.lon]} icon={icon}>
              <Tooltip direction="top" offset={[10, -20]} opacity={1} permanent={false} className="sleek-tooltip">
                <div class="bg-gray-900/90 backdrop-blur-md text-white p-3 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.4)] border border-white/10 min-w-[140px]">
                  <div class="text-[10px] font-black text-red-500 uppercase tracking-widest mb-2 border-b border-white/10 pb-1.5">
                    STATION {idx+1}
                  </div>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] text-gray-400 font-bold uppercase">Wind Speed</span>
                    <span className="font-mono text-sm font-black text-red-400">${w.wind_speed} <small className="text-[9px] opacity-70">km/h</small></span>
                  </div>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] text-gray-400 font-bold uppercase">Bearing</span>
                    <span className="font-mono text-xs font-black text-gray-300 tracking-tighter">${w.wind_direction}° ${getDir(w.wind_direction)}</span>
                  </div>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] text-gray-400 font-bold uppercase">Humid</span>
                    <span className="font-mono text-sm font-black text-blue-400">${w.humidity}%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-gray-400 font-bold uppercase">Temp</span>
                    <span className="font-mono text-sm font-black text-orange-400">${w.temperature}°C</span>
                  </div>
                </div>
                <style>{`
                  .leaflet-tooltip.sleek-tooltip {
                    background: transparent;
                    border: none;
                    box-shadow: none;
                    padding: 0;
                  }
                  .leaflet-tooltip-top.sleek-tooltip::before {
                    border-top-color: rgba(17, 24, 39, 0.9);
                  }
                  /* Tooltip Reset - Shared with Weather and Risk */
                  .leaflet-tooltip.glass-tooltip-wrapper {
                    background: transparent !important;
                    color: white !important;
                    border: none !important;
                    box-shadow: none !important;
                    padding: 0 !important;
                  }
                  .leaflet-tooltip-top.glass-tooltip-wrapper::before {
                    border-top-color: transparent !important;
                  }
                  
                  /* Flip Card CSS - Absolute Perfection */
                  
                  /* Flip Card CSS - Absolute Perfection */
                  .risk-card {
                    perspective: 2000px; /* High perspective for cinematic feel */
                    width: 260px;
                    height: 320px;
                    position: relative;
                  }
                  .risk-card-inner {
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    transition: transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
                    transform-style: preserve-3d;
                  }
                  .risk-card.is-flipped .risk-card-inner {
                    transform: rotateY(180deg);
                  }
                  .card-front, .card-back {
                    position: absolute;
                    top: 0;
                    right: 0;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    backface-visibility: hidden;
                    border-radius: 1.5rem;
                    display: flex;
                    flex-direction: column;
                  }
                  .card-back {
                    transform: rotateY(180deg);
                  }
                `}</style>
              </Tooltip>
            </Marker>
          );
        });
      })}
    </>
  );
}

export default function MapWorkspace({ activeProjectId, activeProjectEntry, setActiveProjectId }) {
  const [redFile, setRedFile] = useState(null);
  const [nirFile, setNirFile] = useState(null);
  const [canopyFile, setCanopyFile] = useState(null);
  const [swirFile, setSwirFile] = useState(null);
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
  const [fitTrigger, setFitTrigger] = useState(0);
  const [weatherData, setWeatherData] = useState(null);

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
        if (riskData.properties) setWeatherData(riskData.properties);
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
            const statusUpper = data.status?.toUpperCase();
            const isDone = ["SUCCESS", "COMPLETED", "FINISHED"].includes(statusUpper);
            const isFailed = ["FAILURE", "FAILED", "CANCELED"].includes(statusUpper);
            
            if (isDone) {
              clearInterval(interval);
              setRunningJobId(null);
              setStatus("success");
              setStatusMsg("✅ Analysis Sequence Finalized!");
              await fetchRuns();
              if (selectedRunId) await loadRunData(selectedRunId);
            } else if (isFailed) {
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
    if (swirFile) formData.append("swir_band", swirFile);

    try {
      const response = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail ?? "Upload failed");
      }
      const data = await response.json();
      
      if (data.dagster?.errors) {
        throw new Error(data.dagster.errors[0]?.message ?? "Unknown GraphQL Error");
      }
      if (data.dagster?.error) {
        throw new Error(data.dagster.error);
      }
      const launchRun = data.dagster?.data?.launchRun;
      if (!launchRun) {
        throw new Error("Dagster API returned no run data.");
      }
      if (launchRun.message) {
        throw new Error("Dagster API Error: " + launchRun.message);
      }
      
      const runId = launchRun.run?.runId;
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
      setRedFile(null); setNirFile(null); setCanopyFile(null); setSwirFile(null); setUtilityFile(null);
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
        <MapEffects geoData={geoData} utilityData={utilityData} fitTrigger={fitTrigger} selectedRunId={selectedRunId} />
        <WeatherLayer weatherData={weatherData} />

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
              const p = feature.properties || {};
              const risk = p.risk_level || 'Unknown';
              const color = risk === 'High' ? '#ef4444' : risk === 'Medium' ? '#f97316' : '#fbbf24';
              
              // Build the "Risk DNA" Dashboard
              const hasDNA = p.ndvi !== undefined;
              const cardId = `card-${feature.id || Math.random()}`;
              
              // Helper to explain the "Why" (Authenticated Pipeline Transcript)
              const getWhy = () => {
                const reasons = [];
                // 1. Base Fuel (NDVI)
                if (p.ndvi > 0.7) reasons.push("Base fuel index is critical (NDVI > 0.7).");
                else if (p.ndvi > 0.5) reasons.push("Significant biomass density detected (NDVI > 0.5).");
                else reasons.push("Base fuel density is currently low (NDVI < 0.5).");

                // 2. Moisture Stress (NDMI)
                if (p.ndmi < 0.1) {
                  reasons.push("Escalated by significant plant desiccation (NDMI < 0.1).");
                }

                // 3. Atmospheric Synergism
                if (p.red_flag_alert) {
                  reasons.push("Atmospheric Red Flag synergistic escalation applied.");
                } else if (p.wind_speed > 30) {
                  reasons.push("Wind-driven risk escalation.");
                }
                
                return reasons.join(" ");
              };

              const content = `
                <div class="risk-card sleek-tooltip" id="${cardId}">
                  <div class="risk-card-inner">
                    <!-- Front: Metrics -->
                    <div class="card-front bg-gray-900/95 backdrop-blur-xl text-white p-5 border border-white/10 shadow-2xl flex flex-col justify-between">
                      <div>
                        <div class="flex justify-between items-center mb-4 border-b border-white/10 pb-2">
                          <span class="text-[10px] font-black uppercase tracking-widest text-red-500">RISK PROFILE</span>
                          <span class="px-2 py-0.5 rounded text-[10px] font-bold text-white shadow-sm" style="background: ${color}">${risk.toUpperCase()}</span>
                        </div>
                        
                        ${hasDNA ? `
                          <div class="grid grid-cols-2 gap-y-3 gap-x-4 mb-4">
                            <div>
                              <div class="text-[9px] uppercase font-black text-gray-500 tracking-tighter mb-0.5">Vegetation/NDVI</div>
                              <div class="text-sm font-mono font-black ${p.ndvi > 0.6 ? 'text-green-400' : 'text-orange-400'}">${p.ndvi.toFixed(3)}</div>
                            </div>
                            <div>
                              <div class="text-[9px] uppercase font-black text-gray-500 tracking-tighter mb-0.5">Moisture/NDMI</div>
                              <div class="text-sm font-mono font-black ${p.ndmi > 0.1 ? 'text-blue-400' : 'text-red-400'}">${p.ndmi.toFixed(3)}</div>
                            </div>
                            <div>
                              <div class="text-[9px] uppercase font-black text-gray-500 tracking-tighter mb-0.5">Local Wind</div>
                              <div class="text-sm font-mono font-black text-red-400">${p.wind_speed || '--'} <small class="text-[9px] opacity-70">km/h</small></div>
                            </div>
                            <div>
                              <div class="text-[9px] uppercase font-black text-gray-500 tracking-tighter mb-0.5">Bearing</div>
                              <div class="text-xs font-mono font-black text-gray-300 tracking-tighter">${p.wind_direction !== undefined ? `${p.wind_direction}° ${['N','NE','E','SE','S','SW','W','NW'][Math.round(p.wind_direction/45)%8]}` : '--'}</div>
                            </div>
                          </div>
                          
                          <div class="bg-white/5 p-3 rounded-xl border border-white/5">
                             <div class="flex justify-between items-center">
                                <span class="text-[9px] font-black uppercase text-gray-400 tracking-widest">Atmos Profile</span>
                                <span class="text-xs font-mono font-black text-gray-300">${p.temp || '--'}°/${p.humidity || '--'}%</span>
                             </div>
                          </div>
                        ` : `
                          <div class="text-[10px] italic text-gray-500 text-center py-10 bg-white/5 rounded-xl border border-dashed border-white/10">Legacy analysis: DNA unavailable</div>
                        `}
                      </div>
                      
                      <div class="pt-3 border-t border-white/5 flex justify-between items-center">
                        <span class="text-[8px] text-gray-600 font-mono tracking-tighter uppercase font-bold">SN: ${feature.id?.slice(0,8) || 'N/A'}</span>
                        <button onclick="document.getElementById('${cardId}').classList.toggle('is-flipped')" class="text-[9px] font-black text-blue-400 hover:text-blue-200 transition-colors uppercase tracking-widest flex items-center gap-1">EXPERT VIEW <svg class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path d="M19 9l-7 7-7-7"/></svg></button>
                      </div>
                    </div>

                    <!-- Back: Qualitative Reasoning -->
                    <div class="card-back bg-gray-900/95 backdrop-blur-xl text-white p-5 border border-white/10 shadow-2xl flex flex-col justify-between">
                      <div>
                        <div class="mb-4 border-b border-white/10 pb-2 flex justify-between items-center">
                          <span class="text-[10px] font-black uppercase tracking-widest text-indigo-400">EXPERT ANALYSIS</span>
                          <button onclick="document.getElementById('${cardId}').classList.toggle('is-flipped')" class="text-[18px] text-gray-500 hover:text-white leading-none">&times;</button>
                        </div>
                        
                        <div>
                          <div class="text-[8px] font-bold text-gray-500 uppercase tracking-widest mb-2 italic">Conclusion Summary:</div>
                          <p class="text-[11px] leading-relaxed text-gray-200">${getWhy()}</p>
                          
                          <div class="mt-4 pt-4 border-t border-white/5">
                             <div class="text-[8px] font-bold text-gray-400 uppercase mb-2">Primary Drivers:</div>
                             <div class="space-y-1.5">
                                ${p.ndvi > 0.6 ? `<div class="flex items-center gap-2 text-[10px]"><span class="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]"></span> Bio-Mass Escalation</div>` : ''}
                                ${p.ndmi < 0.05 ? `<div class="flex items-center gap-2 text-[10px]"><span class="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"></span> Desiccation Stress</div>` : ''}
                                ${p.red_flag_alert ? `<div class="flex items-center gap-2 text-[10px]"><span class="w-1.5 h-1.5 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)]"></span> Wind/Humidity Synergism</div>` : ''}
                             </div>
                          </div>
                        </div>
                      </div>

                      <div class="pt-3 border-t border-white/10 text-center">
                         <span class="text-[9px] font-black text-gray-600 uppercase tracking-widest">GeoFire-Agent v1.2</span>
                      </div>
                    </div>
                  </div>
                </div>
              `;
              layer.bindPopup(content, { 
                maxWidth: 300, 
                className: 'glass-popup-nuclear' 
              });
            }}
          />
        )}

        {/* Global Red Flag Badge Overlay - Dynamic Grid Edition */}
        {weatherData && (Array.isArray(weatherData) ? weatherData.some(w => w.red_flag) : weatherData.red_flag) && (
          <div className="absolute top-6 right-6 z-[1001] animate-bounce">
            <div className="group relative">
              <div className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-full shadow-[0_0_20px_rgba(220,38,38,0.5)] border-2 border-red-400 animate-pulse cursor-help">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="flex flex-col leading-none">
                  <span className="font-black tracking-tighter text-[10px]">REGIONAL</span>
                  <span className="font-black tracking-tighter text-sm">RED FLAG WARNING</span>
                </div>
              </div>
              
              {/* Minimalistic Tooltip - Dynamic Summary */}
              <div className="absolute top-full right-0 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                <div className="bg-gray-900/95 backdrop-blur text-white p-3 rounded-xl shadow-xl border border-gray-700 min-w-[200px]">
                  <div className="flex justify-between items-center mb-2 border-b border-gray-700 pb-1">
                    <div className="text-[10px] uppercase font-bold text-gray-400 tracking-widest">Atmospheric Grid</div>
                    <div className="bg-gray-700 text-[9px] px-1.5 py-0.5 rounded font-mono">{Array.isArray(weatherData) ? weatherData.length : 1} STATIONS</div>
                  </div>
                  
                  {/* Summary Stats */}
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-gray-300">Max Wind Gust</span>
                    <span className="text-sm font-mono font-bold text-red-400">
                      {Array.isArray(weatherData) ? Math.max(...weatherData.map(w => w.wind_speed)).toFixed(1) : weatherData.wind_speed} <small>km/h</small>
                    </span>
                  </div>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-gray-300">Min Humidity</span>
                    <span className="text-sm font-mono font-bold text-blue-400">
                      {Array.isArray(weatherData) ? Math.min(...weatherData.map(w => w.humidity)).toFixed(0) : weatherData.humidity}%
                    </span>
                  </div>
                  <div className="text-[9px] text-gray-500 mt-2 italic text-right">
                    * Showing worst-case regional conditions
                  </div>
                </div>
              </div>
            </div>
          </div>
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
        
        <div className="w-px h-6 bg-gray-200 shadow-sm mr-4 ml-1"></div>
        
        <button onClick={() => setFitTrigger(f => f + 1)} className="px-4 py-1.5 rounded-full text-xs font-bold transition-all border shadow-sm flex items-center gap-2 bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100">
           <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
           FIT TO DATA
        </button>
        
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
                            <FileField id="swir_band" label="SWIR Band (B11/B12, 20m - Optional)" accept=".tif,.tiff,.geotiff,.jp2" file={swirFile} onChange={(e) => setSwirFile(e.target.files[0] ?? null)} />
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
                                            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded shadow-[0_1px_2px_rgba(0,0,0,0.05)] ${(r.status === 'SUCCESS' || r.status === 'COMPLETED') ? 'bg-green-100 text-green-700 border border-green-200' : (r.status === 'RUNNING' || r.status === 'STARTED' || r.status === 'STARTING') ? 'bg-orange-100 text-orange-700 animate-pulse border border-orange-200' : (r.status === 'FAILED' || r.status === 'FAILURE' || r.status === 'ERROR') ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-gray-200 text-gray-600 border border-gray-300'}`}>{r.status}</span>
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
