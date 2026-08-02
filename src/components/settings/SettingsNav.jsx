"use client";

import { WorkspaceStatCard } from "@/components/workspace/WorkspaceTabs";

export { WorkspaceStatCard as SettingsStatCard };

const ICONS = {
  overview: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  security: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  ),
  models: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  ),
  integrations: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  ),
  team: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
};

export const SETTINGS_TABS = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "security", label: "Security", icon: "security" },
  { id: "models", label: "AI Providers", icon: "models", adminOnly: true },
  { id: "integrations", label: "Integrations", icon: "integrations", adminOnly: true },
  { id: "team", label: "Team", icon: "team", adminOnly: true },
];

export default function SettingsNav({ activeTab, onChange, isAdmin }) {
  const tabs = SETTINGS_TABS.filter((t) => !t.adminOnly || isAdmin);

  return (
    <>
      <nav className="settings-nav-desktop hidden lg:block" aria-label="Settings sections">
        <ul className="space-y-1">
          {tabs.map((tab) => (
            <li key={tab.id}>
              <button
                type="button"
                onClick={() => onChange(tab.id)}
                className={`settings-nav-item w-full ${activeTab === tab.id ? "settings-nav-item--active" : ""}`}
              >
                <span className="settings-nav-icon">{ICONS[tab.icon]}</span>
                {tab.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="settings-nav-mobile lg:hidden">
        <div className="settings-nav-mobile-scroll flex gap-2 overflow-x-auto pb-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              className={`settings-nav-pill shrink-0 ${activeTab === tab.id ? "settings-nav-pill--active" : ""}`}
            >
              <span className="settings-nav-pill-icon">{ICONS[tab.icon]}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
