const STATUS_CLASSES = {
  idle: "bg-gray-100 text-gray-600",
  loading: "bg-indigo-100 text-indigo-700",
  success: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status, message }) {
  if (!message) return null;
  return (
    <div className={`mt-3 rounded-lg px-3 py-2 text-sm font-semibold transition-all ${STATUS_CLASSES[status]}`}>
      <span className="animate-pulse">{message}</span>
    </div>
  );
}
