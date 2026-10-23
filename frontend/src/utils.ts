// Utility functions
export const API = "http://localhost:8000";

/** Indian number formatting: 2,45,000 */
export function fmtINR(amount: number): string {
  if (amount === undefined || amount === null) return "₹0";
  const neg = amount < 0;
  const abs = Math.abs(amount);
  const [integer, decimal] = abs.toFixed(2).split(".");
  let result = "";
  let n = integer.length;
  if (n <= 3) {
    result = integer;
  } else {
    result = integer.slice(-3);
    let rest = integer.slice(0, -3);
    while (rest.length > 0) {
      result = rest.slice(-2) + "," + result;
      rest = rest.slice(0, -2);
    }
  }
  return `${neg ? "-" : ""}₹${result}.${decimal}`;
}

export function fmtPct(n: number): string {
  return `${n.toFixed(1)}%`;
}

export function fmtDate(d: string): string {
  if (!d) return "";
  const dt = new Date(d);
  return dt.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export const CATEGORY_COLORS: Record<string, string> = {
  Food:          "#F97316",
  Groceries:     "#10B981",
  Transport:     "#06B6D4",
  Shopping:      "#8B5CF6",
  Bills:         "#64748B",
  Rent:          "#EF4444",
  Entertainment: "#EC4899",
  Health:        "#14B8A6",
  EMI:           "#F59E0B",
  Salary:        "#22C55E",
  Transfers:     "#6366F1",
  Other:         "#94A3B8",
};

export const ACCOUNT_ICONS: Record<string, string> = {
  bank:        "🏦",
  card:        "💳",
  wallet:      "👛",
  loan:        "🏠",
  investment:  "📈",
  insurance:   "🛡️",
};
