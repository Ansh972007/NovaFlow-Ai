"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function shortDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString([], { weekday: "short" });
}

export default function AssistantAnalytics({ analytics }) {
  if (!analytics) return null;

  const chartData = (analytics.series || []).map((row) => ({
    ...row,
    label: shortDate(row.date),
  }));

  return (
    <div className="workspace-panel rounded-[1.75rem] p-6 sm:p-7">
      <p className="workspace-section-label">Analytics</p>
      <h2 className="text-lg font-semibold tracking-tight">Chat activity</h2>
      <p className="mt-1 text-sm text-neutral-500">
        {analytics.total_messages} messages in the last {analytics.days} days
      </p>
      <div className="mt-5 h-48 w-full">
        {chartData.length === 0 || analytics.total_messages === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-neutral-400">
            No chat activity yet — publish and open chat to collect data.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="assistantMsgGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#171717" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="#171717" stopOpacity="0.02" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid rgba(0,0,0,0.06)",
                  fontSize: 12,
                }}
              />
              <Area
                type="monotone"
                dataKey="messages"
                name="Messages"
                stroke="#171717"
                fill="url(#assistantMsgGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
