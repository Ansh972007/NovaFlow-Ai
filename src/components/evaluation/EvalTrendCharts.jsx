"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function shortLabel(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

const COLORS = ["#171717", "#2563eb", "#059669", "#d97706", "#dc2626"];

export function SuiteTrendChart({ points = [] }) {
  const chartData = points.map((p) => ({
    ...p,
    label: shortLabel(p.date),
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-neutral-400">
        Run benchmarks to see pass-rate trends.
      </div>
    );
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "1px solid rgba(0,0,0,0.06)", fontSize: 12 }}
            formatter={(v, name) => [name === "pass_rate" ? `${v}%` : v, name === "pass_rate" ? "Pass rate" : name]}
          />
          <Line type="monotone" dataKey="pass_rate" stroke="#171717" strokeWidth={2} dot={{ r: 3 }} name="pass_rate" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ComparisonTrendChart({ series = [] }) {
  if (!series.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-neutral-400">
        Run comparisons to see assistant trends over time.
      </div>
    );
  }

  const names = new Set();
  series.forEach((row) => {
    (row.assistants || []).forEach((a) => names.add(a.assistant_name || a.assistant_id));
  });
  const assistantNames = [...names].slice(0, 5);

  const chartData = series.map((row) => {
    const point = { label: shortLabel(row.date) };
    assistantNames.forEach((name) => {
      const match = (row.assistants || []).find((a) => (a.assistant_name || a.assistant_id) === name);
      point[name] = match?.pass_rate ?? null;
    });
    return point;
  });

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid rgba(0,0,0,0.06)", fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {assistantNames.map((name, i) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
