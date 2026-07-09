"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import WorkspacePageShell from "@/components/workspace/WorkspacePageShell";
import WorkspaceHero from "@/components/workspace/WorkspaceHero";
import WorkspaceAlert from "@/components/workspace/WorkspaceAlert";
import AnimatedCounter from "@/components/AnimatedCounter";
import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";
import { getUserInfo } from "@/lib/api/auth";
import { listKnowledge } from "@/lib/api/knowledge";
import {
  createWorkflow,
  createWorkflowSchedule,
  deleteWorkflowSchedule,
  listWorkspaceSchedules,
  setWorkflowStatus,
  triggerWorkflowSchedule,
  updateWorkflow,
  updateWorkflowSchedule,
} from "@/lib/api/workflows";

const ease = [0.16, 1, 0.3, 1];
const spring = { type: "spring", stiffness: 420, damping: 34 };

const CRON_PRESETS = [
  { label: "Daily 9:00 UTC", value: "0 9 * * *", hint: "Morning brief" },
  { label: "Weekdays 8:00", value: "0 8 * * 1-5", hint: "Work week" },
  { label: "Monday 10:00", value: "0 10 * * 1", hint: "Weekly roundup" },
  { label: "Hourly", value: "0 * * * *", hint: "High frequency" },
];

const FLOW_STEPS = ["Retrieve", "Summarize", "Deliver"];

function IconGmail({ className = "h-7 w-7" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M22 6.5v11A2.5 2.5 0 0 1 19.5 20h-15A2.5 2.5 0 0 1 2 17.5v-11L12 14.2 22 6.5Z"
      />
      <path
        fill="currentColor"
        fillOpacity="0.35"
        d="M2 6.5 12 14.2 22 6.5 12 3 2 6.5Z"
      />
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
        d="M7.5 14.2V9.8L12 12.8l4.5-3 4.5 3v4.4"
        opacity="0.5"
      />
    </svg>
  );
}

function IconAlert({ className = "h-7 w-7" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M12 2.5 2 20h20L12 2.5Z" />
      <path fill="currentColor" fillOpacity="0.35" d="M12 5.5 5.5 18h13L12 5.5Z" />
      <path fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" d="M12 9v4.5M12 15.5v.5" opacity="0.55" />
    </svg>
  );
}

function IconSlack({ className = "h-7 w-7" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M14.25 10h3.75V6.25a2 2 0 1 0-4 0V10Z" />
      <path fill="currentColor" fillOpacity="0.55" d="M10 14.25H6.25a2 2 0 1 0 4 0V10h-.25Z" />
      <path fill="currentColor" fillOpacity="0.35" d="M10 10H6.25a2 2 0 1 1 4 0v4H10Z" />
      <path fill="currentColor" d="M14.25 14.25H18a2 2 0 1 0-4 0v-3.75H14.25Z" />
      <rect x="9.25" y="9.25" width="5.5" height="5.5" rx="1.25" fill="none" stroke="currentColor" strokeWidth="1.1" opacity="0.45" />
    </svg>
  );
}

function IconTelegram({ className = "h-7 w-7" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path fill="currentColor" d="M22 3 11 14 2 8.5 2 21l4.5-4.5L15 21l7-18Z" />
      <path fill="currentColor" fillOpacity="0.35" d="M22 3 11 14 15 21l7-18Z" />
      <path fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" d="M2 8.5 11 14 22 3" opacity="0.5" />
    </svg>
  );
}

function IconDiscord({ className = "h-7 w-7" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path
        fill="currentColor"
        d="M8.2 16.8c-1.2-.5-2.2-1.2-3-2 0 0-1-3.5-1.2-6.3 0 0 2.5-1.5 6.5-1.5h1c4 0 6.5 1.5 6.5 1.5-.2 2.8-1.2 6.3-1.2 6.3-.8.8-1.8 1.5-3 2l-1.1-1.2a4.2 4.2 0 0 1-3 .8 4.2 4.2 0 0 1-3-.8L8.2 16.8Z"
      />
      <path fill="currentColor" fillOpacity="0.35" d="M9 7.5h6c2.5 0 4 1 4.5 2.5L12 11 7.5 10C8 8.5 9.5 7.5 12 7.5H9Z" />
      <circle cx="9.5" cy="11.2" r="1.3" fill="currentColor" fillOpacity="0.5" />
      <circle cx="14.5" cy="11.2" r="1.3" fill="currentColor" fillOpacity="0.5" />
      <path fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" d="M6.5 18c2 1 4 1.5 5.5 1.5s3.5-.5 5.5-1.5" opacity="0.4" />
    </svg>
  );
}

