"""
SOW Decomposition Engine — Web Interface (Double Line).
Run: python -m src.web
"""
import json
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from .parser import parse_sow
from .matcher import load_catalog, match_deliverables
from .estimator import estimate_tasks
from .dependency import resolve_dependencies


app = FastAPI(title="Double Line SOW Engine", version="1.0.0")


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SOW Engine — Double Line</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230F2B5B'/><rect y='20' width='32' height='12' rx='0' fill='%23E85D1C' opacity='0.9'/><text x='16' y='15' font-family='Arial,sans-serif' font-weight='900' font-size='13' fill='white' text-anchor='middle' dominant-baseline='middle'>DL</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  /* Double Line brand */
  --dl-navy:      #0F2B5B;
  --dl-navy-dim:  rgba(15,43,91,0.08);
  --dl-navy-mid:  rgba(15,43,91,0.15);
  --dl-orange:    #E85D1C;
  --dl-orange-dim:rgba(232,93,28,0.08);
  --dl-teal:      #0891B2;

  /* UI surfaces */
  --bg:       #ECF1FA;
  --surface:  #FFFFFF;
  --surface2: #F3F7FD;
  --border:   #DBE4F0;
  --text:     #131D34;
  --muted:    #5E7290;

  /* Status */
  --green:    #059669;
  --amber:    #D97706;
  --red:      #DC2626;
  --purple:   #7C3AED;

  /* Nav */
  --nav:      #081524;
  --nav-text: #8FA6C0;

  /* Shadows */
  --shadow:   0 1px 4px rgba(8,21,36,0.08), 0 0 0 1px rgba(8,21,36,0.04);
  --shadow-md:0 4px 16px rgba(8,21,36,0.10), 0 0 0 1px rgba(8,21,36,0.04);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: 'Inter', -apple-system, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* ─── DOUBLE LINE STRIPE ─────────────────────────────────── */
.dl-bar {
  height: 5px;
  background: linear-gradient(180deg, var(--dl-navy) 60%, var(--dl-orange) 60%);
  position: fixed; top: 0; left: 0; right: 0; z-index: 300;
}

