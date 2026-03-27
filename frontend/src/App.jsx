import { useState, useRef } from "react";
import { MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

// Status badge Tailwind classes keyed by status
const STATUS_CLASSES = {
  idle: "bg-gray-100 text-gray-600",
  loading: "bg-yellow-100 text-yellow-700",
  success: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

function StatusBadge({ status, message }) {
  if (!message) return null;
  return (
    <div
      className={`mt-3 rounded-lg px-3 py-2 text-sm font-medium ${STATUS_CLASSES[status]}`}
    >
      {message}
    </div>
  );
}

function FileField({ id, label, accept, file, onChange }) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1"
      >
        {label}
      </label>
      <label
        htmlFor={id}
        className="flex items-center gap-2 cursor-pointer rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 hover:bg-gray-100 px-3 py-2 transition"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 shrink-0 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1M12 12V4m0 0L8 8m4-4l4 4"
          />
        </svg>
        <span className="truncate text-sm text-gray-600">
          {file ? file.name : "Click to browse…"}
        </span>
        <input
          id={id}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={onChange}
        />
      </label>
    </div>
  );
}

export default function App() {
  const [satelliteFile, setSatelliteFile] = useState(null);
  const [utilityFile, setUtilityFile] = useState(null);
  const [status, setStatus] = useState("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [panelOpen, setPanelOpen] = useState(true);
  const formRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!satelliteFile || !utilityFile) {
      setStatus("error");
      setStatusMsg("Please select both files before submitting.");
      return;
    }

    setStatus("loading");
    setStatusMsg("Uploading files and triggering pipeline…");

    const formData = new FormData();
    formData.append("satellite_image", satelliteFile);
    formData.append("utility_lines", utilityFile);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail ?? "Upload failed");
      }

      const data = await response.json();
      setStatus("success");
      setStatusMsg(`Pipeline triggered! Run: ${data.dagster?.data?.launchRun?.run?.runId ?? "check Dagster UI"}`);
      // Reset form
      setSatelliteFile(null);
      setUtilityFile(null);
      formRef.current?.reset();
    } catch (err) {
      setStatus("error");
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* ------------------------------------------------------------------ */}
      {/* Full-screen Leaflet map                                             */}
      {/* ------------------------------------------------------------------ */}
      <MapContainer
        center={[36.7783, -119.4179]}
        zoom={6}
        zoomControl={false}
        className="absolute inset-0 z-0"
        style={{ width: "100%", height: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
        />
        <ZoomControl position="bottomright" />
      </MapContainer>

      {/* ------------------------------------------------------------------ */}
      {/* Floating control panel                                              */}
      {/* ------------------------------------------------------------------ */}
      <div className="absolute top-4 left-4 z-[1000] w-80 max-w-[calc(100vw-2rem)]">
        {/* Header bar */}
        <div
          className="flex items-center justify-between rounded-t-2xl bg-white px-4 py-3 shadow-lg cursor-pointer select-none"
          onClick={() => setPanelOpen((o) => !o)}
        >
          <div className="flex items-center gap-2">
            {/* flame icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-orange-500"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a9.566 9.566 0 00-1.98-1.71 1 1 0 00-1.57.99C5.85 8.9 5 11.06 5 13a7 7 0 1014 0c0-3.007-1.04-5.47-2.81-7.147a1 1 0 00-.795-.3z"
                clipRule="evenodd"
              />
            </svg>
            <span className="font-bold text-gray-800">GeoFire Agent</span>
          </div>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-4 w-4 text-gray-400 transition-transform ${panelOpen ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        {/* Collapsible body */}
        {panelOpen && (
          <div className="rounded-b-2xl bg-white px-4 pb-4 pt-2 shadow-lg">
            <p className="mb-3 text-xs text-gray-500">
              Upload a satellite image and utility-line file to trigger the
              vegetation &amp; fire-risk analysis pipeline.
            </p>

            <form ref={formRef} onSubmit={handleSubmit} className="flex flex-col gap-3">
              <FileField
                id="satellite"
                label="Satellite Image (GeoTIFF)"
                accept=".tif,.tiff,.geotiff"
                file={satelliteFile}
                onChange={(e) => setSatelliteFile(e.target.files[0] ?? null)}
              />

              <FileField
                id="utility"
                label="Utility Lines (Shapefile .zip / GeoJSON)"
                accept=".zip,.geojson,.json,.shp"
                file={utilityFile}
                onChange={(e) => setUtilityFile(e.target.files[0] ?? null)}
              />

              <button
                type="submit"
                disabled={status === "loading"}
                className="mt-1 w-full rounded-lg bg-orange-500 py-2 text-sm font-semibold text-white shadow hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {status === "loading" ? "Processing…" : "Run Analysis"}
              </button>

              <StatusBadge status={status} message={statusMsg} />
            </form>

            {/* Links to back-end services */}
            <div className="mt-4 flex gap-3 border-t pt-3">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                API Docs
              </a>
              <a
                href="http://localhost:3000"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                Dagster UI
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
