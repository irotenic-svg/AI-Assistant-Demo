<template>
  <router-view />
</template>

<script setup>
// 根组件
</script>

<style>
/* ================================================================
   Nocturne Clinic — Base Design System
   ================================================================ */

:root {
  /* ── Surfaces ───────────────────── */
  --bg-root: #0a0e14;
  --bg-primary: #0f141c;
  --bg-secondary: #161c26;
  --bg-elevated: #1b2330;
  --bg-hover: #1e2736;

  /* ── Text ───────────────────────── */
  --text-primary: #e4ded4;
  --text-secondary: #a8a298;
  --text-muted: #6e6860;
  --text-disabled: #4a4540;

  /* ── Accent — Medicinal Amber ───── */
  --accent: #c48a40;
  --accent-soft: #b07830;
  --accent-glow: rgba(196, 138, 64, 0.12);
  --accent-glow-strong: rgba(196, 138, 64, 0.22);

  /* ── Semantic ───────────────────── */
  --success: #5a9e6f;
  --warning: #c48a40;
  --danger: #c45a4e;
  --info: #5a8aae;

  /* ── Borders ────────────────────── */
  --border-subtle: #1a2330;
  --border-default: #222d3a;
  --border-strong: #2a3646;

  /* ── Shadows ────────────────────── */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.6);

  /* ── Radii ──────────────────────── */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 20px;

  /* ── Typography ─────────────────── */
  --font-body: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB",
    "Noto Sans SC", -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: "Songti SC", "Noto Serif SC", "SimSun", "STSong", "Georgia",
    "Times New Roman", serif;
  --font-mono: "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code",
    "Consolas", "Monaco", monospace;

  /* ── Transitions ────────────────── */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;
}

/* ── Global Reset ─────────────────────────────────── */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  height: 100%;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

html.dark {
  color-scheme: dark;
}

body {
  height: 100%;
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
  background: var(--bg-root);
  overflow: hidden;
}

#app {
  height: 100%;
}

/* ── Noise texture overlay ────────────────────────── */
body::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}

/* ── Scrollbar ───────────────────────────────────── */
::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* ── Selection ───────────────────────────────────── */
::selection {
  background: var(--accent-glow-strong);
  color: var(--text-primary);
}

/* ── Focus ring ──────────────────────────────────── */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: 2px;
}
</style>