/* ─── TOPNAV ─────────────────────────────────────────────── */
.topnav {
  position: fixed; top: 5px; left: 0; right: 0; z-index: 200;
  height: 54px;
  background: var(--nav);
  display: flex; align-items: center;
  padding: 0 24px;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.nav-left { display: flex; align-items: center; gap: 16px; }
.nav-logo { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.nav-logo-mark {
  width: 30px; height: 30px;
  background: linear-gradient(135deg, var(--dl-navy) 0%, var(--dl-teal) 100%);
  border: 2px solid var(--dl-orange);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 900; color: #fff;
  letter-spacing: -0.5px; flex-shrink: 0;
  font-style: italic;
}
.nav-logo-name {
  font-size: 14px; font-weight: 700; color: #fff;
  letter-spacing: -0.01em;
}
.nav-logo-name em { color: var(--dl-orange); font-style: normal; }
.nav-sep { width: 1px; height: 18px; background: rgba(255,255,255,0.12); }
.nav-page { font-size: 13px; color: var(--nav-text); font-weight: 400; }
.nav-client { font-size: 13px; font-weight: 600; color: #fff; display: none; }
.nav-right { display: flex; align-items: center; gap: 8px; }

/* ─── BUTTONS ────────────────────────────────────────────── */
.btn {
  padding: 8px 18px; border-radius: 6px; border: none;
  font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.15s; display: inline-flex;
  align-items: center; gap: 6px; text-decoration: none;
}
.btn-primary { background: var(--dl-orange); color: #fff; }
.btn-primary:hover { background: #C44B13; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost-light {
  background: rgba(255,255,255,0.08);
  color: var(--nav-text);
  border: 1px solid rgba(255,255,255,0.12);
}
.btn-ghost-light:hover { background: rgba(255,255,255,0.14); color: #fff; }
.btn-outline {
  background: var(--surface); color: var(--text);
  border: 1px solid var(--border); box-shadow: var(--shadow);
}
.btn-outline:hover { background: var(--surface2); border-color: #BDD0E8; }
.btn-dl {
  background: rgba(255,255,255,0.08); color: var(--nav-text);
  border: 1px solid rgba(255,255,255,0.1);
  font-weight: 500; font-size: 12px; padding: 6px 12px;
}
.btn-dl:hover { background: rgba(255,255,255,0.15); color: #fff; }
.dl-group { display: none; align-items: center; gap: 6px; }

/* ─── VIEW TOGGLE ────────────────────────────────────────── */
.view-toggle {
  display: none; align-items: center;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 7px; padding: 3px; gap: 2px;
}
.vtab {
  padding: 5px 14px; border-radius: 5px;
  font-size: 12px; font-weight: 500;
  cursor: pointer; border: none;
  background: transparent; color: var(--nav-text);
  transition: all 0.15s; font-family: 'Inter', sans-serif;
}
.vtab.active { background: rgba(255,255,255,0.15); color: #fff; }

/* ─── INPUT VIEW ─────────────────────────────────────────── */
#input-view {
  min-height: 100vh;
  padding: 132px 24px 60px;
  display: flex; flex-direction: column;
  align-items: center;
}
.hero-chip {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 5px 14px; border-radius: 20px;
  background: var(--dl-navy-dim);
  border: 1px solid rgba(15,43,91,0.2);
  font-size: 11px; font-weight: 600; color: var(--dl-navy);
  letter-spacing: 0.05em; text-transform: uppercase;
  margin-bottom: 22px;
}
.hero-chip-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--dl-orange); }
.hero-h1 {
  font-size: 38px; font-weight: 800; text-align: center;
  line-height: 1.15; letter-spacing: -0.03em;
  color: var(--text); margin-bottom: 14px;
}
.hero-h1 .accent { color: var(--dl-navy); }
.hero-sub {
  font-size: 15px; color: var(--muted); text-align: center;
  max-width: 500px; line-height: 1.65; margin-bottom: 40px;
  font-weight: 400;
}
.input-card {
  width: 100%; max-width: 780px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.input-card-head {
  padding: 16px 20px 0;
  display: flex; align-items: center; justify-content: space-between;
}
.input-card-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }
.sample-link {
  font-size: 12px; font-weight: 500; color: var(--dl-navy);
  background: none; border: none; cursor: pointer; padding: 0;
  font-family: 'Inter', sans-serif;
}
.sample-link:hover { text-decoration: underline; }
textarea {
  width: 100%; height: 260px;
  background: var(--surface);
  border: none;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin-top: 12px;
  color: var(--text);
  font-family: 'Roboto Mono', monospace;
  font-size: 12px; line-height: 1.65;
  padding: 16px 20px; resize: vertical;
  outline: none;
}
textarea::placeholder { color: #9AAFC4; }
textarea:focus { border-color: rgba(15,43,91,0.35); }
.input-footer {
  padding: 14px 20px;
  display: flex; align-items: center;
  justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.status-row { display: flex; align-items: center; gap: 10px; }
.status-txt { font-size: 12px; color: var(--dl-orange); font-family: 'Roboto Mono', monospace; }
.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(232,93,28,0.25);
  border-top-color: var(--dl-orange); border-radius: 50%;
  animation: spin 0.75s linear infinite; display: none;
}
@keyframes spin { to { transform: rotate(360deg); } }
.powered-by {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--muted);
}
.dl-dots { display: flex; gap: 3px; }
.dl-dot { width: 6px; height: 6px; border-radius: 50%; }

/* ─── RESULTS VIEW ───────────────────────────────────────── */
#results-view { display: none; padding-top: 59px; }
.results-body { padding: 24px 28px 40px; max-width: 1360px; margin: 0 auto; }

/* Client header */
.client-header {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow);
  padding: 20px 24px; margin-bottom: 20px;
  display: flex; align-items: flex-start;
  justify-content: space-between; flex-wrap: wrap; gap: 14px;
  border-left: 4px solid var(--dl-orange);
}
.ch-name { font-size: 21px; font-weight: 700; letter-spacing: -0.02em; }
.ch-platform { font-size: 13px; color: var(--muted); margin-top: 3px; }
.ch-platform b { color: var(--text); font-weight: 600; }
.ch-arrow { color: var(--dl-navy); margin: 0 5px; }
.badges { display: flex; gap: 7px; flex-wrap: wrap; }
.badge {
  padding: 4px 11px; border-radius: 20px;
  font-size: 12px; font-weight: 500; border: 1px solid transparent;
}
.b-blue   { background: var(--dl-navy-dim);          color: #0F2B5B; border-color: rgba(15,43,91,0.2); }
.b-green  { background: rgba(5,150,105,0.08);         color: #065F46; border-color: rgba(5,150,105,0.2); }
.b-amber  { background: rgba(217,119,6,0.08);         color: #92400E; border-color: rgba(217,119,6,0.2); }
.b-red    { background: rgba(220,38,38,0.08);         color: #991B1B; border-color: rgba(220,38,38,0.2); }
.b-purple { background: rgba(124,58,237,0.08);        color: #5B21B6; border-color: rgba(124,58,237,0.2); }
.b-orange { background: var(--dl-orange-dim);         color: #C44B13; border-color: rgba(232,93,28,0.2); }

/* Stat cards */
.stats-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 20px; }
.stat-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow);
  padding: 18px 20px;
  border-top: 3px solid;
}
.stat-card.c-blue   { border-top-color: var(--dl-navy); }
.stat-card.c-green  { border-top-color: var(--green); }
.stat-card.c-amber  { border-top-color: var(--dl-orange); }
.stat-card.c-purple { border-top-color: var(--purple); }
.stat-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 8px; }
.stat-val { font-size: 32px; font-weight: 800; line-height: 1; letter-spacing: -0.03em; }
.stat-val.c-blue   { color: var(--dl-navy); }
.stat-val.c-green  { color: var(--green); }
.stat-val.c-amber  { color: var(--dl-orange); }
.stat-val.c-purple { color: var(--purple); }
.stat-sub { font-size: 12px; color: var(--muted); margin-top: 5px; }

/* Two col */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; }
.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow); padding: 18px 20px;
}
.panel-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 16px; }

/* Phase bars */
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.bar-lbl { font-size: 12px; font-weight: 500; width: 80px; flex-shrink: 0; color: var(--text); }
.bar-track { flex: 1; height: 8px; background: var(--surface2); border-radius: 4px; overflow: hidden; border: 1px solid var(--border); }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.8s cubic-bezier(0.4,0,0.2,1); }
.bar-hrs { font-size: 12px; color: var(--muted); width: 34px; text-align: right; font-weight: 500; }

/* Role cards */
.role-cards { display: flex; flex-direction: column; gap: 9px; }
.role-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px; border-radius: 8px;
  background: var(--surface2); border: 1px solid var(--border);
  border-left: 3px solid;
}
.role-name { font-size: 13px; font-weight: 600; color: var(--text); }
.role-pct  { font-size: 11px; color: var(--muted); margin-top: 2px; }
.role-hrs  { font-size: 22px; font-weight: 800; letter-spacing: -0.02em; }