const DIGEST_TEMPLATES = [
  {
    id: "daily_team_email",
    label: "Daily team email",
    tagline: "Morning standup brief",
    channel: "email",
    badge: "Gmail",
    borderAnim: "gmail",
    innerAnim: "mail",
    Icon: IconGmail,
    subject: "{{subject}}",
    message: "{{output}}",
    defaultName: "Daily knowledge digest",
    defaultCron: "0 9 * * *",
    useFor: ["Standups", "Leadership", "Remote teams"],
    details:
      "Pulls from your knowledge base, drafts a crisp digest with Highlights / Risks / Asks, parses an LLM subject line, and emails your team.",
    previewSubject: "Ops standup — Mar 12",
    previewBody:
      "## Highlights\n• Auth fix shipped\n• Docs refresh live\n\n## Risks\n• None flagged\n\n## Asks\n• Review PR #42 by EOD",
    toLabel: "Recipient email",
    toPlaceholder: "team@company.com",
  },
  {
    id: "ops_incidents_email",
    label: "Incidents digest",
    tagline: "On-call risk briefing",
    channel: "email",
    badge: "Email",
    borderAnim: "pulse",
    innerAnim: "radar",
    Icon: IconAlert,
    subject: "Incidents & risks — {{subject}}",
    message: "{{output}}\n\n---\nNovaFlow automated digest. Escalate in #incidents.",
    defaultName: "Incidents & risks digest",
    defaultCron: "0 8 * * 1-5",
    useFor: ["On-call", "SRE", "Platform"],
    details:
      "Weekday email with a prefixed subject for inbox filters. Surfaces open incidents, owners, and recommended actions.",
    previewSubject: "Incidents & risks — P2 latency spike",
    previewBody:
      "## Open\n• API latency P2 — owner: platform\n\n## Asks\n• Confirm rollback window",
    toLabel: "On-call email",
    toPlaceholder: "oncall@company.com",
  },
  {
    id: "slack_summary",
    label: "Slack summary",
    tagline: "#ops channel pulse",
    channel: "slack",
    badge: "Slack",
    borderAnim: "shimmer",
    innerAnim: "grid",
    Icon: IconSlack,
    subject: "{{subject}}",
    message: "*{{subject}}*\n\n{{output}}\n\n_Powered by NovaFlow_",
    defaultName: "Slack daily summary",
    defaultCron: "0 9 * * 1-5",
    useFor: ["#ops", "#product", "Leadership"],
    details: "Posts mrkdwn-friendly summaries via workspace webhook. Override URL below or use Settings.",
    previewSubject: "Daily product pulse",
    previewBody: "• Feature flag GA\n• Docs shipped\n• Eval suite green",
    toLabel: "Webhook override",
    toPlaceholder: "Optional — uses Settings",
  },
  {
    id: "discord_digest",
    label: "Discord digest",
    tagline: "Community roundup",
    channel: "discord",
    badge: "Discord",
    borderAnim: "trace",
    innerAnim: "wave",
    Icon: IconDiscord,
    subject: "{{subject}}",
    message: "**{{subject}}**\n\n{{output}}",
    defaultName: "Discord knowledge digest",
    defaultCron: "0 10 * * 1",
    useFor: ["Community", "Internal", "Weekly"],
    details: "Monday webhook post with markdown formatting for servers and internal communities.",
    previewSubject: "Weekly knowledge roundup",
    previewBody: "• New handbook section\n• FAQ updates\n• Policy clarifications",
    toLabel: "Webhook URL",
    toPlaceholder: "Optional — uses Settings",
  },
  {
    id: "telegram_digest",
    label: "Telegram digest",
    tagline: "Mobile-first brief",
    channel: "telegram",
    badge: "Telegram",
    borderAnim: "ripple",
    innerAnim: "fly",
    Icon: IconTelegram,
    subject: "{{subject}}",
    message: "{{output}}",
    defaultName: "Telegram digest",
    defaultCron: "0 9 * * *",
    useFor: ["Field teams", "Alerts", "Mobile"],
    details: "Plain-text digest to a Telegram chat. Configure bot token in Settings and set chat ID below.",
    previewSubject: "",
    previewBody: "Highlights\n• RAG retrieval improved\n• Eval suite passed\n• New docs indexed",
    toLabel: "Chat ID",
    toPlaceholder: "-1001234567890",
  },
];

function fmtTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function FlowMini({ active = false }) {
  return (
    <div className="flex items-center gap-1.5">
      {FLOW_STEPS.map((step, i) => (
        <div key={step} className="flex items-center gap-1.5">
          <motion.span
            animate={active ? { scale: [1, 1.08, 1] } : {}}
            transition={{ delay: i * 0.15, duration: 0.5, repeat: active ? Infinity : 0, repeatDelay: 2 }}
            className={`rounded-full px-2 py-0.5 text-[9px] font-semibold tracking-wide uppercase ${
              active ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-500"
            }`}
          >
            {step}
          </motion.span>
          {i < FLOW_STEPS.length - 1 && (
            <span className="text-[10px] text-neutral-300">→</span>
          )}
        </div>
      ))}
    </div>
  );
}

function DevicePreview({ tpl }) {
  const isEmail = tpl.channel === "email";
  const isChat = ["slack", "discord", "telegram"].includes(tpl.channel);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, ease }}
      className="relative mx-auto w-full max-w-sm"
    >
      <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-b from-neutral-200/40 to-transparent blur-2xl" />
      <div className="relative overflow-hidden rounded-[1.35rem] border border-neutral-200/80 bg-white shadow-2xl shadow-black/10">
        <div className="flex items-center gap-2 border-b border-neutral-100 bg-neutral-50 px-4 py-3">
          <div className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-neutral-300" />
          </div>
          <span className="ml-2 text-[11px] font-medium text-neutral-500">
            {isEmail ? "Gmail — Preview" : `${tpl.badge} — Preview`}
          </span>
        </div>

        {isEmail && (
          <div className="border-b border-neutral-100 px-4 py-3">
            <p className="text-[10px] font-semibold tracking-widest text-neutral-400 uppercase">Subject</p>
            <p className="mt-1 text-sm font-semibold text-neutral-900">{tpl.previewSubject}</p>
            <p className="mt-2 text-[11px] text-neutral-400">To: team@company.com</p>
          </div>
        )}

        {isChat && tpl.previewSubject && (
          <div className="border-b border-neutral-200 bg-neutral-100 px-4 py-2.5">
            <p className="text-sm font-bold text-neutral-900">{tpl.previewSubject}</p>
          </div>
        )}

        <div className="max-h-56 overflow-auto p-4">
          <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-neutral-700">
            {tpl.previewBody}
          </pre>
        </div>

        <div className="border-t border-neutral-100 bg-neutral-50 px-4 py-2">
          <p className="text-[10px] text-neutral-400">Live sample — actual content generated at run time</p>
        </div>
      </div>
    </motion.div>
  );
}

