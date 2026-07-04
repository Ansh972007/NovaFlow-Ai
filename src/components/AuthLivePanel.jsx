"use client";

import AuthShowcasePanel from "./AuthShowcasePanel";

export default function AuthLivePanel({ isRegister = false, greeting = 0 }) {
  return <AuthShowcasePanel isRegister={isRegister} greeting={greeting} />;
}