/* Critical path */
.crit-section {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow);
  padding: 18px 20px; margin-bottom: 20px;
}
.crit-scroll { overflow-x: auto; padding-bottom: 4px; }
.crit-path { display: flex; align-items: center; flex-wrap: nowrap; min-width: max-content; }
.crit-node {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 14px;
  min-width: 140px; max-width: 165px;
}
.cn-id   { font-size: 10px; font-family: 'Roboto Mono', monospace; color: var(--dl-navy); margin-bottom: 4px; font-weight: 500; }
.cn-name { font-size: 12px; font-weight: 600; line-height: 1.3; color: var(--text); }
.cn-hrs  { font-size: 11px; color: var(--dl-orange); margin-top: 4px; font-weight: 600; }
.crit-arrow { color: var(--dl-navy); font-size: 16px; padding: 0 5px; opacity: 0.5; flex-shrink: 0; }

/* Phase tabs */
.phase-tabs-section {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow);
  margin-bottom: 20px; overflow: hidden;
}
.tab-bar { display: flex; border-bottom: 1px solid var(--border); overflow-x: auto; scrollbar-width: none; }
.tab-bar::-webkit-scrollbar { display: none; }
.ptab {
  padding: 12px 16px; font-size: 13px; font-weight: 500;
  cursor: pointer; border: none; background: transparent;
  color: var(--muted); border-bottom: 2px solid transparent;
  transition: all 0.15s; white-space: nowrap;
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
  font-family: 'Inter', sans-serif;
}
.ptab:hover { color: var(--text); background: var(--surface2); }
.ptab.active { color: var(--text); }
.ptab-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.ptab-count { background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 1px 7px; font-size: 11px; color: var(--muted); }
.phase-panel { display: none; padding: 16px; }
.phase-panel.active { display: block; }

/* Task cards */
.task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); gap: 12px; }
.tcard {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; border-left: 3px solid;
  box-shadow: var(--shadow); transition: box-shadow 0.15s;
}
.tcard:hover { box-shadow: var(--shadow-md); }
.tcard-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 6px; margin-bottom: 6px; }
.tid { font-size: 10px; font-family: 'Roboto Mono', monospace; color: var(--muted); background: var(--surface); border: 1px solid var(--border); padding: 2px 7px; border-radius: 4px; }
.crit-tag { font-size: 10px; font-weight: 700; color: var(--dl-orange); }
.tname { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 9px; line-height: 1.35; }
.thrs-row { display: flex; align-items: baseline; gap: 3px; margin-bottom: 3px; }
.thrs-num { font-size: 26px; font-weight: 800; line-height: 1; letter-spacing: -0.02em; }
.thrs-unit { font-size: 12px; color: var(--muted); }
.trange { font-size: 11px; color: var(--muted); margin-bottom: 9px; }
.tchips { display: flex; gap: 5px; flex-wrap: wrap; }
.chip { font-size: 11px; font-weight: 500; padding: 3px 9px; border-radius: 10px; border: 1px solid transparent; }
.chip-high   { background: rgba(5,150,105,0.1);   color: #065F46; border-color: rgba(5,150,105,0.2); }
.chip-medium { background: rgba(217,119,6,0.1);   color: #92400E; border-color: rgba(217,119,6,0.2); }
.chip-low    { background: rgba(220,38,38,0.1);   color: #991B1B; border-color: rgba(220,38,38,0.2); }
.chip-role   { background: var(--surface); color: var(--muted); border-color: var(--border); }
.tdeps { margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--border); font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.dep-tag { font-family: 'Roboto Mono', monospace; background: var(--surface); border: 1px solid var(--border); padding: 1px 6px; border-radius: 3px; }

/* Warnings */
.warn-section {
  background: #FFF8F5; border: 1px solid rgba(232,93,28,0.25);
  border-radius: 10px; padding: 14px 18px; margin-bottom: 20px;
}
.warn-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #9A3D14; margin-bottom: 8px; }
.warn-row { display: flex; align-items: flex-start; gap: 7px; font-size: 13px; color: #7B2E0C; padding: 3px 0; }

/* ─── GANTT ──────────────────────────────────────────────── */
#gantt-view { display: none; padding: 24px 28px 40px; max-width: 1360px; margin: 0 auto; }
.gantt-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow); overflow: hidden;
}
.gantt-legend {
  padding: 14px 20px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
}
.gantt-legend-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-right: 4px; }
.gl-item { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--muted); }
.gl-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
.gantt-scroll { overflow-x: auto; }
.gantt-inner { min-width: 900px; }

/* Week header */
.g-week-row {
  display: flex; border-bottom: 1px solid var(--border);
  background: var(--surface2);
}
.g-label-col { width: 220px; flex-shrink: 0; padding: 8px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); border-right: 1px solid var(--border); }
.g-weeks-header { flex: 1; display: flex; position: relative; }
.g-week-cell { flex: 1; text-align: center; font-size: 11px; font-weight: 600; color: var(--muted); padding: 8px 4px; border-right: 1px solid var(--border); }
.g-week-cell:last-child { border-right: none; }

