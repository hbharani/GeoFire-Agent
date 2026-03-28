export default function FileField({ id, label, accept, file, onChange }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
        {label}
      </label>
      <label htmlFor={id} className="flex items-center gap-2 cursor-pointer rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 hover:bg-gray-100 px-3 py-2 transition">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1M12 12V4m0 0L8 8m4-4l4 4" />
        </svg>
        <span className="truncate text-sm text-gray-600">
          {file ? file.name : "Click to browse…"}
        </span>
        <input id={id} type="file" accept={accept} className="sr-only" onChange={onChange} />
      </label>
    </div>
  );
}
