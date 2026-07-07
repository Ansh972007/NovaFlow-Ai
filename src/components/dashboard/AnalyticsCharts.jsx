"use client";

import { memo, useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
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

export default memo(function AnalyticsCharts({ series = [], assistants = [], abRouting = null }) {
  const chartData = useMemo(
    () =>
      (series || []).map((row) => ({
        ...row,
        label: shortDate(row.date),
        total: (row.chat || 0) + (row.workflow_chat || 0) + (row.workflow_run || 0),
      })),
    [series]
  );

  const topApps = useMemo(() => (assistants || []).slice(0, 6), [assistants]);

  const abData = useMemo(
    () =>
      abRouting
        ? [
            { name: "Base model", value: abRouting.base_count || 0, fill: "#171717" },
            { name: "Variant", value: abRouting.variant_count || 0, fill: "#047857" },
          ].filter((d) => d.value > 0)
        : [],
    [abRouting]
  );

  const abTotal = useMemo(
    () => (abRouting?.base_count || 0) + (abRouting?.variant_count || 0),
    [abRouting]
  );

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="workspace-panel rounded-2xl p-5 sm:p-6">
        <p className="workspace-section-label">Activity</p>
        <h3 className="mt-1 text-lg font-semibold tracking-tight">Last 7 days</h3>
        <div className="mt-5 h-56 w-full">
          {chartData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-neutral-400">No activity yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="chatGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#171717" stopOpacity="0.25" />
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
                  dataKey="chat"
                  name="Chat"
                  stackId="1"
                  stroke="#171717"
                  fill="url(#chatGrad)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="workflow_chat"
                  name="Workflow chat"
                  stackId="1"
                  stroke="#047857"
                  fill="#04785722"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="workflow_run"
                  name="Workflow runs"
                  stackId="1"
                  stroke="#0369a1"
                  fill="#0369a122"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="workspace-panel rounded-2xl p-5 sm:p-6">
        <p className="workspace-section-label">Top apps</p>
        <h3 className="mt-1 text-lg font-semibold tracking-tight">Messages by assistant / workflow</h3>
        <div className="mt-5 h-56 w-full">
          {topApps.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-neutral-400">No usage yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topApps} layout="vertical" margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "#737373" }} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={100}
                  tick={{ fontSize: 11, fill: "#525252" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: 12,
                    border: "1px solid rgba(0,0,0,0.06)",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" name="Messages" fill="#171717" radius={[0, 6, 6, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {abRouting && (
        <div className="workspace-panel rounded-2xl p-5 sm:p-6 lg:col-span-2">
          <p className="workspace-section-label">A/B routing</p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight">
            Base vs variant traffic ({abRouting.days || 30} days)
          </h3>
          <div className="mt-5 flex flex-col gap-6 sm:flex-row sm:items-center">
            <div className="h-44 w-full sm:w-56 shrink-0">
              {abTotal === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-neutral-400">
                  No A/B traffic yet — enable variant routing on an assistant
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={abData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={42}
                      outerRadius={68}
                      paddingAngle={2}
                    >
                      {abData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        borderRadius: 12,
                        border: "1px solid rgba(0,0,0,0.06)",
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="grid flex-1 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-black/[0.06] bg-white/50 px-4 py-3">
                <p className="text-2xl font-semibold tabular-nums">{abRouting.base_count || 0}</p>
                <p className="mt-0.5 text-xs font-medium text-neutral-500">Base chats</p>
              </div>
              <div className="rounded-xl border border-black/[0.06] bg-white/50 px-4 py-3">
                <p className="text-2xl font-semibold tabular-nums text-emerald-700">{abRouting.variant_count || 0}</p>
                <p className="mt-0.5 text-xs font-medium text-neutral-500">Variant chats</p>
              </div>
              <div className="rounded-xl border border-black/[0.06] bg-white/50 px-4 py-3">
                <p className="text-2xl font-semibold tabular-nums">{abRouting.variant_pct ?? 0}%</p>
                <p className="mt-0.5 text-xs font-medium text-neutral-500">Variant share</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});
