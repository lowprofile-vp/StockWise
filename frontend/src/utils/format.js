export function formatMoney(value, currency = "INR") {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return "—";
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      maximumFractionDigits: 2,
    }).format(number);
  } catch {
    return `${currency} ${number.toFixed(2)}`;
  }
}

export function formatQty(value, unit) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return "—";
  const text = Number.isInteger(number)
    ? number.toLocaleString("en-IN")
    : number.toLocaleString("en-IN", { maximumFractionDigits: 3 });
  return unit ? `${text} ${unit}` : text;
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10);
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDays(value) {
  if (value === null || value === undefined || value === "") return "No estimate";
  const number = Number(value);
  if (Number.isNaN(number)) return "No estimate";
  if (number === 0) return "Out now";
  const rounded = Number.isInteger(number) ? number : number.toFixed(1);
  return `${rounded} day${number === 1 ? "" : "s"}`;
}

export function titleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