function AnimatedBorder({ type, active, uid }) {
  if (!active) return null;

  const r = 21;
  const common = "pointer-events-none absolute inset-0 h-full w-full overflow-visible";

  if (type === "gmail") {
    return (
      <>
        <svg className={common} preserveAspectRatio="none" viewBox="0 0 100 100">
          <rect x="2" y="2" width="96" height="96" rx="14" fill="none" stroke="black" strokeWidth="0.8" strokeOpacity="0.15" />
          <motion.line
            x1="4"
            y1="32"
            x2="96"
            y2="32"
            stroke="black"
            strokeWidth="1.2"
            strokeDasharray="2 5"
            animate={{ strokeDashoffset: [0, -14], opacity: [0.2, 0.75, 0.2] }}
            transition={{ strokeDashoffset: { duration: 1.8, repeat: Infinity, ease: "linear" }, opacity: { duration: 2, repeat: Infinity, ease: "easeInOut" } }}
          />
          <motion.line
            x1="2"
            y1="36"
            x2="2"
            y2="94"
            stroke="black"
            strokeWidth="1"
            strokeDasharray="3 7"
            animate={{ strokeDashoffset: [0, -20] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
          />
          <motion.line
            x1="98"
            y1="36"
            x2="98"
            y2="94"
            stroke="black"
            strokeWidth="1"
            strokeDasharray="3 7"
            animate={{ strokeDashoffset: [0, 20] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
          />
          <motion.rect
            x="2"
            y="2"
            width="96"
            height="96"
            rx="14"
            fill="none"
            stroke="black"
            strokeWidth="2"
            pathLength="1"
            strokeDasharray="0.06 0.94"
            animate={{ strokeDashoffset: [0, -1] }}
            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          />
        </svg>
        <motion.div
          className="pointer-events-none absolute top-3 right-3 flex h-8 w-8 items-center justify-center rounded-full border border-dashed border-black"
          animate={{ rotate: 360, scale: [1, 1.08, 1] }}
          transition={{ rotate: { duration: 8, repeat: Infinity, ease: "linear" }, scale: { duration: 2, repeat: Infinity, ease: "easeInOut" } }}
        >
          <motion.div
            className="h-3 w-3 rounded-full border border-black"
            animate={{ scale: [0.6, 1, 0.6], opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.div>
      </>
    );
  }

  if (type === "march") {
    return (
      <svg className={common} preserveAspectRatio="none">
        <motion.rect
          x="1"
          y="1"
          width="calc(100% - 2px)"
          height="calc(100% - 2px)"
          rx={r}
          fill="none"
          stroke="black"
          strokeWidth="2.5"
          strokeDasharray="14 8"
          animate={{ strokeDashoffset: [0, -44] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
        />
        <motion.rect
          x="4"
          y="4"
          width="calc(100% - 8px)"
          height="calc(100% - 8px)"
          rx={r - 2}
          fill="none"
          stroke="black"
          strokeWidth="1"
          strokeOpacity="0.25"
          strokeDasharray="4 18"
          animate={{ strokeDashoffset: [0, 44] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "linear" }}
        />
        {[0, 1, 2, 3].map((corner) => (
          <motion.path
            key={corner}
            d={
              corner === 0
                ? "M8 2h6M2 8v6"
                : corner === 1
                  ? "M34 2h6M42 8v6"
                  : corner === 2
                    ? "M2 34v6h6"
                    : "M42 34v6h-6"
            }
            fill="none"
            stroke="black"
            strokeWidth="2"
            strokeLinecap="round"
            animate={{ opacity: [0.15, 1, 0.15], pathLength: [0.3, 1, 0.3] }}
            transition={{ duration: 1.6, repeat: Infinity, delay: corner * 0.35, ease: "easeInOut" }}
          />
        ))}
      </svg>
    );
  }

  if (type === "pulse") {
    return (
      <>
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="pointer-events-none absolute inset-0 rounded-[1.35rem] border border-black"
            animate={{ opacity: [0.55, 0], scale: [1, 1.035 + i * 0.01] }}
            transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.55, ease: "easeOut" }}
          />
        ))}
        <svg className={common} preserveAspectRatio="none">
          <motion.rect
            x="1.5"
            y="1.5"
            width="calc(100% - 3px)"
            height="calc(100% - 3px)"
            rx={r}
            fill="none"
            stroke="black"
            strokeWidth="2"
            animate={{ strokeOpacity: [0.35, 1, 0.35] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.path
            d="M0 14 Q40 6 80 18 T160 12 T240 16"
            fill="none"
            stroke="black"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
            style={{ transform: "scale(0.45) translate(4px, 0)" }}
            pathLength="1"
            strokeDasharray="0.08 0.92"
            animate={{ strokeDashoffset: [0, -1], opacity: [0.2, 0.9, 0.2] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
        </svg>
      </>
    );
  }

  if (type === "shimmer") {
    return (
      <svg className={common} preserveAspectRatio="none">
        <defs>
          <linearGradient id={`shimmer-${uid}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="black" stopOpacity="0.08" />
            <stop offset="45%" stopColor="black" stopOpacity="1" />
            <stop offset="55%" stopColor="black" stopOpacity="1" />
            <stop offset="100%" stopColor="black" stopOpacity="0.08" />
          </linearGradient>
        </defs>
        <rect x="1.5" y="1.5" width="calc(100% - 3px)" height="calc(100% - 3px)" rx={r} fill="none" stroke="black" strokeWidth="1" strokeOpacity="0.12" />
        <motion.rect
          x="1.5"
          y="1.5"
          width="calc(100% - 3px)"
          height="calc(100% - 3px)"
          rx={r}
          fill="none"
          stroke={`url(#shimmer-${uid})`}
          strokeWidth="3"
          strokeDasharray="60 200"
          animate={{ strokeDashoffset: [0, -260] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
        />
        <motion.rect
          x="1.5"
          y="1.5"
          width="calc(100% - 3px)"
          height="calc(100% - 3px)"
          rx={r}
          fill="none"
          stroke="black"
          strokeWidth="1.5"
          strokeDasharray="2 10"
          animate={{ strokeDashoffset: [0, -48] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    );
  }

  if (type === "trace") {
    return (
      <svg className={common} preserveAspectRatio="none">
        <rect x="1.5" y="1.5" width="calc(100% - 3px)" height="calc(100% - 3px)" rx={r} fill="none" stroke="black" strokeWidth="1" strokeOpacity="0.12" />
        {[0, 0.35, 0.65].map((offset, idx) => (
          <motion.rect
            key={offset}
            x="1.5"
            y="1.5"
            width="calc(100% - 3px)"
            height="calc(100% - 3px)"
            rx={r}
            fill="none"
            stroke="black"
            strokeWidth={idx === 0 ? 3 : 1.5}
            strokeOpacity={idx === 0 ? 1 : 0.35}
            pathLength="1"
            strokeDasharray={idx === 0 ? "0.1 0.9" : "0.04 0.96"}
            animate={{ strokeDashoffset: [offset, offset - 1] }}
            transition={{ duration: 2.2 + idx * 0.4, repeat: Infinity, ease: "linear" }}
          />
        ))}
      </svg>
    );
  }

  if (type === "ripple") {
    return (
      <>
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="pointer-events-none absolute inset-0 rounded-[1.35rem] border-2 border-black"
            animate={{ opacity: [0.7, 0], scale: [1, 1.05 + i * 0.008] }}
            transition={{ duration: 2.8, repeat: Infinity, delay: i * 0.55, ease: [0.16, 1, 0.3, 1] }}
          />
        ))}
        <svg className={common} preserveAspectRatio="none">
          <motion.rect
            x="1.5"
            y="1.5"
            width="calc(100% - 3px)"
            height="calc(100% - 3px)"
            rx={r}
            fill="none"
            stroke="black"
            strokeWidth="2"
            strokeDasharray="1 7"
            animate={{ strokeDashoffset: [0, -32], rotate: [0, 360] }}
            transition={{ strokeDashoffset: { duration: 3, repeat: Infinity, ease: "linear" }, rotate: { duration: 12, repeat: Infinity, ease: "linear" } }}
            style={{ transformOrigin: "center" }}
          />
        </svg>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <motion.div
            key={`dot-${i}`}
            className="pointer-events-none absolute h-1.5 w-1.5 rounded-full bg-black"
            style={{ top: "50%", left: "50%" }}
            animate={{
              x: [0, Math.cos((i / 6) * Math.PI * 2) * 80],
              y: [0, Math.sin((i / 6) * Math.PI * 2) * 28],
              opacity: [0, 1, 0],
              scale: [0.5, 1.2, 0.5],
            }}
            transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.2, ease: "easeInOut" }}
          />
        ))}
      </>
    );
  }

  return null;
}

function InnerDecor({ type, active }) {
  if (!active) {
    return <div className="h-14 flex-1" />;
  }

  if (type === "mail") {
    return (
      <div className="relative h-14 flex-1 overflow-hidden">
        <motion.div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage: "repeating-linear-gradient(90deg, black 0, black 1px, transparent 1px, transparent 12px)",
          }}
          animate={{ x: [0, 12] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute flex items-center gap-1.5"
            style={{ top: 10 + i * 15 }}
            animate={{ x: [-60, 120], opacity: [0, 1, 1, 0] }}
            transition={{ duration: 3.2, repeat: Infinity, delay: i * 0.9, ease: "easeInOut" }}
          >
            <svg className="h-3.5 w-3.5 shrink-0 text-black" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22 6.5v11A2.5 2.5 0 0 1 19.5 20h-15A2.5 2.5 0 0 1 2 17.5v-11L12 14.2 22 6.5Z" />
            </svg>
            <motion.div
              className="h-1.5 rounded-full bg-black"
              animate={{ width: [24, 56, 40] }}
              transition={{ duration: 3.2, repeat: Infinity, delay: i * 0.9, ease: "easeInOut" }}
            />
          </motion.div>
        ))}
        <motion.div
          className="absolute right-6 bottom-2 h-3 w-0.5 bg-black"
          animate={{ opacity: [0, 1, 0], scaleY: [0.4, 1, 0.4] }}
          transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    );
  }

  if (type === "radar") {
    return (
      <div className="relative flex h-14 flex-1 items-center justify-center overflow-hidden">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full border border-black"
            style={{ width: 12 + i * 14, height: 12 + i * 14 }}
            animate={{ scale: [0.5, 1.8], opacity: [0.8, 0] }}
            transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.45, ease: "easeOut" }}
          />
        ))}
        <motion.div
          className="absolute h-10 w-0.5 origin-bottom bg-gradient-to-t from-black to-transparent"
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
        <div className="relative z-10 h-2 w-2 rounded-full bg-black" />
        {[
          { x: 28, y: -8, d: 0 },
          { x: -32, y: 4, d: 0.6 },
          { x: 18, y: 12, d: 1.2 },
        ].map((blip) => (
          <motion.div
            key={`${blip.x}-${blip.y}`}
            className="absolute h-1.5 w-1.5 rounded-full bg-black"
            style={{ left: "50%", top: "50%" }}
            animate={{
              x: [0, blip.x],
              y: [0, blip.y],
              opacity: [0, 1, 0],
              scale: [0, 1.5, 0],
            }}
            transition={{ duration: 2, repeat: Infinity, delay: blip.d, ease: "easeOut" }}
          />
        ))}
      </div>
    );
  }

  if (type === "grid") {
    const cells = Array.from({ length: 12 });
    return (
      <div className="relative h-14 flex-1 overflow-hidden px-1">
        <div className="grid h-full grid-cols-6 grid-rows-2 gap-1">
          {cells.map((_, i) => (
            <motion.div
              key={i}
              className="rounded-sm border border-black/20"
              animate={{
                backgroundColor: ["rgba(0,0,0,0)", "rgba(0,0,0,0.85)", "rgba(0,0,0,0)"],
                scale: [0.7, 1, 0.7],
                borderColor: ["rgba(0,0,0,0.1)", "rgba(0,0,0,0.9)", "rgba(0,0,0,0.1)"],
              }}
              transition={{ duration: 1.8, repeat: Infinity, delay: (i % 6) * 0.1 + Math.floor(i / 6) * 0.25, ease: "easeInOut" }}
            />
          ))}
        </div>
        <motion.div
          className="pointer-events-none absolute inset-0"
          animate={{ opacity: [0, 0.15, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          style={{
            background: "linear-gradient(180deg, transparent, black 50%, transparent)",
            backgroundSize: "100% 200%",
          }}
        />
      </div>
    );
  }

  if (type === "wave") {
    const bars = [0.35, 0.55, 0.85, 1, 0.7, 0.9, 0.5, 0.75, 0.6];
    return (
      <div className="relative flex h-14 flex-1 flex-col justify-end overflow-hidden px-1 pb-1">
        <svg className="absolute inset-x-2 top-2 h-6 w-[calc(100%-16px)]" viewBox="0 0 200 24" preserveAspectRatio="none">
          <motion.path
            d="M0 12 Q25 4 50 12 T100 12 T150 12 T200 12"
            fill="none"
            stroke="black"
            strokeWidth="1.5"
            strokeOpacity="0.35"
            animate={{ d: ["M0 12 Q25 4 50 12 T100 12 T150 20 T200 12", "M0 12 Q25 20 50 12 T100 12 T150 4 T200 12", "M0 12 Q25 4 50 12 T100 12 T150 20 T200 12"] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          />
        </svg>
        <div className="flex items-end gap-0.5">
          {bars.map((h, i) => (
            <motion.div
              key={i}
              className="flex-1 rounded-full bg-black"
              style={{ height: `${h * 18}px` }}
              animate={{ scaleY: [0.25, 1, 0.35], opacity: [0.3, 1, 0.4] }}
              transition={{ duration: 0.7 + (i % 3) * 0.15, repeat: Infinity, delay: i * 0.07, ease: "easeInOut" }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (type === "fly") {
    return (
      <div className="relative h-14 flex-1 overflow-hidden">
        <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
          <motion.path
            d="M 8 28 Q 60 8 120 28"
            fill="none"
            stroke="black"
            strokeWidth="1"
            strokeDasharray="3 6"
            strokeOpacity="0.2"
            animate={{ pathLength: [0, 1], opacity: [0.1, 0.4, 0.1] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
        </svg>
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.div
            key={i}
            className="absolute top-1/2 h-px w-3 bg-black"
            animate={{ x: [-10, 130], opacity: [0, 0.6, 0], scaleX: [0.5, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.22, ease: "easeOut" }}
          />
        ))}
        <motion.div
          className="absolute top-1/2"
          animate={{
            x: [0, 40, 80, 120, 80, 40, 0],
            y: [0, -10, -4, 0, 4, 10, 0],
            rotate: [0, -8, 0, 8, 0, -8, 0],
          }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <svg className="h-5 w-5 text-black drop-shadow-sm" viewBox="0 0 24 24" fill="currentColor">
            <path d="M22 3 11 14 2 8.5 2 21l4.5-4.5L15 21l7-18Z" />
          </svg>
          <motion.div
            className="absolute -right-3 top-1/2 h-1 w-6 -translate-y-1/2 rounded-full bg-black/30 blur-[1px]"
            animate={{ scaleX: [0.3, 1.2, 0.3], opacity: [0.2, 0.7, 0.2] }}
            transition={{ duration: 0.6, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.div>
      </div>
    );
  }

  return <div className="h-14 flex-1" />;
}

function TemplateCard({ tpl, active, onSelect, index, reducedMotion }) {
  const Icon = tpl.Icon;
  return (
    <motion.button
      type="button"
      layout
      layoutId={`digest-tpl-${tpl.id}`}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: reducedMotion ? 0 : index * 0.06, duration: 0.5, ease }}
      whileHover={reducedMotion ? {} : { y: -4, transition: { duration: 0.25 } }}
      whileTap={{ scale: 0.985 }}
      onClick={() => onSelect(tpl)}
      className={`noise group relative w-full overflow-hidden rounded-[1.35rem] border bg-white text-left transition-shadow duration-500 ${
        active
          ? "border-transparent shadow-[0_16px_48px_-20px_rgba(0,0,0,0.35)]"
          : "border-neutral-200 hover:border-neutral-400 hover:shadow-lg hover:shadow-black/5"
      }`}
    >
      {!reducedMotion && <AnimatedBorder type={tpl.borderAnim} active={active} uid={tpl.id} />}

      <div className="relative p-5 sm:p-6">
        <div className="flex items-center gap-3">
          <motion.div
            layout
            className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border-2 transition-colors ${
              active ? "border-black bg-neutral-50 text-black" : "border-neutral-200 bg-white text-neutral-900"
            }`}
          >
            <Icon />
          </motion.div>

          <InnerDecor type={tpl.innerAnim} active={active && !reducedMotion} />

          <span
            className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[0.14em] uppercase ${
              active ? "border-black bg-black text-white" : "border-neutral-300 bg-white text-neutral-600"
            }`}
          >
            {tpl.badge}
          </span>
        </div>

        <h3 className="mt-5 font-serif text-xl tracking-tight text-neutral-900">{tpl.label}</h3>
        <p className="mt-1 text-sm text-neutral-500">{tpl.tagline}</p>

        <div className="mt-4">
          <FlowMini active={active} />
        </div>

        <div className="mt-4 flex flex-wrap gap-1.5">
          {tpl.useFor.map((tag) => (
            <span
              key={tag}
              className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                active ? "border-black/20 bg-neutral-100 text-neutral-800" : "border-transparent bg-neutral-100 text-neutral-600"
              }`}
            >
              {tag}
            </span>
          ))}
        </div>

        <motion.p
          className={`mt-5 text-xs font-semibold tracking-wide uppercase ${
            active ? "text-black" : "text-neutral-400 opacity-0 transition-opacity group-hover:opacity-100"
          }`}
        >
          {active ? "Selected — configure below" : "Tap to configure →"}
        </motion.p>
      </div>
    </motion.button>
  );
}

export default function DigestsClient() {
  const router = useRouter();
  const reducedMotion = useReducedMotion();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [schedules, setSchedules] = useState([]);
  const [kbs, setKbs] = useState([]);
  const [step, setStep] = useState(0);

  const [selectedId, setSelectedId] = useState(null);
  const [digestName, setDigestName] = useState("");
  const [digestCron, setDigestCron] = useState("0 9 * * *");
  const [digestTo, setDigestTo] = useState("");
  const [digestKb, setDigestKb] = useState("");
  const [digestSubject, setDigestSubject] = useState("{{subject}}");
  const [digestMessage, setDigestMessage] = useState("{{output}}");

  const selected = useMemo(
    () => DIGEST_TEMPLATES.find((t) => t.id === selectedId) || null,
    [selectedId]
  );

  const steps = ["Template", "Source", "Delivery", "Schedule"];

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rows, libraries] = await Promise.all([
        listWorkspaceSchedules().catch(() => []),
        listKnowledge({ pageSize: 100 }).catch(() => ({ data: [] })),
      ]);
      setSchedules(Array.isArray(rows) ? rows : []);
      const list = Array.isArray(libraries) ? libraries : libraries?.data || [];
      setKbs(list);
      setDigestKb((prev) => prev || (list[0]?.id ? String(list[0].id) : ""));
    } catch (err) {
      setError(err.message || "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getUserInfo()
      .then((u) => {
        if (!u) {
          router.replace("/login");
          return;
        }
        setUser(u);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  function selectTemplate(tpl) {
    if (selectedId === tpl.id) {
      setSelectedId(null);
      setStep(0);
      return;
    }
    setSelectedId(tpl.id);
    setDigestName(tpl.defaultName || tpl.label);
    setDigestCron(tpl.defaultCron || "0 9 * * *");
    setDigestSubject(tpl.subject || "{{subject}}");
    setDigestMessage(tpl.message || "{{output}}");
    setDigestTo("");
    setStep(1);
    setError("");
    setMsg("");
    setTimeout(() => {
      document.getElementById("digest-studio")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 120);
  }

  async function handleToggle(row) {
    setBusy(true);
    setError("");
    try {
      await updateWorkflowSchedule(row.id, { enabled: !row.enabled });
      await load();
      setMsg(row.enabled ? "Schedule paused." : "Schedule enabled.");
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleTrigger(row) {
    setBusy(true);
    setError("");
    try {
      await triggerWorkflowSchedule(row.id);
      await load();
      setMsg(`Triggered “${row.workflow_name || row.workflow_id}”.`);
    } catch (err) {
      setError(err.message || "Trigger failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(row) {
    if (!window.confirm("Delete this schedule?")) return;
    setBusy(true);
    try {
      await deleteWorkflowSchedule(row.id);
      await load();
      setMsg("Schedule deleted.");
    } catch (err) {
      setError(err.message || "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateDigest(e) {
    e.preventDefault();
    if (!selected) {
      setError("Pick a digest template first.");
      return;
    }
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const wf = await createWorkflow({
        name: digestName.trim() || selected.defaultName || "Daily digest",
        desc: `Scheduled ${selected.label} from Digests hub`,
        templateId: "daily_digest",
      });
      const graph = wf?.graph;
      if (graph?.nodes) {
        const nodes = graph.nodes.map((n) => {
          if (n.type === "retrieve" && digestKb) {
            return { ...n, data: { ...n.data, knowledge_id: Number(digestKb) } };
          }
          if (n.type === "notify") {
            return {
              ...n,
              data: {
                ...n.data,
                channel: selected.channel,
                to: digestTo.trim() || n.data?.to || "",
                subject: digestSubject.trim() || selected.subject || "{{subject}}",
                message: digestMessage.trim() || selected.message || "{{output}}",
              },
            };
          }
          return n;
        });
        await updateWorkflow({
          id: wf.id,
          name: wf.name,
          desc: wf.desc || "",
          graph: { ...graph, nodes },
        });
      }
      await setWorkflowStatus(wf.id, 1);
      await createWorkflowSchedule(wf.id, {
        cron_expression: digestCron,
        input_text: `${selected.label} run`,
        enabled: true,
      });
      setMsg("Digest workflow published and scheduled.");
      await load();
      router.push(`/workflows/${wf.id}`);
    } catch (err) {
      setError(err.message || "Could not create digest");
    } finally {
      setBusy(false);
    }
  }

  const enabledCount = schedules.filter((s) => s.enabled).length;
  const upcoming = schedules.filter((s) => s.enabled && s.next_run_at).length;

  return (
    <WorkspacePageShell user={user} loading={loading || !user} loadingMessage="Loading digests…" maxWidth="max-w-7xl">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        <WorkspaceHero
          eyebrow="Automation studio"
          title="Scheduled"
          titleHighlight="digests"
          description="Pick a delivery template, connect your knowledge, and ship cron-powered summaries to email or chat — in minutes."
          badge={
            <span className="workspace-badge-live inline-flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-neutral-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-neutral-900" />
              </span>
              {DIGEST_TEMPLATES.length} templates ready
            </span>
          }
        />

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5, ease }}
          className="mt-8 grid gap-4 sm:grid-cols-3"
        >
          <WorkspaceStatCard
            label="Schedules"
            value={<AnimatedCounter value={String(schedules.length)} />}
            hint="Across workspace"
          />
          <WorkspaceStatCard
            label="Enabled"
            value={<AnimatedCounter value={String(enabledCount)} />}
            hint="Active crons"
          />
          <WorkspaceStatCard
            label="Upcoming"
            value={<AnimatedCounter value={String(upcoming)} />}
            hint="Next 7 days"
          />
        </motion.div>

        <AnimatePresence mode="wait">
          {(error || msg) && (
            <motion.div
              key={error ? "e" : "m"}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-6 overflow-hidden"
            >
              <WorkspaceAlert type={error ? "error" : "success"}>{error || msg}</WorkspaceAlert>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Template gallery */}
        <section className="mt-12">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, ease }}
            className="mb-6 flex flex-wrap items-end justify-between gap-4"
          >
            <div>
              <p className="workspace-section-label">Step 1</p>
              <h2 className="mt-1 font-serif text-2xl tracking-tight text-neutral-900 sm:text-3xl">
                Choose your template
              </h2>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-neutral-500">
                Each card ships a full workflow — retrieve, summarize, and deliver. Click to open the configuration studio.
              </p>
            </div>
          </motion.div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {DIGEST_TEMPLATES.map((tpl, i) => (
              <TemplateCard
                key={tpl.id}
                tpl={tpl}
                index={i}
                active={tpl.id === selectedId}
                onSelect={selectTemplate}
                reducedMotion={reducedMotion}
              />
            ))}
          </div>
        </section>

        {/* Configuration studio */}
        <AnimatePresence>
          {selected && (
            <motion.section
              id="digest-studio"
              key={selected.id}
              initial={{ opacity: 0, y: 32 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ duration: 0.5, ease }}
              className="mt-12"
            >
              <div className="workspace-panel noise overflow-hidden rounded-[1.75rem]">
                {/* Studio header */}
                <div className="border-b border-black/[0.06] bg-gradient-to-r from-neutral-50 to-white px-6 py-5 sm:px-8">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-900 text-white shadow-lg">
                        <selected.Icon className="h-6 w-6" />
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold tracking-[0.16em] text-neutral-400 uppercase">
                          Configuration studio
                        </p>
                        <h3 className="font-serif text-xl tracking-tight">{selected.label}</h3>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedId(null);
                        setStep(0);
                      }}
                      className="workspace-btn-ghost text-xs"
                    >
                      Close studio
                    </button>
                  </div>

                  {/* Step progress */}
                  <div className="mt-6 flex flex-wrap gap-2">
                    {steps.map((label, i) => (
                      <button
                        key={label}
                        type="button"
                        onClick={() => setStep(i)}
                        className={`relative overflow-hidden rounded-full px-4 py-2 text-xs font-semibold transition ${
                          step === i
                            ? "bg-neutral-900 text-white shadow-md"
                            : step > i
                              ? "bg-neutral-200 text-neutral-700"
                              : "bg-neutral-100 text-neutral-500 hover:bg-neutral-200"
                        }`}
                      >
                        <span className="relative z-10">
                          {i + 1}. {label}
                        </span>
                        {step === i && (
                          <motion.span
                            layoutId="digest-step-glow"
                            className="absolute inset-0 bg-neutral-900"
                            transition={spring}
                          />
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                <form onSubmit={handleCreateDigest} className="grid lg:grid-cols-[1fr_minmax(280px,360px)]">
                  <div className="p-6 sm:p-8">
                    <AnimatePresence mode="wait">
                      {step === 0 && (
                        <motion.div
                          key="s0"
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 12 }}
                          transition={{ duration: 0.3 }}
                          className="space-y-4"
                        >
                          <p className="text-sm leading-relaxed text-neutral-600">{selected.details}</p>
                          <FlowMini />
                          <div className="flex flex-wrap gap-2">
                            {selected.useFor.map((t) => (
                              <span key={t} className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700">
                                {t}
                              </span>
                            ))}
                          </div>
                          <button type="button" onClick={() => setStep(1)} className="btn-primary mt-4">
                            Continue to source →
                          </button>
                        </motion.div>
                      )}

                      {step === 1 && (
                        <motion.div
                          key="s1"
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 12 }}
                          className="space-y-5"
                        >
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-700">Digest name</span>
                            <input
                              value={digestName}
                              onChange={(e) => setDigestName(e.target.value)}
                              className="input-field mt-2 w-full"
                              required
                            />
                          </label>
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-700">Knowledge base</span>
                            <select
                              value={digestKb}
                              onChange={(e) => setDigestKb(e.target.value)}
                              className="input-field mt-2 w-full"
                            >
                              <option value="">None — generic digest</option>
                              {kbs.map((kb) => (
                                <option key={kb.id} value={kb.id}>
                                  {kb.name || `KB #${kb.id}`}
                                </option>
                              ))}
                            </select>
                            <p className="mt-2 text-[11px] text-neutral-400">
                              Grounded summaries pull from indexed documents in this library.
                            </p>
                          </label>
                          <div className="flex gap-3">
                            <button type="button" onClick={() => setStep(0)} className="workspace-btn-ghost">
                              Back
                            </button>
                            <button type="button" onClick={() => setStep(2)} className="btn-primary">
                              Delivery →
                            </button>
                          </div>
                        </motion.div>
                      )}

                      {step === 2 && (
                        <motion.div
                          key="s2"
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 12 }}
                          className="space-y-5"
                        >
                          <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                            <p className="text-xs font-semibold text-neutral-800">Channel: {selected.badge}</p>
                            <p className="mt-1 text-[11px] text-neutral-500">
                              Connectors in Settings → Integrations. Override destination below if needed.
                            </p>
                          </div>
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-700">{selected.toLabel}</span>
                            <input
                              value={digestTo}
                              onChange={(e) => setDigestTo(e.target.value)}
                              placeholder={selected.toPlaceholder}
                              className="input-field mt-2 w-full"
                            />
                          </label>
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-700">Subject template</span>
                            <input
                              value={digestSubject}
                              onChange={(e) => setDigestSubject(e.target.value)}
                              className="input-field mt-2 w-full font-mono text-xs"
                            />
                          </label>
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-700">Message template</span>
                            <textarea
                              value={digestMessage}
                              onChange={(e) => setDigestMessage(e.target.value)}
                              rows={5}
                              className="input-field mt-2 w-full resize-y font-mono text-xs leading-relaxed"
                            />
                          </label>
                          <div className="flex gap-3">
                            <button type="button" onClick={() => setStep(1)} className="workspace-btn-ghost">
                              Back
                            </button>
                            <button type="button" onClick={() => setStep(3)} className="btn-primary">
                              Schedule →
                            </button>
                          </div>
                        </motion.div>
                      )}

                      {step === 3 && (
                        <motion.div
                          key="s3"
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 12 }}
                          className="space-y-5"
                        >
                          <label className="block">
                            <span className="text-xs font-semibold text-neutral-700">Cron schedule</span>
                            <select
                              value={digestCron}
                              onChange={(e) => setDigestCron(e.target.value)}
                              className="input-field mt-2 w-full"
                            >
                              {CRON_PRESETS.map((p) => (
                                <option key={p.value} value={p.value}>
                                  {p.label} — {p.hint} ({p.value})
                                </option>
                              ))}
                            </select>
                          </label>

                          <div className="rounded-xl border border-dashed border-neutral-300 bg-neutral-50 p-4">
                            <p className="text-xs font-semibold text-neutral-800">Ready to publish</p>
                            <ul className="mt-2 space-y-1.5 text-[11px] text-neutral-600">
                              <li>• Workflow template: daily digest</li>
                              <li>• Delivery: {selected.badge}</li>
                              <li>• Knowledge: {digestKb ? kbs.find((k) => String(k.id) === digestKb)?.name || digestKb : "None"}</li>
                              <li>• Cron: {digestCron}</li>
                            </ul>
                          </div>

                          <div className="flex flex-wrap gap-3">
                            <button type="button" onClick={() => setStep(2)} className="workspace-btn-ghost">
                              Back
                            </button>
                            <motion.button
                              type="submit"
                              disabled={busy}
                              whileHover={busy ? {} : { scale: 1.02 }}
                              whileTap={busy ? {} : { scale: 0.98 }}
                              className="btn-primary disabled:opacity-50"
                            >
                              {busy ? "Publishing…" : "Create & schedule digest"}
                            </motion.button>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Live preview column */}
                  <div className="border-t border-black/[0.06] bg-neutral-50/80 p-6 lg:border-t-0 lg:border-l lg:p-8">
                    <p className="text-center text-[11px] font-semibold tracking-[0.16em] text-neutral-400 uppercase">
                      Live preview
                    </p>
                    <div className="mt-6">
                      <AnimatePresence mode="wait">
                        <DevicePreview key={selected.id} tpl={selected} />
                      </AnimatePresence>
                    </div>
                    <motion.ul
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.2 }}
                      className="mt-8 space-y-3 text-[11px] text-neutral-500"
                    >
                      {[
                        "Retrieve → LLM digest → notify",
                        "{{subject}} parsed from model output",
                        "Editable in workflow builder after create",
                      ].map((line, i) => (
                        <motion.li
                          key={line}
                          initial={{ opacity: 0, x: 8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.25 + i * 0.07 }}
                          className="flex gap-2"
                        >
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-neutral-900" />
                          {line}
                        </motion.li>
                      ))}
                    </motion.ul>
                  </div>
                </form>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* Schedules timeline */}
        <section className="mt-16">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.5, ease }}
            className="mb-6 flex items-center justify-between gap-3"
          >
            <div>
              <p className="workspace-section-label">Operations</p>
              <h2 className="mt-1 font-serif text-2xl tracking-tight">Active schedules</h2>
            </div>
            <Link href="/workflows" className="workspace-btn-ghost text-sm">
              All workflows →
            </Link>
          </motion.div>

          {schedules.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="workspace-empty rounded-[1.5rem] py-16 text-center"
            >
              <p className="font-semibold text-neutral-900">No schedules yet</p>
              <p className="mt-2 text-sm text-neutral-500">Select a template above to create your first digest.</p>
            </motion.div>
          ) : (
            <ul className="space-y-3">
              {schedules.map((row, i) => (
                <motion.li
                  key={row.id}
                  initial={{ opacity: 0, x: -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.04, duration: 0.4, ease }}
                  whileHover={{ x: 4 }}
                  className="workspace-panel flex flex-col gap-4 rounded-2xl p-5 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex min-w-0 items-start gap-4">
                    <div
                      className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${
                        row.enabled ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-500"
                      }`}
                    >
                      {row.enabled ? "ON" : "—"}
                    </div>
                    <div className="min-w-0">
                      <Link
                        href={`/workflows/${row.workflow_id}`}
                        className="font-semibold text-neutral-900 hover:underline"
                      >
                        {row.workflow_name || row.workflow_id}
                      </Link>
                      <p className="mt-1 font-mono text-xs text-neutral-500">{row.cron_expression}</p>
                      <p className="mt-1 text-xs text-neutral-400">
                        Next {fmtTime(row.next_run_at)} · Last {fmtTime(row.last_run_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleTrigger(row)}
                      className="btn-secondary text-xs disabled:opacity-50"
                    >
                      Run now
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleToggle(row)}
                      className="btn-secondary text-xs disabled:opacity-50"
                    >
                      {row.enabled ? "Pause" : "Enable"}
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDelete(row)}
                      className="workspace-btn-ghost workspace-btn-danger text-xs"
                    >
                      Delete
                    </button>
                  </div>
                </motion.li>
              ))}
            </ul>
          )}
        </section>
      </motion.div>
    </WorkspacePageShell>
  );
}