/* Phase group */
.g-phase-header {
  display: flex; align-items: center;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
}
.g-phase-name {
  width: 220px; flex-shrink: 0;
  padding: 7px 12px;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em;
  border-right: 1px solid var(--border);
  display: flex; align-items: center; gap: 6px;
}
.g-phase-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.g-phase-track { flex: 1; height: 100%; }

/* Task row */
.g-row {
  display: flex; align-items: center;
  border-bottom: 1px solid var(--border);
  min-height: 36px;
}
.g-row:last-child { border-bottom: none; }
.g-row:hover { background: rgba(15,43,91,0.025); }
.g-task-label {
  width: 220px; flex-shrink: 0;
  padding: 6px 12px 6px 20px;
  font-size: 12px; font-weight: 500; color: var(--text);
  border-right: 1px solid var(--border);
  line-height: 1.3;
  display: flex; align-items: center; gap: 5px;
}
.g-task-bar-area {
  flex: 1; position: relative;
  height: 36px; overflow: visible;
}
.g-grid-lines {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; pointer-events: none;
}
.g-grid-line { flex: 1; border-right: 1px solid var(--border); }
.g-grid-line:last-child { border-right: none; }
.g-bar {
  position: absolute; top: 50%; transform: translateY(-50%);
  height: 20px; border-radius: 4px;
  display: flex; align-items: center;
  padding: 0 6px; overflow: hidden;
  cursor: default;
  transition: opacity 0.15s;
  min-width: 4px;
}
.g-bar:hover { opacity: 0.85; }
.g-bar-label { font-size: 10px; font-weight: 600; color: rgba(255,255,255,0.9); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.g-bar-crit { outline: 2px solid var(--dl-orange); outline-offset: 1px; border-radius: 4px; }

/* Footer */
.page-footer {
  text-align: center; padding: 18px;
  font-size: 12px; color: var(--muted);
  border-top: 1px solid var(--border); margin-top: 4px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.footer-mark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 3px;
  background: linear-gradient(135deg, var(--dl-navy), var(--dl-teal));
  font-size: 7px; font-weight: 900; color: #fff;
  letter-spacing: -0.3px; font-style: italic;
}
.page-footer span { color: var(--dl-navy); font-weight: 600; }

/* Utility */
.hidden { display: none !important; }
@media (max-width: 860px) {
  .stats-row { grid-template-columns: repeat(2,1fr); }
  .two-col   { grid-template-columns: 1fr; }
  .results-body, #gantt-view { padding: 14px; }
}
</style>
</head>
<body>

<div class="dl-bar"></div>

<!-- ══ NAV ═══════════════════════════════════════════════════════ -->
<nav class="topnav">
  <div class="nav-left">
    <a class="nav-logo" href="#">
      <div class="nav-logo-mark">DL</div>
      <div class="nav-logo-name">Double <em>Line</em></div>
    </a>
    <div class="nav-sep"></div>
    <span class="nav-page" id="nav-page">SOW Decomposition Engine</span>
    <span class="nav-client hidden" id="nav-client"></span>
  </div>
  <div class="nav-right">
    <div class="view-toggle" id="view-toggle">
      <button class="vtab active" id="vt-overview" onclick="setView('overview')">Overview</button>
      <button class="vtab"        id="vt-gantt"    onclick="setView('gantt')">Timeline</button>
    </div>
    <div class="dl-group" id="dl-group">
      <button class="btn btn-dl" onclick="downloadJira()">↓ JIRA CSV</button>
      <button class="btn btn-dl" onclick="downloadMarkdown()">↓ Markdown</button>
      <button class="btn btn-dl" onclick="downloadJSON()">↓ JSON</button>
    </div>
    <button class="btn btn-ghost-light hidden" id="btn-back" onclick="newAnalysis()">← New Analysis</button>
  </div>
</nav>

<!-- ══ INPUT VIEW ════════════════════════════════════════════════ -->
<div id="input-view">
  <div class="hero-chip"><div class="hero-chip-dot"></div>Data &amp; Technology Strategy</div>
  <h1 class="hero-h1">Turn any SOW into a<br><span class="accent">JIRA-ready project plan</span></h1>
  <p class="hero-sub">Paste a Statement of Work. Claude AI extracts every deliverable, matches them to the task catalog, estimates hours with confidence scoring, and resolves the critical path — in under 30 seconds.</p>

  <div class="input-card">
    <div class="input-card-head">
      <span class="input-card-label">Statement of Work</span>
      <label class="sample-link" for="sow-file">Upload SOW file ↗
        <input type="file" id="sow-file" accept=".txt,.pdf" style="display:none" onchange="loadFile(this)">
      </label>
    </div>
    <textarea id="sow" placeholder="Paste your Statement of Work here — plain text or copied from a PDF..."></textarea>
    <div class="input-footer">
      <div class="status-row">
        <button class="btn btn-primary" id="btn-analyze" onclick="analyze()">Analyze SOW</button>
        <div class="spinner" id="spinner"></div>
        <span class="status-txt" id="status-txt"></span>
      </div>
      <div class="powered-by">
        <div class="dl-dots">
          <div class="dl-dot" style="background:var(--dl-navy)"></div>
          <div class="dl-dot" style="background:var(--dl-orange)"></div>
        </div>
        Powered by Claude AI
      </div>
    </div>
  </div>
</div>

<!-- ══ RESULTS VIEW ══════════════════════════════════════════════ -->
<div id="results-view">
<div class="results-body">

  <!-- Client header -->
  <div class="client-header">
    <div>
      <div class="ch-name" id="r-name"></div>
      <div class="ch-platform">
        <b id="r-platform"></b><span class="ch-arrow">→</span><b id="r-target"></b>
      </div>
    </div>
    <div class="badges" id="r-badges"></div>
  </div>

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat-card c-blue">
      <div class="stat-lbl">Total Estimated Hours</div>
      <div class="stat-val c-blue" id="s-hours">—</div>
      <div class="stat-sub" id="s-hours-sub"></div>
    </div>
    <div class="stat-card c-green">
      <div class="stat-lbl">Tasks Generated</div>
      <div class="stat-val c-green" id="s-tasks">—</div>
      <div class="stat-sub">across 7 project phases</div>
    </div>
    <div class="stat-card c-amber">
      <div class="stat-lbl">Critical Path</div>
      <div class="stat-val c-amber" id="s-crit">—</div>
      <div class="stat-sub">sequential dependencies</div>
    </div>
    <div class="stat-card c-purple">
      <div class="stat-lbl">Engagement Type</div>
      <div class="stat-val c-purple" id="s-type" style="font-size:18px;padding-top:7px">—</div>
      <div class="stat-sub" id="s-type-sub"></div>
    </div>
  </div>

  <!-- Phase + Role -->
  <div class="two-col">
    <div class="panel">
      <div class="panel-title">Hours by Phase</div>
      <div id="phase-bars"></div>
    </div>
    <div class="panel">
      <div class="panel-title">Hours by Role</div>
      <div class="role-cards" id="role-cards"></div>
    </div>
  </div>

  <!-- Critical Path -->
  <div class="crit-section">
    <div class="panel-title">⚡ Critical Path</div>
    <div class="crit-scroll"><div class="crit-path" id="crit-path"></div></div>
  </div>

  <!-- Phase Tabs -->
  <div class="phase-tabs-section">
    <div class="tab-bar" id="tab-bar"></div>
    <div id="phase-panels"></div>
  </div>

  <!-- Warnings -->
  <div class="warn-section hidden" id="warn-section">
    <div class="warn-title">⚠ Dependency Warnings</div>
    <div id="warn-list"></div>
  </div>

  <div class="page-footer">
    <div class="footer-mark">DL</div>
    Generated by <span>Double Line</span> SOW Engine &nbsp;·&nbsp; Powered by Claude AI
  </div>
</div>
</div>

<!-- ══ GANTT VIEW ════════════════════════════════════════════════ -->
<div id="gantt-view">
  <div class="gantt-card">
    <div class="gantt-legend" id="gantt-legend">
      <span class="gantt-legend-title">Phases:</span>
    </div>
    <div class="gantt-scroll">
      <div class="gantt-inner" id="gantt-inner"></div>
    </div>
  </div>
  <div class="page-footer" style="margin-top:16px">
    <div class="footer-mark">DL</div>
    Generated by <span>Double Line</span> SOW Engine &nbsp;·&nbsp; Powered by Claude AI
  </div>
</div>

<!-- ══ SCRIPT ════════════════════════════════════════════════════ -->
<script>
const PHASE_COLORS = {
  Discovery: '#0F2B5B', Planning: '#7C3AED', Build: '#D97706',
  Migration: '#059669', Testing: '#0891B2', Cutover: '#DC2626', Hypercare: '#DB2777',
};
const ROLE_COLORS = { Engineer: '#0F2B5B', PM: '#DC2626', 'Change Manager': '#059669' };
const PHASE_ORDER = ['Discovery','Planning','Build','Migration','Testing','Cutover','Hypercare'];

function loadFile(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => { document.getElementById('sow').value = e.target.result; };
  reader.readAsText(file);
}

async function analyze() {
  const sow = document.getElementById('sow').value.trim();
  if (!sow) return;
  const btn = document.getElementById('btn-analyze');
  const spin = document.getElementById('spinner');
  const stxt = document.getElementById('status-txt');
  btn.disabled = true;
  spin.style.display = 'block';
  const steps = ['Parsing SOW with Claude AI...','Extracting deliverables...','Matching task catalog...','Estimating hours...','Resolving critical path...'];
  let i = 0; stxt.textContent = steps[0];
  const tick = setInterval(() => { i = Math.min(i+1, steps.length-1); stxt.textContent = steps[i]; }, 4500);
  try {
    const r = await fetch('/analyze', {
      method: 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded'},
      body: 'sow_text=' + encodeURIComponent(sow),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail||'Analysis failed'); }
    const data = await r.json();
    clearInterval(tick); spin.style.display='none'; stxt.textContent='';
    renderResults(data);
  } catch(err) {
    clearInterval(tick); spin.style.display='none';
    stxt.textContent='Error: '+err.message; stxt.style.color='#DC2626';
    btn.disabled = false;
  }
}

function newAnalysis() {
  ['results-view','gantt-view'].forEach(id => document.getElementById(id).style.display='none');
  document.getElementById('input-view').style.display='flex';
  document.getElementById('view-toggle').style.display='none';
  document.getElementById('dl-group').style.display='none';
  document.getElementById('btn-back').classList.add('hidden');
  document.getElementById('nav-client').classList.add('hidden');
  document.getElementById('nav-page').classList.remove('hidden');
  document.getElementById('btn-analyze').disabled=false;
  document.getElementById('status-txt').textContent='';
  document.getElementById('status-txt').style.color='';
}

function setView(v) {
  document.getElementById('results-view').style.display = v==='overview' ? 'block' : 'none';
  document.getElementById('gantt-view').style.display    = v==='gantt'    ? 'block' : 'none';
  document.getElementById('vt-overview').classList.toggle('active', v==='overview');
  document.getElementById('vt-gantt').classList.toggle('active', v==='gantt');
}

function renderResults(data) {
  window._plan = data;
  const {client, summary, tasks, warnings} = data;

  // Nav
  document.getElementById('nav-page').classList.add('hidden');
  document.getElementById('nav-client').textContent = client.name;
  document.getElementById('nav-client').classList.remove('hidden');
  document.getElementById('view-toggle').style.display='flex';
  document.getElementById('dl-group').style.display='flex';
  document.getElementById('btn-back').classList.remove('hidden');

  // Client header
  document.getElementById('r-name').textContent = client.name;
  document.getElementById('r-platform').textContent = client.current_platform||'Current Platform';
  document.getElementById('r-target').textContent = (client.target_services||[]).join(', ')||'Cloud Platform';
  const bd = document.getElementById('r-badges'); bd.innerHTML='';
  if (client.user_count) bd.innerHTML+=`<span class="badge b-blue">${client.user_count.toLocaleString()} users</span>`;
  if (client.timeline_weeks) bd.innerHTML+=`<span class="badge b-amber">${client.timeline_weeks}-week engagement</span>`;
  bd.innerHTML += client.is_federal
    ? '<span class="badge b-red">Federal</span>'
    : '<span class="badge b-green">Commercial</span>';

  // Stats
  document.getElementById('s-hours').textContent = Math.round(summary.total_hours)+'h';
  const wks = client.timeline_weeks || 8;
  const hrsPerWeek = Math.round(summary.total_hours / wks);
  const ftes = (summary.total_hours / (wks * 40)).toFixed(1);
  document.getElementById('s-hours-sub').textContent = `~${hrsPerWeek}h/week · ${ftes} avg FTEs`;
  document.getElementById('s-tasks').textContent = summary.task_count;
  document.getElementById('s-crit').textContent = summary.critical_path.length;
  document.getElementById('s-type').textContent = client.is_federal ? 'Federal' : 'Commercial';
  document.getElementById('s-type-sub').textContent = client.is_federal ? 'FedRAMP overhead applied' : 'Standard delivery model';

  // Phase bars
  const pb = document.getElementById('phase-bars'); pb.innerHTML='';
  const maxH = Math.max(...Object.values(summary.hours_by_phase));
  PHASE_ORDER.forEach(ph => {
    const h = summary.hours_by_phase[ph]; if (!h) return;
    const pct = (h/maxH*100).toFixed(1);
    pb.innerHTML += `<div class="bar-row">
      <div class="bar-lbl">${ph}</div>
      <div class="bar-track"><div class="bar-fill" style="width:0%;background:${PHASE_COLORS[ph]||'#64748B'}" data-pct="${pct}"></div></div>
      <div class="bar-hrs">${Math.round(h)}h</div></div>`;
  });
  setTimeout(() => { document.querySelectorAll('.bar-fill').forEach(el => { el.style.width = el.dataset.pct+'%'; }); }, 60);

  // Roles
  const rc = document.getElementById('role-cards'); rc.innerHTML='';
  const tot = summary.total_hours;
  Object.entries(summary.hours_by_role).forEach(([r,h]) => {
    const c = ROLE_COLORS[r]||'#64748B';
    rc.innerHTML+=`<div class="role-card" style="border-left-color:${c}">
      <div><div class="role-name">${r}</div><div class="role-pct">${((h/tot)*100).toFixed(0)}% of engagement</div></div>
      <div class="role-hrs" style="color:${c}">${Math.round(h)}h</div></div>`;
  });

  // Critical path
  const cp = document.getElementById('crit-path'); cp.innerHTML='';
  summary.critical_path.forEach((id,i) => {
    const t = tasks.find(t=>t.id===id); if(!t) return;
    cp.innerHTML+=`<div class="crit-node"><div class="cn-id">${t.id}</div><div class="cn-name">${t.name}</div><div class="cn-hrs">${t.adjusted_hours}h</div></div>`;
    if(i<summary.critical_path.length-1) cp.innerHTML+='<div class="crit-arrow">→</div>';
  });

  // Phase tabs
  const tb = document.getElementById('tab-bar'); tb.innerHTML='';
  const pp = document.getElementById('phase-panels'); pp.innerHTML='';
  const sortedPhases = [...new Set(tasks.map(t=>t.phase))].sort((a,b)=>PHASE_ORDER.indexOf(a)-PHASE_ORDER.indexOf(b));
  sortedPhases.forEach((ph,i) => {
    const pts = tasks.filter(t=>t.phase===ph);
    const c = PHASE_COLORS[ph]||'#64748B';
    const active = i===0;
    tb.innerHTML+=`<button class="ptab${active?' active':''}" id="ptab-${ph}" onclick="switchPhase('${ph}','${c}')" style="${active?'border-bottom-color:'+c:''}">
      <div class="ptab-dot" style="background:${c}"></div>${ph}<span class="ptab-count">${pts.length}</span></button>`;
    const cards = pts.map(t=>{
      const isCrit = summary.critical_path.includes(t.id);
      const deps = (t.dependencies||[]);
      const dh = deps.length?`<div class="tdeps"><span>Deps:</span>${deps.map(d=>`<span class="dep-tag">${d}</span>`).join('')}</div>`:'';
      return `<div class="tcard" style="border-left-color:${c}">
        <div class="tcard-top"><span class="tid">${t.id}</span>${isCrit?'<span class="crit-tag">⚡ critical</span>':''}</div>
        <div class="tname">${t.name}</div>
        <div class="thrs-row"><span class="thrs-num" style="color:${c}">${t.adjusted_hours}</span><span class="thrs-unit">h estimated</span></div>
        <div class="trange">Range: ${t.range[0]}h – ${t.range[1]}h</div>
        <div class="tchips"><span class="chip chip-${t.confidence}">${t.confidence} confidence</span><span class="chip chip-role">${t.role}</span></div>
        ${dh}</div>`;
    }).join('');
    pp.innerHTML+=`<div class="phase-panel${active?' active':''}" id="pp-${ph}"><div class="task-grid">${cards}</div></div>`;
  });

  // Warnings
  if (warnings?.length) {
    document.getElementById('warn-section').classList.remove('hidden');
    document.getElementById('warn-list').innerHTML = warnings.map(w=>`<div class="warn-row"><span>⚠</span><span>${w}</span></div>`).join('');
  }

  // Build Gantt
  buildGantt(data);

  // Show
  document.getElementById('input-view').style.display='none';
  setView('overview');
  document.getElementById('results-view').style.display='block';
  window.scrollTo(0,0);
}

function switchPhase(ph, c) {
  document.querySelectorAll('.ptab').forEach(t=>{ t.classList.remove('active'); t.style.borderBottomColor='transparent'; });
  document.querySelectorAll('.phase-panel').forEach(p=>p.classList.remove('active'));
  const tab = document.getElementById('ptab-'+ph);
  tab.classList.add('active'); tab.style.borderBottomColor=c;
  document.getElementById('pp-'+ph).classList.add('active');
}

// ─── GANTT ─────────────────────────────────────────────────────
function computeSchedule(tasks) {
  const byId = {}; tasks.forEach(t=>byId[t.id]={...t});
  const starts = {};
  function getStart(id) {
    if (id in starts) return starts[id];
    const task = byId[id];
    if (!task||!task.dependencies?.length) { starts[id]=0; return 0; }
    starts[id] = Math.max(...task.dependencies.map(d=>{ const dt=byId[d]; return dt?getStart(d)+dt.adjusted_hours:0; }));
    return starts[id];
  }
  tasks.forEach(t=>getStart(t.id));
  let maxEnd = 0;
  tasks.forEach(t=>{ maxEnd=Math.max(maxEnd,starts[t.id]+t.adjusted_hours); });
  return tasks.map(t=>({ ...t, startPct:(starts[t.id]/maxEnd)*100, widthPct:Math.max((t.adjusted_hours/maxEnd)*100,1.5) }));
}

function buildGantt(data) {
  const {client, summary, tasks} = data;
  const weeks = client.timeline_weeks||8;
  const critSet = new Set(summary.critical_path);
  const scheduled = computeSchedule(tasks);
  const byPhase = {};
  PHASE_ORDER.forEach(ph=>byPhase[ph]=[]);
  scheduled.forEach(t=>{ if(byPhase[t.phase]) byPhase[t.phase].push(t); });

  // Legend
  const leg = document.getElementById('gantt-legend'); leg.innerHTML='<span class="gantt-legend-title">Phases:</span>';
  PHASE_ORDER.filter(ph=>byPhase[ph]?.length).forEach(ph=>{
    leg.innerHTML+=`<div class="gl-item"><div class="gl-dot" style="background:${PHASE_COLORS[ph]}"></div>${ph}</div>`;
  });

  const weekCells = Array.from({length:weeks},(_,i)=>`<div class="g-week-cell">Wk ${i+1}</div>`).join('');
  const gridLines = Array.from({length:weeks},()=>'<div class="g-grid-line"></div>').join('');

  let html = `<div class="g-week-row">
    <div class="g-label-col">Task</div>
    <div class="g-weeks-header">${weekCells}</div></div>`;

  PHASE_ORDER.forEach(ph=>{
    const pts = byPhase[ph]; if(!pts?.length) return;
    const c = PHASE_COLORS[ph]||'#64748B';
    html+=`<div class="g-phase-header">
      <div class="g-phase-name" style="color:${c}"><div class="g-phase-dot" style="background:${c}"></div>${ph}</div>
      <div class="g-phase-track"></div></div>`;
    pts.forEach(t=>{
      const isCrit = critSet.has(t.id);
      const barClass = isCrit ? 'g-bar g-bar-crit' : 'g-bar';
      html+=`<div class="g-row">
        <div class="g-task-label">
          ${isCrit?'<span style="color:'+PHASE_COLORS[ph]+';font-size:10px">⚡</span>':''}
          <span>${t.name}</span>
        </div>
        <div class="g-task-bar-area">
          <div class="g-grid-lines">${gridLines}</div>
          <div class="${barClass}" style="left:${t.startPct.toFixed(2)}%;width:${t.widthPct.toFixed(2)}%;background:${c}" title="${t.name} — ${t.adjusted_hours}h (${t.confidence} confidence)">
            <span class="g-bar-label">${t.adjusted_hours}h</span>
          </div>
        </div></div>`;
    });
  });

  document.getElementById('gantt-inner').innerHTML = html;
}

// ─── DOWNLOADS ─────────────────────────────────────────────────
function dl(content, name, mime) {
  const a = Object.assign(document.createElement('a'),{href:URL.createObjectURL(new Blob([content],{type:mime})),download:name});
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}
function downloadJSON() {
  if(!window._plan) return;
  dl(JSON.stringify(window._plan,null,2),'plan.json','application/json');
}
function downloadJira() {
  if(!window._plan) return;
  const {tasks}=window._plan;
  const H=['Summary','Description','Issue Type','Priority','Story Points','Original Estimate','Component','Labels','Sprint Phase','Assignee Role','Dependencies','Confidence','Estimation Rationale'];
  const esc=v=>`"${String(v).replace(/"/g,'""')}"`;
  const rows=tasks.map(t=>[t.name,`[${t.id}] ${t.category}\n\nMatch type: ${t.match_type}\nConfidence: ${t.confidence}\n\n${t.rationale}`,'Task',t.confidence==='high'?'High':t.confidence==='medium'?'Medium':'Low',Math.max(1,Math.round(t.adjusted_hours/4)),`${t.adjusted_hours}h`,t.category,`${t.phase},${t.match_type}`,t.phase,t.role,(t.dependencies||[]).join(', '),t.confidence,t.rationale]);
  dl([H.map(esc).join(','),...rows.map(r=>r.map(esc).join(','))].join('\r\n'),'jira_import.csv','text/csv');
}
function downloadMarkdown() {
  if(!window._plan) return;
  const {client,summary,tasks,warnings}=window._plan;
  let md=`# Project Plan: ${client.name}\n\n**Users:** ${client.user_count} | **Timeline:** ${client.timeline_weeks} weeks | **Platform:** ${client.current_platform} → ${(client.target_services||[]).join(', ')}\n\n## Summary\n\n|Metric|Value|\n|---|---|\n|Total Estimated Hours|**${Math.round(summary.total_hours)}h**|\n`;
  PHASE_ORDER.forEach(ph=>{const h=summary.hours_by_phase[ph];if(h)md+=`|${ph}|${Math.round(h)}h|\n`;});
  md+='\n### Hours by Role\n\n';
  Object.entries(summary.hours_by_role).forEach(([r,h])=>{md+=`- **${r}:** ${Math.round(h)}h\n`;});
  md+='\n## Critical Path\n\n';
  summary.critical_path.forEach(id=>{const t=tasks.find(t=>t.id===id);if(t)md+=`→ **${t.name}** (${t.adjusted_hours}h, ${t.phase})\n`;});
  md+='\n## Task Breakdown by Phase\n\n';
  let cur=null;
  [...tasks].sort((a,b)=>PHASE_ORDER.indexOf(a.phase)-PHASE_ORDER.indexOf(b.phase)).forEach(t=>{
    if(t.phase!==cur){cur=t.phase;md+=`\n### ${cur}\n\n`;}
    const ic=t.confidence==='high'?'🟢':t.confidence==='medium'?'🟡':'🔴';
    const cr=summary.critical_path.includes(t.id)?' ⚡':'';
    const dp=t.dependencies?.length?` (depends on: ${t.dependencies.join(', ')})`:'';
    md+=`- ${ic} **${t.name}** [${t.id}]${cr}\n  - Role: ${t.role} | Hours: ${t.adjusted_hours}h\n  - ${t.rationale}${dp}\n\n`;
  });
  if(warnings?.length){md+=`## Warnings\n\n`;warnings.forEach(w=>{md+=`⚠️ ${w}\n`;});}
  dl(md,'project_timeline.md','text/markdown');
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML


@app.post("/analyze")
async def analyze(sow_text: str = Form(...)):
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")

    try:
        parsed = parse_sow(sow_text)
        ctx = parsed.client_context

        catalog = load_catalog()
        match_result = match_deliverables(
            deliverables=parsed.deliverables,
            exclusions=parsed.exclusions,
            catalog=catalog,
            is_federal=ctx.is_federal,
        )

        estimated = estimate_tasks(match_result.matched_tasks, ctx)
        plan = resolve_dependencies(estimated)

        return JSONResponse(content={
            "client": {
                "name": ctx.organization_name,
                "user_count": ctx.user_count,
                "current_platform": ctx.current_platform,
                "target_services": ctx.target_services,
                "is_federal": ctx.is_federal,
                "timeline_weeks": ctx.timeline_weeks,
            },
            "summary": {
                "total_hours": plan.total_hours,
                "hours_by_phase": plan.hours_by_phase,
                "hours_by_role": plan.hours_by_role,
                "task_count": len(plan.ordered_tasks),
                "critical_path": plan.critical_path,
            },
            "tasks": [
                {
                    "id": t.task_id,
                    "name": t.task_name,
                    "category": t.category,
                    "role": t.role,
                    "phase": t.phase,
                    "baseline_hours": t.baseline_hours,
                    "adjusted_hours": t.adjusted_hours,
                    "range": [t.low_hours, t.high_hours],
                    "confidence": t.confidence,
                    "rationale": t.rationale,
                    "dependencies": t.dependencies,
                    "match_type": t.match_type,
                }
                for t in plan.ordered_tasks
            ],
            "warnings": plan.dependency_warnings,
            "unmatched_deliverables": [
                {"name": d.name, "description": d.description}
                for d in match_result.unmatched_deliverables
            ],
            "excluded_tasks": [
                {"task": t.name, "reason": reason}
                for t, reason in match_result.excluded_tasks
            ],
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
