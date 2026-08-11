import io
import json
import secrets
import re
import sqlite3
import threading
import time
import random
import uuid
from datetime import datetime, timedelta

# --- SECURITY & CLOUD MODULES ---
from werkzeug.security import generate_password_hash, check_password_hash
import boto3

# --- EMAIL MODULES (NEW) ---
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- WEB FRAMEWORK ---
from flask import (
    Flask, request, jsonify, render_template_string, send_file, url_for, redirect, session, has_request_context, g, make_response
)
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
DATABASE = 'cspm.db'

# ==========================================
# EMAIL ALERT CONFIGURATION
# ==========================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "devp20050@gmail.com" 
SENDER_PASSWORD = "xhehoefkfamxwhjt" # Note: Spaces removed for SMTP compatibility

def send_email_async(user_email, severity, message):
    """Background task to send email without blocking the web application."""
    if SENDER_EMAIL == "your_email@gmail.com":
        print(f"[Simulated Email] Would send to {user_email}: [{severity}] {message}")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = user_email
        msg['Subject'] = f"Nexus Security Alert: {severity} Notice"

        body = f"Hello,\n\nNexus Security has generated a new automatic system alert.\n\nSeverity: {severity}\nDetails: {message}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nPlease log in to the dashboard to investigate or verify this action.\n\nBest,\nNexus Security Auto-Bot"
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Automatic alert email sent successfully to {user_email}")
    except Exception as e:
        print(f"Failed to send alert email: {e}")

def trigger_email_alert(user_email, severity, message):
    """Triggers an email alert to the user's registered email address automatically via threading."""
    # Using threading so the UI doesn't freeze while waiting for the SMTP server to respond
    threading.Thread(target=send_email_async, args=(user_email, severity, message), daemon=True).start()

# -------------------------
# 1. HTML TEMPLATES (REALISTIC UI UPDATES)
# -------------------------

AUTH_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Nexus Security | Authentication</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: { extend: { fontFamily: { sans: ['Inter', 'sans-serif'] }, colors: { primary: '#4f46e5', secondary: '#8b5cf6', darkbg: '#0b0f19', cardbg: '#111827' } } }
    }
  </script>
  <style>
    .glass-panel { background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }
    .input-field { transition: all 0.3s ease; }
    .input-field:focus { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15); }
  </style>
</head>
<body class="bg-gray-50 dark:bg-darkbg text-gray-900 dark:text-gray-100 min-h-screen flex transition-colors duration-300">

  <div class="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-gray-900 to-black items-center justify-center">
    <div class="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-primary/30 rounded-full blur-[120px]"></div>
    <div class="absolute bottom-[-10%] right-[-10%] w-[400px] h-[400px] bg-secondary/20 rounded-full blur-[100px]"></div>
    
    <div class="z-10 p-16 text-white max-w-2xl">
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/10 glass-panel text-primary mb-8 shadow-xl">
        <i class="fas fa-shield-halved text-4xl"></i>
      </div>
      <h1 class="text-5xl font-bold mb-6 tracking-tight leading-tight">Secure your infrastructure.<br><span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Instantly.</span></h1>
      <p class="text-gray-400 text-lg mb-10 leading-relaxed">Nexus Security provides enterprise-grade Cloud Security Posture Management (CSPM) and real-time Endpoint Detection & Response (EDR) in one unified platform.</p>
      
      <div class="grid grid-cols-2 gap-6">
        <div class="glass-panel p-5 rounded-2xl">
            <i class="fas fa-bolt text-yellow-400 text-xl mb-3"></i>
            <h3 class="font-semibold mb-1">Real-Time Alerts</h3>
            <p class="text-sm text-gray-400">Get notified immediately when threats emerge via automated workflows.</p>
        </div>
        <div class="glass-panel p-5 rounded-2xl">
            <i class="fas fa-robot text-primary text-xl mb-3"></i>
            <h3 class="font-semibold mb-1">Auto-Remediation</h3>
            <p class="text-sm text-gray-400">Let our AI engine fix critical misconfigurations instantly.</p>
        </div>
      </div>
    </div>
  </div>

  <div class="w-full lg:w-1/2 flex items-center justify-center p-8 sm:p-12 relative bg-white dark:bg-cardbg">
    <button onclick="toggleTheme()" class="absolute top-6 right-6 p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">
      <i class="fas fa-moon text-xl" id="theme-icon"></i>
    </button>

    <div class="w-full max-w-md">
      <div class="lg:hidden flex items-center gap-3 mb-8">
        <div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary"><i class="fas fa-shield-halved text-xl"></i></div>
        <span class="text-2xl font-bold tracking-tight">Nexus Security</span>
      </div>

      <div class="mb-8">
        <h2 class="text-3xl font-bold mb-2">{{ 'Create an account' if mode == 'register' else 'Welcome back' }}</h2>
        <p class="text-gray-500 dark:text-gray-400">{{ 'Start securing your assets today.' if mode == 'register' else 'Please enter your details to sign in.' }}</p>
      </div>
      
      {% if error %}
      <div class="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-r-lg text-red-700 dark:text-red-400 text-sm font-medium flex items-center shadow-sm">
        <i class="fas fa-circle-exclamation mr-3 text-lg"></i>{{ error }}
      </div>
      {% endif %}

      <form method="POST" class="space-y-5">
        {% if mode == 'register' %}
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Full Name</label>
            <input type="text" name="full_name" required placeholder="Jane Doe" class="input-field w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm">
            </div>
            <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Organization</label>
            <input type="text" name="org_name" required placeholder="Acme Corp" class="input-field w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm">
            </div>
        </div>
        {% endif %}
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Email Address</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="fas fa-envelope text-gray-400 text-sm"></i></div>
            <input type="email" name="email" required placeholder="name@company.com" class="input-field w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm">
          </div>
        </div>
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
            {% if mode == 'login' %}<a href="#" class="text-xs font-medium text-primary hover:text-indigo-500">Forgot password?</a>{% endif %}
          </div>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="fas fa-lock text-gray-400 text-sm"></i></div>
            <input type="password" name="password" required placeholder="••••••••" class="input-field w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm">
          </div>
        </div>
        
        <button type="submit" class="w-full mt-2 py-2.5 px-4 bg-primary hover:bg-indigo-500 text-white font-medium rounded-lg shadow-lg shadow-primary/30 transform hover:-translate-y-0.5 transition-all duration-200 text-sm">
          {{ 'Sign Up' if mode == 'register' else 'Sign In' }}
        </button>
      </form>

      <div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-800 text-center text-sm text-gray-500 dark:text-gray-400">
        {% if mode == 'login' %}
          Don't have an account? <a href="/register" class="font-semibold text-primary hover:text-indigo-400 transition-colors">Create one now</a>
        {% else %}
          Already have an account? <a href="/login" class="font-semibold text-primary hover:text-indigo-400 transition-colors">Sign in to your dashboard</a>
        {% endif %}
      </div>
    </div>
  </div>

  <script>
    function toggleTheme() { 
        document.documentElement.classList.toggle('dark');
        const isDark = document.documentElement.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        document.getElementById('theme-icon').className = isDark ? 'fas fa-sun text-xl' : 'fas fa-moon text-xl';
    }
    if(localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
        document.getElementById('theme-icon').className = 'fas fa-sun text-xl';
    }
  </script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Nexus Security | Enterprise Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: { sans: ['Inter', 'sans-serif'] },
          colors: { primary: '#4f46e5', secondary: '#8b5cf6', dark: '#0b0f19', darker: '#06090e', card: '#111827' }
        }
      }
    }
  </script>
  <style>
    /* Smooth Transitions & Utils */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
    .dark ::-webkit-scrollbar-thumb { background: #334155; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
    
    .sidebar-transition { transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    
    /* Nav Items Modernized */
    .nav-item { transition: all 0.2s ease; }
    .nav-item-active { background-color: rgba(79, 70, 229, 0.1); color: #4f46e5 !important; font-weight: 600; position: relative; }
    .dark .nav-item-active { background-color: rgba(99, 102, 241, 0.15); color: #818cf8 !important; }
    .nav-item-active::before { content: ''; position: absolute; left: -12px; top: 10%; height: 80%; width: 4px; background: #4f46e5; border-radius: 0 4px 4px 0; }
    .dark .nav-item-active::before { background: #818cf8; }
    
    .glass-modal { background: rgba(0,0,0,0.5); backdrop-filter: blur(8px); }
    .animate-fade-in { animation: fadeIn 0.3s ease-out forwards; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
    
    /* Enterprise Table Styles */
    .table-custom { width: 100%; text-align: left; border-collapse: separate; border-spacing: 0; }
    .table-custom th { padding: 14px 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }
    .dark .table-custom th { color: #94a3b8; border-color: #334155; background: #0f172a; }
    .table-custom td { padding: 16px 20px; font-size: 13px; color: #334155; border-bottom: 1px solid #f1f5f9; transition: background 0.2s; }
    .dark .table-custom td { color: #cbd5e1; border-color: #1e293b; }
    .table-custom tbody tr:hover td { background-color: #f8fafc; }
    .dark .table-custom tbody tr:hover td { background-color: #1e293b; }
    
    /* Polished Badges */
    .badge-c { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; border: 1px solid transparent; }
    .bg-crit { background: #fef2f2; color: #b91c1c; border-color: #fecaca; } .dark .bg-crit { background: rgba(185,28,28,0.15); color: #fca5a5; border-color: rgba(248,113,113,0.2); }
    .bg-high { background: #fff7ed; color: #c2410c; border-color: #fed7aa; } .dark .bg-high { background: rgba(194,65,12,0.15); color: #fdba74; border-color: rgba(251,146,60,0.2); }
    .bg-warn { background: #fefce8; color: #a16207; border-color: #fef08a; } .dark .bg-warn { background: rgba(161,98,7,0.15); color: #fde047; border-color: rgba(250,204,21,0.2); }
    .bg-ok { background: #f0fdf4; color: #15803d; border-color: #bbf7d0; }   .dark .bg-ok { background: rgba(21,128,61,0.15); color: #86efac; border-color: rgba(74,222,128,0.2); }
    .bg-info { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; } .dark .bg-info { background: rgba(29,78,216,0.15); color: #93c5fd; border-color: rgba(96,165,250,0.2); }

    /* Switch Component */
    .toggle-checkbox:checked { right: 0; border-color: #4f46e5; }
    .toggle-checkbox:checked + .toggle-label { background-color: #4f46e5; }
    
    /* Vis Network Tooltip Styling overide */
    div.vis-tooltip {
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #f1f5f9 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 12px !important;
        padding: 10px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
    }
  </style>
</head>
<body class="bg-slate-50 dark:bg-dark text-slate-800 dark:text-slate-200 h-screen overflow-hidden flex transition-colors duration-200">

  <aside id="sidebar" class="sidebar-transition w-64 bg-white dark:bg-card border-r border-slate-200 dark:border-slate-800 flex flex-col h-full flex-shrink-0 z-20 shadow-sm relative">
    <div class="h-16 flex items-center justify-between px-6 border-b border-slate-200 dark:border-slate-800">
      <div class="flex items-center gap-3 overflow-hidden">
        <div class="w-8 h-8 rounded bg-primary/10 flex items-center justify-center text-primary flex-shrink-0"><i class="fas fa-shield-halved"></i></div>
        <span class="font-bold text-lg tracking-tight whitespace-nowrap logo-text">Nexus</span>
      </div>
      <button onclick="toggleSidebar()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
        <i class="fas fa-bars"></i>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto py-6 px-4 space-y-8">
      <div>
        <p class="px-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3 nav-category">Posture Management</p>
        <nav class="space-y-1">
          <button onclick="switchTab('dashboard')" id="tab-dashboard" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 nav-item-active">
            <i class="fas fa-chart-pie w-5 text-center"></i><span class="nav-text font-medium">Dashboard</span>
          </button>
          <button onclick="switchTab('alerts')" id="tab-alerts" class="nav-item w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <div class="flex items-center gap-3"><i class="fas fa-bell w-5 text-center"></i><span class="nav-text font-medium">Alerts</span></div>
            <span class="nav-text bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 text-[10px] font-bold px-2 py-0.5 rounded-full">NEW</span>
          </button>
          <button onclick="switchTab('findings')" id="tab-findings" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-list-check w-5 text-center"></i><span class="nav-text font-medium">Findings</span>
          </button>
          <button onclick="switchTab('assets')" id="tab-assets" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-server w-5 text-center"></i><span class="nav-text font-medium">Asset Inventory</span>
          </button>
        </nav>
      </div>

      <div>
        <p class="px-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3 nav-category">Endpoint & Threats</p>
        <nav class="space-y-1">
          <button onclick="switchTab('endpoints')" id="tab-endpoints" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-laptop-security w-5 text-center"></i><span class="nav-text font-medium">Device Fleet</span>
          </button>
          <button onclick="switchTab('live-monitoring')" id="tab-live-monitoring" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-wave-square w-5 text-center"></i><span class="nav-text font-medium">Live Telemetry</span>
          </button>
          <button onclick="switchTab('threats')" id="tab-threats" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-shield-virus w-5 text-center"></i><span class="nav-text font-medium">Detections</span>
          </button>
        </nav>
      </div>

      <div>
        <p class="px-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3 nav-category">Intelligence</p>
        <nav class="space-y-1">
          <button onclick="switchTab('darkweb')" id="tab-darkweb" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 font-medium">
            <i class="fas fa-user-secret w-5 text-center"></i><span class="nav-text font-medium">Dark Web Intel</span>
          </button>
          <button onclick="switchTab('attack-graph')" id="tab-attack-graph" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-network-wired w-5 text-center"></i><span class="nav-text font-medium">Attack Graph</span>
          </button>
          <button onclick="switchTab('compliance')" id="tab-compliance" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-file-shield w-5 text-center"></i><span class="nav-text font-medium">Compliance</span>
          </button>
          <button onclick="switchTab('identity')" id="tab-identity" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-id-badge w-5 text-center"></i><span class="nav-text font-medium">CIEM (Identity)</span>
          </button>
          <button onclick="switchTab('k8s')" id="tab-k8s" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fab fa-docker w-5 text-center"></i><span class="nav-text font-medium">KSPM</span>
          </button>
        </nav>
      </div>

      <div>
        <p class="px-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3 nav-category">Administration</p>
        <nav class="space-y-1">
          <button onclick="switchTab('integrations')" id="tab-integrations" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-puzzle-piece w-5 text-center"></i><span class="nav-text font-medium">Integrations</span>
          </button>
          <button onclick="switchTab('policies')" id="tab-policies" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-sliders w-5 text-center"></i><span class="nav-text font-medium">Policies</span>
          </button>
          <button onclick="switchTab('automation')" id="tab-automation" class="nav-item w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <i class="fas fa-bolt-lightning w-5 text-center"></i><span class="nav-text font-medium">Automation</span>
          </button>
        </nav>
      </div>
    </div>

    <div class="px-4 py-4 server-widget">
      <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-700/50">
        <div class="flex justify-between items-center mb-1.5"><span class="text-[11px] text-slate-500 font-medium">Engine CPU</span><span id="cpu-txt" class="text-[11px] font-bold text-slate-700 dark:text-slate-300">0%</span></div>
        <div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1 mb-3"><div id="cpu-bar" class="bg-primary h-1 rounded-full" style="width: 0%"></div></div>
        
        <div class="flex justify-between items-center mb-1.5"><span class="text-[11px] text-slate-500 font-medium">Engine RAM</span><span id="ram-txt" class="text-[11px] font-bold text-slate-700 dark:text-slate-300">0%</span></div>
        <div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1 mb-3"><div id="ram-bar" class="bg-secondary h-1 rounded-full" style="width: 0%"></div></div>
        
        <div class="flex items-center gap-2 mt-1 text-[11px] font-medium">
          <span class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>
          <span class="text-slate-500 dark:text-slate-400">System Healthy</span>
        </div>
      </div>
    </div>

    <div class="p-4 border-t border-slate-200 dark:border-slate-800">
      <div class="flex items-center justify-between mb-4">
         <span id="current-plan-badge" class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 user-info">FREE</span>
         <button onclick="toggleTheme()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 user-info transition-colors" title="Toggle Dark Mode"><i class="fas fa-moon"></i></button>
      </div>
      <div class="flex items-center gap-3 cursor-pointer group" onclick="switchTab('profile')">
        <div class="w-9 h-9 rounded-full bg-gradient-to-tr from-primary to-secondary text-white flex items-center justify-center font-bold text-sm flex-shrink-0 shadow-sm border border-white/10" id="p-avatar-sm">U</div>
        <div class="overflow-hidden user-info">
          <p class="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate group-hover:text-primary transition-colors">{{ user.split('@')[0] }}</p>
          <a href="/logout" class="text-xs text-slate-500 hover:text-red-500 font-medium transition-colors">Sign Out</a>
        </div>
      </div>
    </div>
  </aside>

  <main class="flex-1 flex flex-col relative overflow-hidden">
    
    <header class="h-16 px-8 flex items-center justify-between bg-white dark:bg-card border-b border-slate-200 dark:border-slate-800 z-10 shrink-0 shadow-sm">
      <h1 id="page-title" class="text-xl font-bold text-slate-800 dark:text-white tracking-tight">Security Posture</h1>
      
      <div class="flex items-center gap-4">
        <div class="hidden md:flex relative group">
            <i class="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors"></i>
            <input type="text" placeholder="Search resources, alerts..." class="pl-9 pr-4 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all w-64 text-slate-700 dark:text-slate-200">
        </div>

        <div class="h-6 w-px bg-slate-300 dark:bg-slate-700 mx-1 hidden md:block"></div>
        
        <button onclick="document.getElementById('settingsModal').style.display='flex'" class="p-2 text-slate-400 hover:text-slate-700 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors" title="Settings"><i class="fas fa-cog"></i></button>
        
        <input type="file" id="uploadInput" accept=".csv" class="hidden" onchange="handleFileSelect()">
        <button onclick="document.getElementById('uploadInput').click()" class="hidden sm:flex px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-card border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors items-center shadow-sm"><i class="fas fa-upload mr-2"></i> Upload CSV</button>
        <button onclick="downloadDemoCSV()" class="hidden sm:flex p-1.5 text-slate-400 hover:text-primary transition-colors" title="Download Demo Template"><i class="fas fa-file-csv text-lg"></i></button>
        
        <button onclick="downloadReport()" class="px-3 py-1.5 text-sm font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-card border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg shadow-sm transition flex items-center gap-2">
            <i class="fas fa-file-pdf text-red-500"></i> Report
        </button>

        <button onclick="openScanModal()" class="px-4 py-1.5 text-sm font-semibold text-white bg-primary hover:bg-indigo-600 rounded-lg shadow-md shadow-primary/20 transition-all flex items-center gap-2 transform hover:-translate-y-0.5">
          <i class="fas fa-radar"></i> Run Scan
        </button>
      </div>
    </header>

    <div id="scan-progress" class="hidden absolute top-16 left-0 w-full z-10 shadow-md">
      <div class="h-1 w-full bg-slate-200 dark:bg-slate-800">
        <div id="scan-bar" class="h-1 bg-gradient-to-r from-primary to-secondary transition-all duration-500 w-0"></div>
      </div>
      <div class="absolute top-3 right-6 bg-slate-800 dark:bg-white text-white dark:text-slate-900 text-xs px-3 py-1.5 rounded-md shadow-lg font-medium tracking-wide flex items-center gap-2">
        <i class="fas fa-circle-notch fa-spin"></i> <span id="scan-msg">Initializing...</span>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-6 md:p-8">
      
      <div class="mb-8 bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm flex items-center overflow-hidden h-12 relative group">
        <div class="bg-red-500 text-white font-bold text-xs px-5 h-full flex items-center shrink-0 uppercase tracking-wider gap-2 shadow-inner z-10 relative">
          <span class="relative flex h-2 w-2 mr-1"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-white"></span></span>
          LIVE ALERTS
        </div>
        <div class="flex-1 overflow-hidden relative h-full bg-gradient-to-r from-red-50 to-transparent dark:from-red-900/10 dark:to-transparent">
          <div id="alert-ticker-content" class="absolute flex flex-col w-full px-5 h-full animate-[slideUp_10s_infinite]">
            <div class="h-12 flex items-center text-sm font-medium text-slate-500">Waiting for telemetry data...</div>
          </div>
        </div>
      </div>
      <style>@keyframes slideUp { 0%, 20% { transform: translateY(0); } 25%, 45% { transform: translateY(-48px); } 50%, 70% { transform: translateY(-96px); } 75%, 95% { transform: translateY(-144px); } }</style>

      <div id="view-dashboard" class="space-y-6 animate-fade-in">
        
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
            <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-red-500/10 to-transparent rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110"></div>
            <div class="flex justify-between items-start mb-2">
                <p class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Critical Issues</p>
                <i class="fas fa-fire text-red-500"></i>
            </div>
            <div class="flex items-end justify-between mt-1">
              <h2 id="kpi-crit" class="text-4xl font-extrabold text-slate-800 dark:text-white">--</h2>
              <div class="flex gap-2 relative z-10">
                <button onclick="previewFixCritical()" class="text-[10px] font-bold px-2 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-600 dark:text-slate-300 transition-colors uppercase">Preview</button>
                <button onclick="fixAllCritical()" class="text-[10px] font-bold px-2 py-1 bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 rounded transition-colors uppercase border border-red-200 dark:border-red-800/50"><i class="fas fa-wrench mr-1"></i> Fix</button>
              </div>
            </div>
          </div>
          
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow flex items-center justify-between">
            <div>
              <p class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">AI Risk Score</p>
              <h2 id="kpi-score" class="text-4xl font-extrabold text-slate-800 dark:text-white">--</h2>
              <p class="text-xs text-slate-400 mt-1">Platform wide posture</p>
            </div>
            <div id="risk-circle" class="w-16 h-16 rounded-full border-[5px] border-slate-100 dark:border-slate-800 flex items-center justify-center text-xl font-bold shadow-inner">--</div>
          </div>

          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div class="absolute right-4 top-1/2 transform -translate-y-1/2 text-primary/10 dark:text-primary/5 transition-transform hover:scale-110"><i class="fas fa-server text-6xl"></i></div>
            <p class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Active Agents</p>
            <h2 id="kpi-endpoints" class="text-3xl font-extrabold text-primary">0</h2>
            <p class="text-xs font-medium text-emerald-600 dark:text-emerald-400 mt-2 bg-emerald-50 dark:bg-emerald-900/20 inline-block px-2 py-0.5 rounded"><i class="fas fa-arrow-up mr-1"></i>EDR Protected</p>
          </div>

          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div class="absolute right-4 top-1/2 transform -translate-y-1/2 text-purple-500/10 dark:text-purple-500/5 transition-transform hover:scale-110"><i class="fas fa-spider text-6xl"></i></div>
            <p class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Dark Web Intel</p>
            <h2 id="kpi-darkweb" class="text-3xl font-extrabold text-purple-600 dark:text-purple-400">0</h2>
            <p class="text-xs font-medium text-slate-500 mt-2">Creds & API Leaks</p>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow"><div class="flex justify-between items-center mb-4"><h3 class="text-sm font-bold text-slate-700 dark:text-slate-300">Risk by Service</h3><i class="fas fa-cloud text-slate-400"></i></div><div class="h-64"><canvas id="polarChart"></canvas></div></div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow"><div class="flex justify-between items-center mb-4"><h3 class="text-sm font-bold text-slate-700 dark:text-slate-300">30 Day Trend</h3><i class="fas fa-chart-line text-slate-400"></i></div><div class="h-64"><canvas id="lineChart"></canvas></div></div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow"><div class="flex justify-between items-center mb-4"><h3 class="text-sm font-bold text-slate-700 dark:text-slate-300">Severity Distribution</h3><i class="fas fa-chart-bar text-slate-400"></i></div><div class="h-64"><canvas id="barChart"></canvas></div></div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm hover:shadow-md transition-shadow"><div class="flex justify-between items-center mb-4"><h3 class="text-sm font-bold text-slate-700 dark:text-slate-300">Compliance Status</h3><i class="fas fa-shield-check text-slate-400"></i></div><div class="h-64 relative"><canvas id="pieChart"></canvas></div></div>
        </div>

        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm hover:shadow-md transition-shadow overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 flex justify-between items-center">
            <h3 class="font-bold text-slate-800 dark:text-white"><i class="fas fa-satellite-dish text-primary mr-2"></i> External Threat Intelligence</h3>
            <button class="text-xs font-semibold text-primary hover:text-indigo-600 transition-colors">View All Feed &rarr;</button>
          </div>
          <div class="p-0 overflow-x-auto" id="threatTable">
            <div class="p-8 text-slate-500 text-sm text-center flex flex-col items-center"><i class="fas fa-inbox text-3xl mb-3 text-slate-300 dark:text-slate-600"></i> Run a scan to load live intel data.</div>
          </div>
        </div>
      </div>

      <div id="view-alerts" class="hidden space-y-6 animate-fade-in">
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/20">
            <h3 class="font-bold text-slate-800 dark:text-white"><i class="fas fa-bell text-yellow-500 mr-2"></i> System Security Alerts Log</h3>
            <div class="flex gap-2 items-center">
              <span id="daemon-status-indicator" class="text-xs font-bold px-2 py-1 rounded bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400 mr-2">Daemon: Stopped</span>
              <button class="px-3 py-1.5 bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800/50 rounded-lg text-xs font-semibold shadow-sm transition-colors" onclick="toggleAlertDaemon('start')"><i class="fas fa-play mr-1.5"></i> Start</button>
              <button class="px-3 py-1.5 bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800/50 rounded-lg text-xs font-semibold shadow-sm transition-colors" onclick="toggleAlertDaemon('stop')"><i class="fas fa-stop mr-1.5"></i> Stop</button>
              <button class="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold shadow-sm transition-colors" onclick="loadAlerts()"><i class="fas fa-sync-alt mr-1.5"></i> Refresh</button>
            </div>
          </div>
          <div class="overflow-x-auto" id="alertsTableContainer">
            <div class="p-8 text-center text-slate-500 text-sm"><i class="fas fa-circle-notch fa-spin text-xl mb-3"></i><br>Loading alerts...</div>
          </div>
        </div>
      </div>

      <div id="view-endpoints" class="hidden space-y-6 animate-fade-in">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm">
            <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase mb-4"><i class="fas fa-shield-virus mr-2 text-primary"></i>Antivirus (EDR)</h3>
            <div class="flex justify-between items-center mb-2"><span class="text-sm font-medium">Active Agents:</span><b id="av-count" class="text-lg">--</b></div>
            <div class="flex justify-between items-center"><span class="text-sm font-medium">Threats Blocked:</span><span class="badge-c bg-ok">24</span></div>
            <button class="w-full mt-5 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-sm font-semibold rounded-lg transition-colors" onclick="alert('Command sent to fleet')">Run Fleet Scan</button>
          </div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm">
            <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase mb-4"><i class="fas fa-hard-drive mr-2 text-secondary"></i>Disk Encryption</h3>
            <div class="flex justify-between items-center mb-2"><span class="text-sm font-medium">Encrypted:</span><b id="enc-rate" class="text-lg text-emerald-600 dark:text-emerald-400">--%</b></div>
            <div class="flex justify-between items-center"><span class="text-sm font-medium">At Risk (Unencrypted):</span><span id="enc-risk" class="badge-c bg-crit">--</span></div>
          </div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm">
            <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase mb-4"><i class="fas fa-wall-brick mr-2 text-yellow-500"></i>Host Firewall</h3>
            <div class="flex justify-between items-center mb-2"><span class="text-sm font-medium">Policy Enforced:</span><b id="fw-count" class="text-lg text-emerald-600 dark:text-emerald-400">--</b></div>
            <div class="flex justify-between items-center"><span class="text-sm font-medium">Disabled / Offline:</span><span id="fw-disabled" class="badge-c bg-warn">--</span></div>
          </div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 shadow-sm">
            <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase mb-4"><i class="fas fa-ban mr-2 text-red-500"></i>App Control</h3>
            <div class="text-sm mb-2 flex justify-between"><span class="text-slate-500">Blocked Hashes:</span> <span class="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">Tor, Keygen</span></div>
            <div class="text-sm flex justify-between"><span class="text-slate-500">Violations:</span> <b class="text-red-500">5 This Week</b></div>
          </div>
        </div>
        
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/20">
            <h3 class="font-bold text-slate-800 dark:text-white">Endpoint Inventory & Status</h3>
            <button class="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-xs font-semibold shadow-sm transition-colors" onclick="loadEndpoints()"><i class="fas fa-sync-alt mr-1.5"></i> Refresh Data</button>
          </div>
          <div class="overflow-x-auto" id="endpointTable"><div class="p-8 text-center text-slate-500 text-sm">Loading endpoints...</div></div>
        </div>
      </div>

      <div id="view-live-monitoring" class="hidden space-y-6 animate-fade-in">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 text-center shadow-sm">
            <p class="text-xs font-bold text-slate-500 uppercase mb-3 tracking-wider"><i class="fas fa-satellite-dish mr-1"></i> Aggregator Status</p>
            <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400 flex items-center justify-center gap-2"><span class="relative flex h-2.5 w-2.5"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span></span> RECEIVING</div>
            <p class="text-[10px] text-slate-400 mt-2 font-mono">Last ping: <span id="live-last-update">--</span></p>
          </div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 text-center shadow-sm">
            <p class="text-xs font-bold text-slate-500 uppercase mb-2 tracking-wider"><i class="fas fa-microchip mr-1"></i> Fleet CPU Avg</p>
            <div id="live-cpu" class="text-3xl font-extrabold text-primary mb-3">--</div>
            <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden"><div id="live-cpu-bar" class="bg-primary h-full rounded-full transition-all duration-500"></div></div>
          </div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 text-center shadow-sm">
            <p class="text-xs font-bold text-slate-500 uppercase mb-2 tracking-wider"><i class="fas fa-memory mr-1"></i> Fleet RAM Avg</p>
            <div id="live-ram" class="text-3xl font-extrabold text-secondary mb-3">--</div>
            <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden"><div id="live-ram-bar" class="bg-secondary h-full rounded-full transition-all duration-500"></div></div>
          </div>
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-5 text-center shadow-sm">
            <p class="text-xs font-bold text-slate-500 uppercase mb-2 tracking-wider"><i class="fas fa-network-wired mr-1"></i> Traffic</p>
            <div id="live-network" class="text-2xl font-extrabold text-slate-700 dark:text-slate-200 mb-2">-- MB/s</div>
            <div class="text-[11px] font-semibold text-slate-500 flex justify-center gap-4 mt-2 bg-slate-50 dark:bg-slate-800/50 py-1.5 rounded">
              <span><i class="fas fa-arrow-up text-primary mr-1"></i><span id="upload-speed">0</span></span>
              <span><i class="fas fa-arrow-down text-emerald-500 mr-1"></i><span id="download-speed">0</span></span>
            </div>
          </div>
        </div>
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm p-6 relative overflow-hidden">
           <div class="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-yellow-500/5 to-transparent rounded-bl-full pointer-events-none"></div>
           <h3 class="font-bold text-slate-800 dark:text-white mb-5 flex items-center"><i class="fas fa-bolt text-yellow-500 mr-2 text-lg"></i> Raw Telemetry Stream</h3>
           <div id="live-events" class="space-y-3 max-h-96 overflow-y-auto pr-3 scroll-smooth font-mono text-xs">Loading encrypted stream...</div>
        </div>
      </div>

      <div id="view-threats" class="hidden space-y-6 animate-fade-in">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div class="bg-white dark:bg-card p-6 rounded-xl border-t-4 border-t-red-500 shadow-sm text-center"><p class="text-xs uppercase text-slate-500 font-bold mb-2 tracking-wider">Active Threats</p><div id="threats-active" class="text-4xl font-extrabold text-red-500">0</div></div>
          <div class="bg-white dark:bg-card p-6 rounded-xl border-t-4 border-t-emerald-500 shadow-sm text-center"><p class="text-xs uppercase text-slate-500 font-bold mb-2 tracking-wider">Blocked via EDR</p><div id="threats-blocked" class="text-4xl font-extrabold text-emerald-600 dark:text-emerald-400">0</div></div>
          <div class="bg-white dark:bg-card p-6 rounded-xl border-t-4 border-t-yellow-500 shadow-sm text-center"><p class="text-xs uppercase text-slate-500 font-bold mb-2 tracking-wider">In Quarantine</p><div id="threats-quarantine" class="text-4xl font-extrabold text-slate-800 dark:text-white">0</div></div>
          <div class="bg-white dark:bg-card p-6 rounded-xl border-t-4 border-t-slate-400 shadow-sm text-center"><p class="text-xs uppercase text-slate-500 font-bold mb-2 tracking-wider">False Positives</p><div id="threats-false" class="text-4xl font-extrabold text-slate-400">0</div></div>
        </div>
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden">
           <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold">Recent Detection Sandbox Log</h3></div>
           <div id="threatDetectionTable" class="overflow-x-auto"></div>
        </div>
      </div>

      <div id="view-darkweb" class="hidden space-y-6 animate-fade-in">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div class="bg-white dark:bg-card p-6 rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm relative overflow-hidden"><div class="absolute right-0 bottom-0 text-purple-500/10 p-2"><i class="fas fa-key text-5xl"></i></div><p class="text-xs uppercase text-slate-500 font-bold tracking-wider">Credential Leaks</p><h2 class="text-4xl font-extrabold mt-3 text-slate-800 dark:text-white">12</h2></div>
          <div class="bg-white dark:bg-card p-6 rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm relative overflow-hidden"><div class="absolute right-0 bottom-0 text-red-500/10 p-2"><i class="fas fa-code text-5xl"></i></div><p class="text-xs uppercase text-slate-500 font-bold tracking-wider">API Key Exposures</p><h2 class="text-4xl font-extrabold text-red-500 mt-3">3</h2></div>
          <div class="bg-white dark:bg-card p-6 rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm relative overflow-hidden"><div class="absolute right-0 bottom-0 text-yellow-500/10 p-2"><i class="fas fa-globe text-5xl"></i></div><p class="text-xs uppercase text-slate-500 font-bold tracking-wider">Domain Mentions</p><h2 class="text-4xl font-extrabold text-yellow-600 dark:text-yellow-500 mt-3">45</h2></div>
          <div class="bg-white dark:bg-card p-6 rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm relative overflow-hidden"><div class="absolute right-0 bottom-0 text-slate-500/10 p-2"><i class="fas fa-bug text-5xl"></i></div><p class="text-xs uppercase text-slate-500 font-bold tracking-wider">Stealer Logs</p><h2 class="text-4xl font-extrabold mt-3 text-slate-800 dark:text-white">2</h2></div>
        </div>
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden">
           <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold flex items-center"><i class="fas fa-mask text-purple-500 mr-2 text-lg"></i> Live Onion & Telegram Scrapes</h3></div>
           <div id="detailedDarkWebTable" class="overflow-x-auto"></div>
        </div>
      </div>

      <div id="view-integrations" class="hidden animate-fade-in">
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-8 shadow-sm">
          <h3 class="text-xl font-bold mb-2">Connect Your Infrastructure</h3>
          <p class="text-slate-500 text-sm mb-8 max-w-2xl">Deploy API hooks into your cloud environments, SIEMs, and issue trackers to enable continuous monitoring and automated remediation.</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            
            <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-center flex flex-col items-center hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all bg-slate-50/50 dark:bg-slate-800/20">
              <div class="w-16 h-16 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center shadow-sm mb-4 border border-slate-100 dark:border-slate-700"><i class="fab fa-aws text-3xl text-[#FF9900]"></i></div>
              <h4 class="font-bold mb-2 text-slate-800 dark:text-slate-100">AWS</h4>
              <span id="status-aws" class="badge-c bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400 mb-5">Disconnected</span>
              <button onclick="connectCloud('AWS')" class="w-full py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors mt-auto shadow-sm">Configure</button>
            </div>
            
            <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-center flex flex-col items-center hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all bg-slate-50/50 dark:bg-slate-800/20">
              <div class="w-16 h-16 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center shadow-sm mb-4 border border-slate-100 dark:border-slate-700"><i class="fab fa-microsoft text-3xl text-[#00A4EF]"></i></div>
              <h4 class="font-bold mb-2 text-slate-800 dark:text-slate-100">Azure</h4>
              <span id="status-azure" class="badge-c bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400 mb-5">Disconnected</span>
              <button onclick="openGenericIntegrationModal('Azure')" class="w-full py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors mt-auto shadow-sm">Configure</button>
            </div>
            
            <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-center flex flex-col items-center hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all bg-slate-50/50 dark:bg-slate-800/20">
              <div class="w-16 h-16 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center shadow-sm mb-4 border border-slate-100 dark:border-slate-700"><i class="fas fa-database text-3xl text-emerald-500"></i></div>
              <h4 class="font-bold mb-2 text-slate-800 dark:text-slate-100">Splunk</h4>
              <span id="status-splunk" class="badge-c bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400 mb-5">Disconnected</span>
              <button onclick="openGenericIntegrationModal('Splunk')" class="w-full py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors mt-auto shadow-sm">Configure</button>
            </div>
            
            <div class="border border-slate-200 dark:border-slate-700 rounded-xl p-6 text-center flex flex-col items-center hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all bg-slate-50/50 dark:bg-slate-800/20">
              <div class="w-16 h-16 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center shadow-sm mb-4 border border-slate-100 dark:border-slate-700"><i class="fab fa-jira text-3xl text-blue-500"></i></div>
              <h4 class="font-bold mb-2 text-slate-800 dark:text-slate-100">Jira</h4>
              <span id="status-jira" class="badge-c bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400 mb-5">Disconnected</span>
              <button onclick="openGenericIntegrationModal('Jira')" class="w-full py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 text-sm font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors mt-auto shadow-sm">Configure</button>
            </div>
          </div>
        </div>
      </div>

      <div id="view-policies" class="hidden animate-fade-in"><div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden"><div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold">Security Policies & Framework Mapping</h3></div><div id="policy-list" class="overflow-x-auto"></div></div></div>

      <div id="view-automation" class="hidden space-y-6 animate-fade-in">
        <div class="grid grid-cols-1 md:grid-cols-5 gap-6">
          <div class="md:col-span-2 bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-8 shadow-sm">
             <div class="w-12 h-12 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 text-primary flex items-center justify-center text-xl mb-4"><i class="fas fa-robot"></i></div>
             <h3 class="text-xl font-bold mb-3">Auto-Remediation Engine</h3>
             <p class="text-sm text-slate-500 dark:text-slate-400 mb-8 leading-relaxed">Give Nexus permission to automatically fix critical misconfigurations like public S3 buckets or disabled multi-factor authentication without requiring human approval.</p>
             <div class="flex items-center justify-between p-5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700">
               <div>
                   <p class="font-semibold text-slate-800 dark:text-slate-200">Enable Engine</p>
                   <p class="text-xs text-slate-500 mt-1">Status: <span id="auto-status" class="font-bold text-slate-700 dark:text-slate-300">Disabled</span></p>
               </div>
               <div class="relative inline-block w-12 mr-2 align-middle select-none transition duration-200 ease-in">
                  <input type="checkbox" id="auto-fix-toggle" onchange="toggleAutoFix()" class="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer transition-transform duration-200 z-10 shadow-sm"/>
                  <label for="auto-fix-toggle" class="toggle-label block overflow-hidden h-6 rounded-full bg-slate-300 dark:bg-slate-600 cursor-pointer"></label>
               </div>
             </div>
          </div>
          <div class="md:col-span-3 bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden flex flex-col">
             <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 shrink-0"><h3 class="font-bold"><i class="fas fa-list-ul mr-2 text-slate-400"></i>Engine Action Log</h3></div>
             <div id="autoLogsTable" class="overflow-x-auto flex-1 p-0">No actions yet.</div>
          </div>
        </div>
      </div>

      <div id="view-compliance" class="hidden animate-fade-in"><div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden"><div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold text-lg mb-1">Compliance Scorecards</h3><p class="text-xs text-slate-500">Continuous drift analysis against regulatory frameworks.</p></div><div id="complianceTable" class="overflow-x-auto"></div></div></div>
      <div id="view-identity" class="hidden animate-fade-in"><div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden"><div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold">Identity & Access Governance (CIEM)</h3></div><div id="identityTable" class="overflow-x-auto"></div></div></div>
      <div id="view-k8s" class="hidden animate-fade-in"><div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden"><div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold">Kubernetes Security Posture (KSPM)</h3></div><div id="k8sTable" class="overflow-x-auto"></div></div></div>
      <div id="view-findings" class="hidden animate-fade-in"><div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden"><div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold">Raw Findings Register</h3></div><div id="findingsTable" class="overflow-x-auto"></div></div></div>
      <div id="view-assets" class="hidden animate-fade-in"><div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm overflow-hidden"><div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20"><h3 class="font-bold">Unified Asset Inventory</h3></div><div id="assetsTable" class="overflow-x-auto"></div></div></div>

      <div id="view-attack-graph" class="hidden animate-fade-in">
        <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-sm h-[750px] flex flex-col overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 flex justify-between items-center shrink-0">
              <h3 class="font-bold"><i class="fas fa-project-diagram mr-2 text-primary"></i> Exploit Path Visualizer</h3>
              <div class="flex gap-4 text-xs font-semibold text-slate-500">
                  <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-full bg-red-500"></span> Critical Node</span>
                  <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-full bg-emerald-500"></span> Secured</span>
              </div>
          </div>
          <div id="mynetwork" class="flex-1 w-full min-h-[600px] bg-slate-50 dark:bg-black/20"></div>
        </div>
      </div>

      <div id="view-profile" class="hidden space-y-6 animate-fade-in">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-8 shadow-sm flex flex-col items-center text-center relative overflow-hidden">
             <div class="absolute top-0 w-full h-24 bg-gradient-to-r from-primary/80 to-secondary/80"></div>
             <div class="w-28 h-28 rounded-full bg-white dark:bg-card p-1.5 z-10 mt-6 mb-4 shadow-lg">
                <div class="w-full h-full rounded-full bg-gradient-to-tr from-slate-200 to-slate-100 dark:from-slate-700 dark:to-slate-600 text-slate-700 dark:text-slate-300 flex items-center justify-center text-4xl font-bold shadow-inner" id="p-avatar">U</div>
             </div>
             <h3 id="p-display-name" class="text-2xl font-bold text-slate-800 dark:text-white mb-1">Loading...</h3>
             <p id="p-email" class="text-slate-500 text-sm mb-4 font-mono">...</p>
             <span id="p-role" class="px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-full text-xs font-bold tracking-widest uppercase mb-8 border border-slate-200 dark:border-slate-700">Viewer</span>
             <div class="mt-auto w-full p-4 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl border border-indigo-100 dark:border-indigo-800/30 flex justify-between items-center">
                 <div class="text-left"><p class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Current Plan</p><p id="p-tier" class="text-primary font-extrabold text-lg">Free</p></div>
                 <button onclick="switchTab('subscription')" class="text-xs bg-white dark:bg-slate-800 px-3 py-1.5 rounded-lg font-semibold text-slate-700 dark:text-slate-200 shadow-sm border border-slate-200 dark:border-slate-700 hover:text-primary">Upgrade</button>
             </div>
          </div>

          <div class="lg:col-span-2 space-y-6">
              <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-8 shadow-sm">
                <h3 class="text-lg font-bold mb-6 pb-4 border-b border-slate-100 dark:border-slate-800">Account Details</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Full Name</label>
                    <input type="text" id="edit-name" class="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all">
                  </div>
                  <div>
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Organization</label>
                    <input type="text" id="edit-org" class="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all">
                  </div>
                </div>
                <div class="flex justify-end"><button onclick="updateProfile()" class="px-6 py-2.5 bg-slate-900 hover:bg-black dark:bg-white dark:hover:bg-slate-200 dark:text-slate-900 text-white font-semibold rounded-lg shadow-md transition-colors">Save Changes</button></div>
              </div>

              <div class="bg-white dark:bg-card rounded-xl border border-slate-200 dark:border-slate-700/80 p-8 shadow-sm">
                <h3 class="text-lg font-bold mb-2">API Access Token</h3>
                <p class="text-sm text-slate-500 mb-6 max-w-lg">Generate a personal access token to interact with the Nexus Security API. Keep this secret.</p>
                <div class="flex gap-3">
                  <div class="relative flex-1">
                      <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><i class="fas fa-key text-slate-400"></i></div>
                      <input type="text" id="api-token-box" readonly class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 font-mono text-sm outline-none focus:ring-2 focus:ring-slate-400 cursor-copy" placeholder="No active token">
                  </div>
                  <button onclick="generateToken()" class="px-5 py-2.5 bg-primary hover:bg-indigo-600 text-white font-semibold rounded-lg shadow-md transition-colors whitespace-nowrap"><i class="fas fa-arrows-rotate mr-2"></i>Roll Token</button>
                </div>
              </div>
          </div>
        </div>
      </div>
      
      <div id="view-subscription" class="hidden animate-fade-in">
        <div class="text-center max-w-2xl mx-auto mb-10 mt-6">
          <h2 class="text-3xl font-bold mb-3">Upgrade your Security</h2>
          <p class="text-slate-500">Choose the plan that fits your organization's needs.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          <div class="bg-white dark:bg-card rounded-2xl border border-slate-200 dark:border-slate-700 p-8 text-center flex flex-col hover:shadow-md transition-shadow">
             <h3 class="text-lg font-bold mb-2">Starter</h3>
             <div class="text-4xl font-extrabold mb-6">Free</div>
             <ul class="text-left space-y-4 mb-8 text-sm text-slate-600 dark:text-slate-400 flex-1">
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Basic Cloud Scanning</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Asset Inventory</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Manual Remediation</li>
             </ul>
             <button id="btn-tier-Free" onclick="upgradePlan('Free')" class="w-full py-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">Select Free</button>
          </div>
          
          <div class="bg-white dark:bg-card rounded-2xl border-2 border-primary shadow-xl shadow-primary/10 p-8 text-center relative flex flex-col transform hover:-translate-y-1 transition-transform">
             <div class="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-primary text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Recommended</div>
             <h3 class="text-lg font-bold mb-2 text-primary">Professional</h3>
             <div class="text-4xl font-extrabold mb-6">$99<span class="text-lg text-slate-400 font-normal">/mo</span></div>
             <ul class="text-left space-y-4 mb-8 text-sm text-slate-600 dark:text-slate-400 flex-1">
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Everything in Free</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> PDF Executive Reports</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Continuous Monitoring</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Basic EDR</li>
             </ul>
             <button id="btn-tier-Pro" onclick="upgradePlan('Pro')" class="w-full py-2.5 rounded-lg bg-primary hover:bg-indigo-600 text-white font-medium transition shadow-md">Upgrade to Pro</button>
          </div>
          
          <div class="bg-white dark:bg-card rounded-2xl border border-slate-200 dark:border-slate-700 p-8 text-center flex flex-col hover:shadow-md transition-shadow">
             <h3 class="text-lg font-bold mb-2">Enterprise</h3>
             <div class="text-4xl font-extrabold mb-6">$299<span class="text-lg text-slate-400 font-normal">/mo</span></div>
             <ul class="text-left space-y-4 mb-8 text-sm text-slate-600 dark:text-slate-400 flex-1">
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Everything in Pro</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Auto-Remediation (Bot)</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Dark Web Intel</li>
               <li><i class="fas fa-check text-emerald-500 mr-2"></i> Full EDR Suite + API</li>
             </ul>
             <button id="btn-tier-Enterprise" onclick="upgradePlan('Enterprise')" class="w-full py-2.5 rounded-lg bg-slate-900 hover:bg-black dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 text-white font-medium transition shadow-md">Upgrade to Enterprise</button>
          </div>
        </div>
      </div>

    </div>
  </main>
  
  <div id="epModal" class="hidden fixed inset-0 z-50 glass-modal flex justify-center items-center px-4">
    <div class="bg-white dark:bg-card w-full max-w-lg p-0 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 transform transition-all overflow-hidden flex flex-col">
       <div class="px-6 py-5 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 flex justify-between items-start">
         <div><h3 id="m-hostname" class="text-xl font-extrabold flex items-center gap-2"><i class="fas fa-laptop text-slate-400"></i> Hostname</h3><p id="m-ip" class="text-sm font-mono text-slate-500 mt-1">IP: --</p></div>
         <span id="m-status-badge" class="badge-c bg-ok mt-1">Healthy</span>
       </div>
       <div class="p-6">
           <div class="grid grid-cols-1 gap-4 mb-8">
              <div class="flex justify-between items-center p-4 rounded-xl border border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-800/20 text-sm">
                  <span class="font-semibold text-slate-700 dark:text-slate-300"><i class="fas fa-shield-virus w-6 text-slate-400"></i> Antivirus Engine</span><span id="m-av" class="badge-c bg-ok">Active</span>
              </div>
              <div class="flex justify-between items-center p-4 rounded-xl border border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-800/20 text-sm">
                  <span class="font-semibold text-slate-700 dark:text-slate-300"><i class="fas fa-wall-brick w-6 text-slate-400"></i> Host Firewall</span><input type="checkbox" id="m-fw-toggle" class="rounded text-primary focus:ring-primary w-4 h-4" checked disabled>
              </div>
              <div class="flex justify-between items-center p-4 rounded-xl border border-slate-100 dark:border-slate-700/50 bg-slate-50/50 dark:bg-slate-800/20 text-sm">
                  <span class="font-semibold text-slate-700 dark:text-slate-300"><i class="fas fa-hard-drive w-6 text-slate-400"></i> Volume Encryption</span><span id="m-enc" class="badge-c bg-ok">Encrypted</span>
              </div>
           </div>
           
           <h4 class="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Command & Control</h4>
           <div class="grid grid-cols-2 gap-3 mb-6">
             <button class="py-2.5 bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40 dark:text-red-400 rounded-lg text-sm font-bold transition-colors border border-red-100 dark:border-red-900/50 shadow-sm" onclick="executeEDR('isolate')"><i class="fas fa-biohazard mr-1"></i> Isolate Host</button>
             <button class="py-2.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/20 dark:hover:bg-indigo-900/40 dark:text-indigo-400 rounded-lg text-sm font-bold transition-colors border border-indigo-100 dark:border-indigo-900/50 shadow-sm" onclick="executeEDR('unisolate')"><i class="fas fa-unlock mr-1"></i> Unisolate</button>
             <button class="py-2.5 bg-white dark:bg-slate-800 text-slate-700 hover:bg-slate-50 border border-slate-200 dark:border-slate-700 dark:hover:bg-slate-700 dark:text-slate-300 rounded-lg text-sm font-bold transition-colors shadow-sm" onclick="executeEDR('scan')"><i class="fas fa-search mr-1"></i> Deep Scan</button>
             <button class="py-2.5 bg-white dark:bg-slate-800 text-slate-700 hover:bg-slate-50 border border-slate-200 dark:border-slate-700 dark:hover:bg-slate-700 dark:text-slate-300 rounded-lg text-sm font-bold transition-colors shadow-sm" onclick="executeEDR('memory-dump')"><i class="fas fa-microchip mr-1"></i> Mem Dump</button>
           </div>
       </div>
       <div class="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700 text-right shrink-0">
           <button class="px-6 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 rounded-lg font-semibold transition-colors shadow-sm" onclick="document.getElementById('epModal').style.display='none'">Close Panel</button>
       </div>
    </div>
  </div>

  <div id="scanModal" class="hidden fixed inset-0 z-50 glass-modal flex justify-center items-center px-4">
    <div class="bg-white dark:bg-card w-full max-w-md p-0 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
       <div class="p-6">
           <div class="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xl mb-4"><i class="fas fa-radar"></i></div>
           <h3 class="text-xl font-bold mb-2">Initiate Infrastructure Scan</h3>
           <p class="text-sm text-slate-500 mb-6">Select the environments you wish to include in this ad-hoc posture evaluation.</p>
           
           <div class="space-y-3 mb-4">
              <label class="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"><input type="checkbox" id="scope-aws" checked class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary"> <span class="font-medium flex items-center gap-2"><i class="fab fa-aws text-[#FF9900]"></i> Amazon Web Services</span></label>
              <label class="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"><input type="checkbox" id="scope-azure" checked class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary"> <span class="font-medium flex items-center gap-2"><i class="fab fa-microsoft text-[#00A4EF]"></i> Microsoft Azure</span></label>
              <label class="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"><input type="checkbox" id="scope-gcp" checked class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary"> <span class="font-medium flex items-center gap-2"><i class="fas fa-cloud text-blue-400"></i> Google Cloud</span></label>
              <label class="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"><input type="checkbox" id="scope-saas" checked class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary"> <span class="font-medium flex items-center gap-2"><i class="fas fa-cube text-slate-400"></i> Connected SaaS</span></label>
           </div>
       </div>
       <div class="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
         <button onclick="document.getElementById('scanModal').style.display='none'" class="px-5 py-2 bg-white border border-slate-300 dark:bg-slate-700 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 font-semibold rounded-lg transition-colors shadow-sm">Cancel</button>
         <button onclick="runScanWithScope()" class="px-5 py-2 bg-primary hover:bg-indigo-600 text-white font-semibold rounded-lg shadow-md transition-colors">Start Scan</button>
       </div>
    </div>
  </div>

  <div id="settingsModal" class="hidden fixed inset-0 z-50 glass-modal flex justify-center items-center px-4">
    <div class="bg-white dark:bg-card w-full max-w-sm p-6 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700">
       <h3 class="text-xl font-bold mb-4 text-slate-800 dark:text-white">Scanner Configuration</h3>
       <div class="mb-6">
         <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Scan Frequency</label>
         <select id="confFreq" class="w-full px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary shadow-sm">
            <option>Continuous</option><option>15 Minutes</option><option>1 Hour</option><option>24 Hours</option>
         </select>
       </div>
       <div class="flex justify-end gap-3 pt-2 border-t border-slate-100 dark:border-slate-800 mt-4">
         <button onclick="document.getElementById('settingsModal').style.display='none'" class="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-lg shadow-sm transition-colors">Close</button>
         <button onclick="saveScanConfig()" class="px-4 py-2 bg-slate-900 hover:bg-black dark:bg-white dark:hover:bg-slate-200 dark:text-slate-900 text-white font-semibold rounded-lg shadow-md transition-colors">Save Settings</button>
       </div>
    </div>
  </div>

  <div id="awsModal" class="hidden fixed inset-0 z-50 glass-modal flex justify-center items-center px-4"><div class="bg-white dark:bg-card w-full max-w-sm p-8 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700"><div class="text-center mb-6"><i class="fab fa-aws text-5xl text-[#FF9900] mb-3"></i><h3 class="text-xl font-bold text-slate-800 dark:text-white">Connect AWS</h3></div><div class="space-y-4 mb-8"><div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Access Key ID</label><input id="awsAK" class="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 outline-none focus:ring-2 focus:ring-[#FF9900] focus:border-[#FF9900] text-sm shadow-sm" placeholder="AKIA..."></div><div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Secret Access Key</label><input id="awsSK" type="password" class="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 outline-none focus:ring-2 focus:ring-[#FF9900] focus:border-[#FF9900] text-sm shadow-sm" placeholder="••••••••••••••••"></div></div><div class="flex justify-end gap-3"><button onclick="document.getElementById('awsModal').style.display='none'" class="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm font-semibold shadow-sm text-slate-700 dark:text-slate-300">Cancel</button><button onclick="connectAWS()" class="px-4 py-2 bg-slate-900 dark:bg-white dark:text-slate-900 text-white rounded-lg text-sm font-semibold shadow-md">Authenticate</button></div></div></div>
  <div id="genericIntModal" class="hidden fixed inset-0 z-50 glass-modal flex justify-center items-center px-4"><div class="bg-white dark:bg-card w-full max-w-sm p-8 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700"><h3 id="genIntTitle" class="text-xl font-bold mb-6 text-slate-800 dark:text-white pb-3 border-b border-slate-100 dark:border-slate-800">Connect</h3><div class="space-y-4 mb-8"><div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Endpoint URL</label><input id="genIntURL" class="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm shadow-sm" placeholder="https://api..."></div><div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">Integration Token</label><input id="genIntKey" type="password" class="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm shadow-sm" placeholder="••••••••••••••••"></div></div><div class="flex justify-end gap-3"><button onclick="document.getElementById('genericIntModal').style.display='none'" class="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm font-semibold shadow-sm text-slate-700 dark:text-slate-300">Cancel</button><button onclick="submitGenericIntegration()" class="px-4 py-2 bg-primary hover:bg-indigo-600 text-white rounded-lg text-sm font-semibold shadow-md">Link Service</button></div></div></div>
  
  <div id="previewFixModal" class="hidden fixed inset-0 z-50 glass-modal flex justify-center items-center px-4"><div class="bg-white dark:bg-card w-full max-w-lg p-0 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col"><div class="px-6 py-5 bg-red-50 dark:bg-red-900/20 border-b border-red-100 dark:border-red-900/50"><h3 class="text-lg font-bold text-red-600 dark:text-red-400 flex items-center gap-2"><i class="fas fa-exclamation-triangle"></i> Confirm Engine Remediation</h3></div><div class="p-6"><p class="text-sm text-slate-600 dark:text-slate-400 mb-4">The AI Engine will automatically modify infrastructure to resolve the following critical findings:</p><div id="preview-list" class="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700 max-h-48 overflow-y-auto text-sm space-y-2.5 mb-2 shadow-inner font-mono text-xs"></div></div><div class="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3 shrink-0"><button onclick="document.getElementById('previewFixModal').style.display='none'" class="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-sm font-semibold text-slate-700 dark:text-slate-300 shadow-sm">Abort</button><button onclick="fixAllCritical(); document.getElementById('previewFixModal').style.display='none'" class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-bold shadow-md shadow-red-500/20">Execute Fixes</button></div></div></div>

<script>
let network, pollInterval, barChartInstance, pieChartInstance, lineChartInstance, polarChartInstance;
let currentIntegrationName = "";
let currentEpId = null;
let liveMonitorInterval = null;

Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = 'Inter';
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: 'bold' };
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;

document.addEventListener("DOMContentLoaded", () => { 
    initCharts(); 
    refreshAll(); 
    loadAutomationStatus();
    loadIntegratedToolsStatus();
    loadProfile();
    fetchDaemonStatus(); // NEW: Fetch initial daemon status on load
    
    if(localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    }

    // Listen to window resize to fix graph bounding issues on screen changes
    window.addEventListener('resize', () => {
        if(network && !document.getElementById('view-attack-graph').classList.contains('hidden')) {
            network.redraw();
            network.fit();
        }
    });
});

function toggleTheme() {
    document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    refreshAll(); 
}

function toggleSidebar() {
    const sb = document.getElementById('sidebar');
    const texts = sb.querySelectorAll('.nav-text, .nav-category, .logo-text, .user-info');
    if(sb.classList.contains('w-64')) {
        sb.classList.replace('w-64', 'w-20');
        texts.forEach(el => el.style.display = 'none');
        document.querySelector('.server-widget').style.display = 'none';
        sb.querySelectorAll('.nav-item').forEach(el => el.classList.add('justify-center', 'px-0'));
    } else {
        sb.classList.replace('w-20', 'w-64');
        setTimeout(() => {
            texts.forEach(el => el.style.display = '');
            document.querySelector('.server-widget').style.display = '';
            sb.querySelectorAll('.nav-item').forEach(el => el.classList.remove('justify-center', 'px-0'));
        }, 200);
    }
    setTimeout(() => { if(network) network.fit(); }, 300);
}

function switchTab(id) {
    if(liveMonitorInterval && id !== 'live-monitoring') { clearInterval(liveMonitorInterval); liveMonitorInterval = null; }
    if(id === 'live-monitoring') startLiveMonitoring();
    
    document.querySelectorAll('[id^="view-"]').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('animate-fade-in'); // Reset animation
    });
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('nav-item-active'));
    
    const targetView = document.getElementById('view-'+id);
    targetView.classList.remove('hidden');
    // Trigger reflow for animation
    void targetView.offsetWidth;
    targetView.classList.add('animate-fade-in');
    
    document.getElementById('tab-'+id).classList.add('nav-item-active');
    
    const titleMap = { 
        'dashboard': 'Security Posture', 'integrations': 'Integrations', 'policies': 'Policies', 'automation': 'Automation', 
        'attack-graph': 'Attack Graph', 'compliance': 'Compliance', 'profile': 'Profile', 'identity': 'Identity', 
        'findings': 'Findings', 'assets': 'Assets', 'subscription': 'Subscription Plans', 'k8s': 'Kubernetes Posture',
        'darkweb': 'Dark Web Monitoring', 'endpoints': 'Endpoint Fleet', 'live-monitoring': 'Live Monitoring', 'threats': 'Threat Detection',
        'alerts': 'System Alerts' 
    };
    document.getElementById('page-title').innerText = titleMap[id] || 'CSPM';
    
    // FIX FOR ATTACK GRAPH Sizing BUG: Force redrawing after tab switch transition
    if(id==='attack-graph' && network) { 
        setTimeout(() => { 
            const container = document.getElementById('mynetwork');
            container.style.height = '600px';
            network.setSize('100%', '600px');
            network.redraw(); 
            network.fit(); 
        }, 200); // Increased timeout to ensure the browser has finished changing display:none to block
    }
    
    if(id==='compliance') loadCompliance();
    if(id==='profile') loadProfile();
    if(id==='policies') loadPolicies();
    if(id==='automation') loadAutoLogs();
    if(id==='k8s') loadK8s(); 
    if(id==='darkweb') loadDarkWeb();
    if(id==='endpoints') loadEndpoints();
    if(id==='threats') loadThreats();
    if(id==='alerts') loadAlerts(); 
}

// =====================================
// NEW: Global Alert Daemon Controls
// =====================================
async function toggleAlertDaemon(action) {
    const res = await fetch('/api/toggle_alert_daemon', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: action})
    }).then(r=>r.json());
    updateDaemonStatus(res.is_running);
    if(action === 'start') alert('Alert Daemon Started! You will receive simulated alerts every 10-20 seconds.');
    if(action === 'stop') alert('Alert Daemon Stopped!');
}

async function fetchDaemonStatus() {
    const res = await fetch('/api/alert_daemon_status').then(r=>r.json());
    updateDaemonStatus(res.is_running);
}

function updateDaemonStatus(isRunning) {
    const indicator = document.getElementById('daemon-status-indicator');
    if (isRunning) {
        indicator.innerText = "Daemon: Running";
        indicator.className = "text-xs font-bold px-2 py-1 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 mr-2";
    } else {
        indicator.innerText = "Daemon: Stopped";
        indicator.className = "text-xs font-bold px-2 py-1 rounded bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400 mr-2";
    }
}
// =====================================

async function loadEndpoints() {
    const res = await fetch('/api/endpoints').then(r=>r.json());
    const total = res.endpoints.length;
    const encrypted = res.endpoints.filter(e => e.encrypted).length;
    const fw = res.endpoints.filter(e => e.firewall).length;
    
    document.getElementById('av-count').innerText = total; 
    document.getElementById('enc-rate').innerText = total > 0 ? Math.round((encrypted/total)*100) + "%" : "0%";
    document.getElementById('enc-risk').innerText = total - encrypted;
    document.getElementById('fw-count').innerText = fw;
    document.getElementById('fw-disabled').innerText = total - fw;

    let html = `<table class="table-custom"><thead><tr><th>Hostname</th><th>OS</th><th>IP Addr</th><th>AV Status</th><th>Firewall</th><th>EDR Status</th><th></th></tr></thead><tbody>`;
    res.endpoints.forEach(e => {
        let avBadge = e.av_status === 'Clean' ? 'bg-ok' : 'bg-crit';
        let edrBadge = e.status === 'Healthy' ? 'bg-ok' : (e.status === 'Isolated' ? 'bg-crit' : 'bg-warn');
        let fwIcon = e.firewall ? '<i class="fas fa-check-circle text-emerald-500"></i>' : '<i class="fas fa-exclamation-triangle text-yellow-500"></i>';
        
        html += `<tr>
            <td class="font-bold text-slate-800 dark:text-slate-200"><i class="fas fa-desktop text-slate-400 mr-2.5"></i>${e.hostname}</td>
            <td class="text-xs text-slate-500">${e.os}</td><td class="text-xs font-mono text-slate-600 dark:text-slate-400">${e.ip}</td>
            <td><span class="badge-c ${avBadge}">${e.av_status}</span></td>
            <td>${fwIcon}</td>
            <td><span class="badge-c ${edrBadge}"><span class="w-1.5 h-1.5 rounded-full ${e.status==='Healthy'?'bg-emerald-500':'bg-red-500'}"></span> ${e.status}</span></td>
            <td class="text-right"><button class="px-4 py-1.5 bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-md text-xs font-bold text-slate-700 dark:text-slate-300 shadow-sm transition-colors" onclick="openEpModal('${e.id}', '${e.hostname}', '${e.ip}', '${e.status}', '${e.av_status}', ${e.firewall}, ${e.encrypted})">Manage</button></td>
        </tr>`;
    });
    document.getElementById('endpointTable').innerHTML = html + "</tbody></table>";
}

function openEpModal(id, host, ip, status, av, fw, enc) {
    currentEpId = id;
    document.getElementById('epModal').style.display='flex';
    document.getElementById('m-hostname').innerHTML = `<i class="fas fa-laptop text-slate-400"></i> ` + host;
    document.getElementById('m-ip').innerText = "IP: " + ip;
    document.getElementById('m-status-badge').innerText = status;
    document.getElementById('m-status-badge').className = "badge-c mt-1 " + (status === 'Healthy' ? 'bg-ok' : 'bg-crit');
    document.getElementById('m-av').innerText = av;
    document.getElementById('m-av').className = "badge-c " + (av === 'Clean' ? 'bg-ok' : 'bg-crit');
    document.getElementById('m-fw-toggle').checked = fw;
    document.getElementById('m-enc').innerText = enc ? 'BitLocker Active' : 'Not Encrypted';
    document.getElementById('m-enc').className = "badge-c " + (enc ? 'bg-ok' : 'bg-warn');
}

async function executeEDR(action) {
    if(!currentEpId) return;
    const res = await fetch('/api/endpoint_action', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: currentEpId, action: action}) }).then(r=>r.json());
    alert(res.message);
    document.getElementById('epModal').style.display='none';
    loadEndpoints(); refreshAll();
}

async function loadThreats() {
    const res = await fetch('/api/threats').then(r=>r.json());
    document.getElementById('threats-active').innerText = res.active;
    document.getElementById('threats-blocked').innerText = res.blocked;
    document.getElementById('threats-quarantine').innerText = res.quarantine;
    document.getElementById('threats-false').innerText = res.false_positives;
    
    let html = `<table class="table-custom"><thead><tr><th>Detection Time</th><th>Target Host</th><th>Threat Signature</th><th>Severity</th><th>Enforcement</th></tr></thead><tbody>`;
    res.detections.forEach(d => {
        let badge = d.severity === 'Critical' ? 'bg-crit' : (d.severity === 'High' ? 'bg-high' : 'bg-warn');
        html += `<tr><td class="text-xs text-slate-500 font-mono">${d.time}</td><td class="font-bold text-slate-700 dark:text-slate-300"><i class="fas fa-desktop text-slate-400 mr-2"></i>${d.hostname}</td><td class="font-mono text-xs text-red-600 dark:text-red-400 font-semibold bg-red-50 dark:bg-red-900/20 px-2 py-1 rounded inline-block">${d.threat_name}</td><td><span class="badge-c ${badge}">${d.severity}</span></td><td><button class="px-4 py-1.5 bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 rounded-md text-xs font-bold text-slate-700 dark:text-slate-300 shadow-sm hover:bg-slate-50 dark:hover:bg-slate-700" onclick="alert('Block applied.')">Block Hash</button></td></tr>`;
    });
    document.getElementById('threatDetectionTable').innerHTML = html + "</tbody></table>";
}

async function loadAlerts() {
    const res = await fetch('/api/system_alerts').then(r=>r.json());
    let html = `<table class="table-custom"><thead><tr><th>Timestamp</th><th>Severity</th><th>Event Detail</th></tr></thead><tbody>`;
    
    if(res.alerts.length === 0) {
        html += `<tr><td colspan="3" class="text-center text-slate-500 py-8 italic">No security alerts found in the database.</td></tr>`;
    } else {
        res.alerts.forEach(a => {
            let badge = a.severity === 'CRITICAL' ? 'bg-crit' : (a.severity === 'HIGH' ? 'bg-high' : (a.severity === 'INFO' ? 'bg-info' : 'bg-warn'));
            let icon = a.severity === 'CRITICAL' ? 'fa-fire text-red-500' : (a.severity === 'INFO' ? 'fa-info-circle text-blue-500' : 'fa-exclamation-triangle text-yellow-500');
            html += `<tr><td class="text-xs text-slate-500 font-mono whitespace-nowrap">${a.timestamp}</td><td><span class="badge-c ${badge}">${a.severity}</span></td><td class="font-medium text-slate-700 dark:text-slate-300"><i class="fas ${icon} mr-2"></i>${a.message}</td></tr>`;
        });
    }
    document.getElementById('alertsTableContainer').innerHTML = html + "</tbody></table>";
}

async function startLiveMonitoring() { if(liveMonitorInterval) return; updateLiveMonitoring(); liveMonitorInterval = setInterval(updateLiveMonitoring, 2000); }
async function updateLiveMonitoring() {
    const res = await fetch('/api/live_metrics').then(r=>r.json());
    document.getElementById('live-last-update').innerText = res.timestamp;
    document.getElementById('live-cpu').innerText = res.cpu + '%'; document.getElementById('live-cpu-bar').style.width = res.cpu + '%';
    document.getElementById('live-ram').innerText = res.ram + '%'; document.getElementById('live-ram-bar').style.width = res.ram + '%';
    document.getElementById('live-network').innerText = res.network_speed + ' MB/s';
    document.getElementById('upload-speed').innerText = res.upload_speed; document.getElementById('download-speed').innerText = res.download_speed;
    
    if(res.events) {
        let html = "";
        res.events.forEach(e => {
            let icon = 'fa-info-circle text-blue-500 bg-blue-100 dark:bg-blue-900/40 p-2 rounded-lg';
            if(e.type === 'THREAT') icon = 'fa-biohazard text-red-500 bg-red-100 dark:bg-red-900/40 p-2 rounded-lg';
            if(e.type === 'AUTH') icon = 'fa-user-lock text-purple-500 bg-purple-100 dark:bg-purple-900/40 p-2 rounded-lg';
            if(e.type === 'SCAN') icon = 'fa-radar text-emerald-500 bg-emerald-100 dark:bg-emerald-900/40 p-2 rounded-lg';
            
            html += `<div class="p-4 bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-xl text-sm flex gap-4 items-start shadow-sm">
                <i class="fas ${icon}"></i>
                <div class="flex-1"><div class="flex justify-between mb-1"><strong class="text-slate-800 dark:text-slate-200 font-bold">${e.type} EVENT</strong><span class="text-xs text-slate-400 font-mono">${e.time}</span></div><div class="text-slate-600 dark:text-slate-400 leading-relaxed font-mono text-xs">${e.message}</div></div>
            </div>`;
        });
        document.getElementById('live-events').innerHTML = html;
    }
}

function connectCloud(type) { if(type === 'AWS') document.getElementById('awsModal').style.display='flex'; }
function openGenericIntegrationModal(name) { currentIntegrationName = name; document.getElementById('genIntTitle').innerHTML = "<i class='fas fa-plug text-primary mr-2'></i> Connect " + name; document.getElementById('genericIntModal').style.display = 'flex'; }
async function submitGenericIntegration() { const url = document.getElementById('genIntURL').value; const key = document.getElementById('genIntKey').value; await fetch('/api/configure_integration', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: currentIntegrationName, url: url, key: key}) }); document.getElementById('genericIntModal').style.display = 'none'; loadIntegratedToolsStatus(); }

async function loadIntegratedToolsStatus() {
    const res = await fetch('/api/get_integrations_status').then(r=>r.json());
    res.integrations.forEach(i => {
        const badgeEl = document.getElementById('status-' + i.name.toLowerCase());
        if(badgeEl) {
            badgeEl.innerHTML = i.status === 'Connected' ? '<span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Connected' : 'Disconnected';
            badgeEl.className = "badge-c mb-5 " + (i.status === 'Connected' ? 'bg-ok' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400');
        }
    });
}

async function loadPolicies() {
    const res = await fetch('/api/policies').then(r=>r.json());
    let html = '<table class="table-custom"><thead><tr><th>Policy Code</th><th>Control Name</th><th>Enforcement</th></tr></thead><tbody>';
    res.policies.forEach(p => { 
        html += `<tr><td class="font-mono text-xs font-bold text-slate-500">${p.code}</td><td class="font-bold text-slate-700 dark:text-slate-300">${p.name}</td><td>
        <div class="relative inline-block w-10 mr-2 align-middle select-none">
            <input type="checkbox" id="pol-${p.code}" ${p.enabled ? 'checked' : ''} onchange="togglePolicy('${p.code}')" class="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer z-10 shadow-sm"/>
            <label for="pol-${p.code}" class="toggle-label block overflow-hidden h-5 rounded-full bg-slate-300 dark:bg-slate-600 cursor-pointer"></label>
        </div></td></tr>`; 
    });
    document.getElementById('policy-list').innerHTML = html + '</tbody></table>';
}
async function togglePolicy(code) { await fetch('/api/toggle_policy', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code: code}) }); }
async function loadAutomationStatus() { const res = await fetch('/api/automation_config').then(r=>r.json()); document.getElementById('auto-fix-toggle').checked = res.auto_fix; document.getElementById('auto-status').innerText = res.auto_fix ? "Active" : "Disabled"; document.getElementById('auto-status').className = res.auto_fix ? 'font-bold text-emerald-600 dark:text-emerald-400' : 'font-bold text-slate-700 dark:text-slate-300'; }
async function toggleAutoFix() { const enabled = document.getElementById('auto-fix-toggle').checked; await fetch('/api/toggle_automation', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({enabled: enabled}) }); loadAutomationStatus(); }
async function loadAutoLogs() { const res = await fetch('/api/automation_logs').then(r=>r.json()); let html = '<table class="table-custom"><thead><tr><th>Timestamp</th><th>Action Applied</th><th>Target Resource</th></tr></thead><tbody>'; res.logs.forEach(l => { html += `<tr><td class="text-xs font-mono text-slate-500">${l.timestamp}</td><td><span class="badge-c bg-info"><i class="fas fa-robot mr-1"></i> ${l.action}</span></td><td class="font-mono text-xs font-bold text-slate-700 dark:text-slate-300">${l.resource}</td></tr>`; }); document.getElementById('autoLogsTable').innerHTML = html + "</tbody></table>"; }

async function handleFileSelect() { const file = document.getElementById('uploadInput').files[0]; if(!file) return; const fd = new FormData(); fd.append('file', file); const res = await fetch('/api/upload_cloud', {method:'POST', body:fd}); if(res.ok) { alert("Data ingested successfully! Scan ready."); refreshAll(); } }
async function connectAWS() { const ak=document.getElementById('awsAK').value; const sk=document.getElementById('awsSK').value; await fetch('/api/connect_aws', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({access_key:ak, secret_key:sk})}); document.getElementById('awsModal').style.display='none'; loadIntegratedToolsStatus(); runScan(); }

function openScanModal() { document.getElementById('scanModal').style.display='flex'; }
async function runScanWithScope() {
    document.getElementById('scanModal').style.display='none';
    const scopes = [];
    if(document.getElementById('scope-aws').checked) scopes.push('AWS');
    if(document.getElementById('scope-azure').checked) scopes.push('Azure');
    if(document.getElementById('scope-gcp').checked) scopes.push('GCP');
    if(document.getElementById('scope-saas').checked) scopes.push('SaaS');
    
    const res=await fetch('/api/run_scan', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({scopes: scopes})}).then(r=>r.json());
    if(res.status==='started') { 
        document.getElementById('scan-progress').classList.remove('hidden'); 
        pollInterval=setInterval(checkStatus, 1000); 
    }
}
async function runScan() { runScanWithScope(); }

async function checkStatus() { const res=await fetch('/api/scan_status').then(r=>r.json()); document.getElementById('scan-msg').innerText=res.message; document.getElementById('scan-bar').style.width=res.progress+'%'; if(!res.is_scanning && res.progress===100) { clearInterval(pollInterval); setTimeout(()=>{document.getElementById('scan-progress').classList.add('hidden'); refreshAll();}, 1000); } }

async function previewFixCritical() {
    const res = await fetch('/api/preview_fix').then(r=>r.json());
    let html = "";
    if(res.resources.length === 0) html = "<div class='text-slate-500 italic p-2'>No critical resources found to remediate.</div>";
    else res.resources.forEach(r => html += `<div class='flex gap-3 items-center p-2 border-b border-slate-200 dark:border-slate-700/50 last:border-0'><i class='fas fa-exclamation-triangle text-red-500'></i><span class='font-mono font-bold text-slate-700 dark:text-slate-200'>${r}</span></div>`);
    document.getElementById('preview-list').innerHTML = html;
    document.getElementById('previewFixModal').style.display='flex';
}

async function fixAllCritical() { 
    const res = await fetch('/api/fix_all_critical', {method:'POST'}); 
    if(res.status === 403) { alert("Enterprise plan required to utilize Auto-Remediation features."); return; }
    refreshAll(); 
}
async function saveScanConfig() { const freq = document.getElementById('confFreq').value; await fetch('/api/update_scan_config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({frequency: freq}) }); document.getElementById('settingsModal').style.display='none'; }

async function loadProfile() {
    try {
        const res = await fetch('/api/get_profile').then(r => r.json());
        if (res && !res.error) {
            const fullName = res.full_name || 'User'; const email = res.email || 'No Email'; const role = res.role || 'Viewer'; const org = res.organization || ''; const tier = res.subscription_tier || 'Free'; const token = res.api_token || '';

            document.getElementById('p-display-name').innerText = fullName; document.getElementById('p-email').innerText = email; document.getElementById('p-role').innerText = role + " Role"; document.getElementById('p-tier').innerText = tier;
            document.getElementById('current-plan-badge').innerText = tier; document.getElementById('api-token-box').value = token;
            
            const initial = fullName.charAt(0).toUpperCase() || email.charAt(0).toUpperCase() || 'U';
            document.getElementById('p-avatar').innerText = initial; document.getElementById('p-avatar-sm').innerText = initial;
            document.getElementById('edit-name').value = fullName; document.getElementById('edit-org').value = org;
            
            // NEW PLAN BUTTON LOGIC
            const tiers = ['Free', 'Pro', 'Enterprise'];
            tiers.forEach(t => {
                const btn = document.getElementById('btn-tier-' + t);
                if (btn) {
                    if (t === tier) {
                        btn.innerText = "Current Plan";
                        btn.className = "w-full py-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 cursor-not-allowed font-medium";
                        btn.disabled = true;
                    } else {
                        btn.innerText = "Upgrade to " + t;
                        btn.disabled = false;
                        if (t === 'Pro') btn.className = "w-full py-2.5 rounded-lg bg-primary hover:bg-indigo-600 text-white font-medium transition shadow-md";
                        if (t === 'Enterprise') btn.className = "w-full py-2.5 rounded-lg bg-slate-900 hover:bg-black dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 text-white font-medium transition shadow-md";
                    }
                }
            });
        }
    } catch (e) { console.error("Failed to load profile:", e); }
}

async function updateProfile() { 
    const name = document.getElementById('edit-name').value; const org = document.getElementById('edit-org').value; 
    const res = await fetch('/api/update_profile', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({full_name: name, organization: org}) }); 
    if(res.ok) { loadProfile(); } 
}
async function generateToken() { const res = await fetch('/api/generate_token', { method: 'POST' }).then(r=>r.json()); if(res.token) { document.getElementById('api-token-box').value = res.token; } }
async function upgradePlan(tier) { if(confirm(`Confirm simulated billing upgrade to the ${tier} tier?`)) { const res = await fetch('/api/upgrade_plan', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({tier: tier}) }); if(res.ok) { loadProfile(); } } }

async function refreshAll() {
    const res = await fetch('/api/metrics').then(r=>r.json());
    if(!res.data || !res.data.ai_risk_score) return; 
    const d = res.data;
    
    document.getElementById('kpi-crit').innerText = d.severity_dist.critical;
    document.getElementById('kpi-score').innerText = d.ai_risk_score;
    if(document.getElementById('kpi-darkweb')) document.getElementById('kpi-darkweb').innerText = d.dark_web_count;
    if(document.getElementById('kpi-endpoints')) document.getElementById('kpi-endpoints').innerText = d.endpoint_count;
    
    const riskColor = d.ai_risk_score > 80 ? '#ef4444' : (d.ai_risk_score > 50 ? '#f59e0b' : '#10b981');
    const gauge = document.getElementById('risk-circle');
    gauge.innerText = d.ai_risk_score; gauge.style.borderTopColor = riskColor; gauge.style.color = riskColor;

    if(d.server_health) {
        document.getElementById('cpu-bar').style.width = d.server_health.cpu + "%"; document.getElementById('cpu-txt').innerText = d.server_health.cpu + "%";
        document.getElementById('ram-bar').style.width = d.server_health.ram + "%"; document.getElementById('ram-txt').innerText = d.server_health.ram + "%";
    }

    barChartInstance.data.datasets[0].data = [d.severity_dist.critical, d.severity_dist.high, d.severity_dist.medium, d.severity_dist.low]; barChartInstance.update();
    pieChartInstance.data.datasets[0].data = [d.severity_dist.critical, d.severity_dist.high, d.severity_dist.medium, d.severity_dist.low]; pieChartInstance.update();
    
    if(d.history && d.history.length > 0) {
        lineChartInstance.data.labels = d.history.map(h => h.date);
        lineChartInstance.data.datasets[0].data = d.history.map(h => h.risk_score);
        lineChartInstance.update();
    }

    if(d.risk_by_service) { polarChartInstance.data.labels = Object.keys(d.risk_by_service); polarChartInstance.data.datasets[0].data = Object.values(d.risk_by_service); polarChartInstance.update(); }

    if(d.graph_data) {
        const container = document.getElementById('mynetwork');
        const isDark = document.documentElement.classList.contains('dark');
        const data = { nodes: new vis.DataSet(d.graph_data.nodes), edges: new vis.DataSet(d.graph_data.edges) };
        
        const options = { 
            layout: { 
                hierarchical: { 
                    direction: 'LR', 
                    levelSeparation: 300, 
                    nodeSpacing: 150, 
                    treeSpacing: 200 
                } 
            },
            nodes: { 
                shape: 'box', 
                margin: 15, 
                borderWidth: 2, 
                shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 10, x: 5, y: 5 },
                font: { face:'Inter', color: isDark?'#f1f5f9':'#1e293b', size: 14, multi: 'html' }
            }, 
            edges: { 
                smooth: {type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.4}, 
                arrows: {to: {enabled: true, scaleFactor: 0.8}},
                font: { face: 'Inter', size: 10, align: 'horizontal', color: isDark ? '#94a3b8' : '#64748b', strokeWidth: 0, background: isDark ? '#1e293b' : '#ffffff' }
            }, 
            physics: { enabled: false },
            groups: { 
                attacker: {color: {background:'#ef4444', border:'#991b1b'}}, 
                critical: {color: {background: isDark?'#7f1d1d':'#fee2e2', border:'#ef4444'}}, 
                warning: {color: {background: isDark?'#713f12':'#fef08a', border:'#f59e0b'}}, 
                safe: {color: {background: isDark?'#14532d':'#dcfce3', border:'#22c55e'}} 
            },
            interaction: { hover: true, tooltipDelay: 200, zoomView: true, dragView: true }
        };

        if (!network) { 
            network = new vis.Network(container, data, options); 
            // Fix graph size bug
            setTimeout(() => { 
                document.getElementById('mynetwork').style.height = '600px';
                network.setSize('100%', '600px');
                network.redraw();
                network.fit(); 
            }, 500);
        } else { 
            network.setData(data); 
            network.setOptions(options); 
            document.getElementById('mynetwork').style.height = '600px';
            network.setSize('100%', '600px');
            network.redraw();
            network.fit();
        }
    }
    
    if(d.threat_intel) {
        let tHtml = '<table class="table-custom"><thead><tr><th>Source Channel</th><th>Data Class</th><th>Scrape Date</th></tr></thead><tbody>';
        d.threat_intel.forEach(t => {
            const isDarkWeb = t.source.includes('Dark') || t.source.includes('Tor');
            const badgeCls = isDarkWeb ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 border border-purple-200 dark:border-purple-800/50' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800/50';
            tHtml += `<tr><td><span class="px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-widest ${badgeCls}"><i class="fas ${isDarkWeb?'fa-spider':'fa-database'} mr-1.5"></i>${t.source}</span></td><td class="font-bold text-slate-700 dark:text-slate-300">${t.data}</td><td class="text-xs text-slate-500 font-mono">${t.date}</td></tr>`;
        });
        document.getElementById('threatTable').innerHTML = tHtml + "</tbody></table>";
    }

    if(d.alerts && d.alerts.length > 0) {
        let tickHtml = "";
        d.alerts.forEach(a => {
            const isCrit = a.severity === 'CRITICAL';
            tickHtml += `<div class="h-12 flex items-center text-sm"><span class="px-2 py-0.5 rounded text-[10px] font-bold mr-4 uppercase tracking-widest ${isCrit?'bg-red-100 text-red-700':'bg-yellow-100 text-yellow-700'}">${a.severity}</span> <span class="text-slate-800 dark:text-slate-200 font-medium mr-3">${a.msg}</span> <span class="text-[11px] text-slate-500 font-mono">(${a.time})</span></div>`;
        });
        document.getElementById('alert-ticker-content').innerHTML = tickHtml;
    }

    loadTables(d.findings);
}

async function loadDarkWeb() {
    const res = await fetch('/api/darkweb_feed').then(r=>r.json());
    let html = '<table class="table-custom"><thead><tr><th>Discovery Date</th><th>Source Node</th><th>Leak Details</th><th>Enforcement</th></tr></thead><tbody>';
    res.data.forEach(f => {
        html += `<tr><td class="text-xs text-slate-500 font-mono">${f.date}</td><td><span class="badge-c bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 border-purple-200 dark:border-purple-800/50"><i class="fas fa-mask mr-1"></i>${f.source}</span></td><td><div class="font-extrabold text-slate-800 dark:text-slate-200">${f.leak_type}</div><div class="text-xs text-slate-500 mt-1 font-mono">${f.detail}</div></td><td><button class="px-4 py-1.5 bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-md text-xs font-bold transition-colors shadow-sm" onclick="alert('Mitigation Takedown Initiated via Third-Party Partner')">Initiate Takedown</button></td></tr>`;
    });
    document.getElementById('detailedDarkWebTable').innerHTML = html + "</tbody></table>";
}

async function loadCompliance() { 
    const res=await fetch('/api/compliance_scorecard').then(r=>r.json()); 
    let html='<table class="table-custom"><thead><tr><th>Regulatory Framework</th><th>Status</th><th>Coverage Score</th></tr></thead><tbody>'; 
    res.scorecard.forEach(f => { html+=`<tr><td class="font-bold text-slate-800 dark:text-slate-200"><i class="fas fa-file-signature text-slate-400 mr-2"></i>${f.framework}</td><td><span class="badge-c ${f.passed ? 'bg-ok' : 'bg-crit'}">${f.status}</span></td><td><div class="flex items-center gap-4"><div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 max-w-[120px] overflow-hidden"><div class="${f.passed?'bg-emerald-500':'bg-red-500'} h-full rounded-full" style="width: ${f.score}%"></div></div><span class="text-sm font-mono font-bold text-slate-700 dark:text-slate-300">${f.score}%</span></div></td></tr>`; });
    document.getElementById('complianceTable').innerHTML=html+'</tbody></table>'; 
}

async function loadK8s() {
    const res = await fetch('/api/k8s_posture').then(r=>r.json());
    let html = '<table class="table-custom"><thead><tr><th>Cluster ID</th><th>Resource Target</th><th>Misconfiguration Issue</th><th>Severity Rating</th></tr></thead><tbody>';
    res.findings.forEach(f => { html += `<tr><td class="font-bold text-blue-600 dark:text-blue-400"><i class="fab fa-docker mr-2"></i>${f.cluster}</td><td class="font-mono text-xs font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded inline-block">${f.resource}</td><td class="font-medium text-slate-800 dark:text-slate-200">${f.issue}</td><td><span class="badge-c bg-crit">${f.severity}</span></td></tr>`; });
    document.getElementById('k8sTable').innerHTML = html + "</tbody></table>";
}

function loadTables(findings) {
    let fHtml = '<table class="table-custom"><thead><tr><th>Resource Target</th><th>Issue Description</th><th>Remediation Path</th></tr></thead><tbody>';
    let iHtml = '<table class="table-custom"><thead><tr><th>Identity Principal</th><th>Risk Context</th><th>Risk Score</th></tr></thead><tbody>';
    findings.forEach(f => {
        let issueCls = f.issue.includes('[FIXED]') ? 'text-emerald-600 dark:text-emerald-400 line-through opacity-60' : 'text-slate-800 dark:text-slate-200 font-medium';
        let resIcon = f.cloud === 'AWS' ? 'fab fa-aws text-[#FF9900]' : (f.cloud === 'Azure' ? 'fab fa-microsoft text-[#00A4EF]' : 'fas fa-cloud text-blue-400');
        
        fHtml += `<tr><td class="font-mono text-xs font-semibold text-slate-600 dark:text-slate-400"><i class="${resIcon} mr-2"></i>${f.resource_id}</td><td class="${issueCls}">${f.issue}</td><td class="text-sm font-semibold ${f.remediation==='AUTO-FIXED'?'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-0.5 rounded inline-flex items-center gap-1':(f.issue.includes('[FIXED]')?'text-slate-400':'text-primary')}">${f.remediation==='AUTO-FIXED'?'<i class="fas fa-robot text-[10px]"></i> Auto-Remediated':f.remediation}</td></tr>`;
        
        if(['Identity','IAM'].includes(f.resource_type) || f.issue.includes("MFA") || f.issue.includes("Admin")) {
             iHtml += `<tr><td class="font-mono text-xs font-bold text-slate-700 dark:text-slate-300"><i class="fas fa-user-shield text-slate-400 mr-2"></i>${f.resource_id}</td><td class="font-medium text-slate-800 dark:text-slate-200">${f.issue}</td><td><span class="badge-c ${f.risk_score > 80 ? 'bg-crit' : 'bg-warn'} shadow-sm">${f.risk_score}</span></td></tr>`;
        }
    });
    document.getElementById('findingsTable').innerHTML = fHtml + "</tbody></table>";
    document.getElementById('identityTable').innerHTML = iHtml + "</tbody></table>";
    
    fetch('/api/assets').then(r=>r.json()).then(res => {
        let aHtml = '<table class="table-custom"><thead><tr><th>Provider</th><th>Asset Identifier</th><th>Classification</th><th>Risk Index</th></tr></thead><tbody>';
        res.assets.forEach(a => {
            let icon = a.cloud === 'AWS' ? 'fab fa-aws text-[#FF9900]' : (a.cloud === 'Azure' ? 'fab fa-microsoft text-[#00A4EF]' : (a.cloud === 'GCP' ? 'fas fa-cloud text-blue-400' : 'fas fa-cube text-slate-400'));
            aHtml += `<tr><td><div class="w-8 h-8 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 flex items-center justify-center shadow-sm"><i class="${icon} text-lg"></i></div></td><td class="font-mono text-xs font-bold text-slate-700 dark:text-slate-300">${a.resource_id}</td><td><span class="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-md text-[11px] font-bold uppercase tracking-wider border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400">${a.resource_type}</span></td><td><span class="badge-c ${a.risk_score>80?'bg-crit':(a.risk_score>50?'bg-warn':'bg-ok')}">${a.risk_score}</span></td></tr>`;
        });
        document.getElementById('assetsTable').innerHTML = aHtml + "</tbody></table>";
    });
}

function downloadReport() { window.location.href = '/download_report'; }
function downloadDemoCSV() { window.location.href = '/download_demo_template'; }

function initCharts() {
    const isDark = document.documentElement.classList.contains('dark');
    const gridColor = isDark ? '#1e293b' : '#f1f5f9';
    const textColor = isDark ? '#64748b' : '#94a3b8';
    const chartOpts = { 
        plugins: { legend: { display: false } }, 
        scales: { 
            x: { grid: { display: false }, ticks: {color: textColor, font: {family: 'Inter', size: 11, weight: '600'}} }, 
            y: { grid: { color: gridColor, borderDash: [4, 4] }, border: {display: false}, ticks: {color: textColor, font: {family: 'Inter', size: 11}} } 
        },
        maintainAspectRatio: false
    };
    
    barChartInstance = new Chart(document.getElementById('barChart'), { type:'bar', data:{labels:['CRITICAL','HIGH','MEDIUM','LOW'], datasets:[{data:[0,0,0,0], backgroundColor:['#ef4444','#f97316','#eab308','#10b981'], borderRadius: 4, barPercentage: 0.6}]}, options: chartOpts });
    pieChartInstance = new Chart(document.getElementById('pieChart'), { type:'doughnut', data:{labels:['Critical','High','Medium','Low'], datasets:[{data:[0,0,0,0], backgroundColor:['#ef4444','#f97316','#eab308','#10b981'], borderWidth: 0, hoverOffset: 4}]}, options: { cutout: '75%', maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: {color: isDark ? '#cbd5e1' : '#475569', usePointStyle: true, boxWidth: 8, font: {family: 'Inter', size: 12, weight: '500'}} } } } });
    lineChartInstance = new Chart(document.getElementById('lineChart'), { type:'line', data:{labels:[], datasets:[{label:'Risk Trend', data:[], borderColor:'#4f46e5', backgroundColor: 'rgba(79, 70, 229, 0.1)', fill: true, tension:0.4, pointRadius: 3, pointBackgroundColor: '#fff', pointBorderColor: '#4f46e5', pointBorderWidth: 2, pointHoverRadius: 6, borderWidth: 3}]}, options: { ...chartOpts, plugins: { legend: {display: false}, tooltip: { mode: 'index', intersect: false } } } });
    polarChartInstance = new Chart(document.getElementById('polarChart'), { type: 'polarArea', data: { labels: ['Compute', 'Storage', 'Identity', 'Database'], datasets: [{ data: [10, 20, 5, 15], backgroundColor: ['rgba(239, 68, 68, 0.8)', 'rgba(249, 115, 22, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(16, 185, 129, 0.8)'], borderWidth: 0 }] }, options: { maintainAspectRatio: false, scales: { r: { grid: { color: gridColor }, angleLines: {color: gridColor}, ticks:{display:false, backdropColor: 'transparent'} } }, plugins: { legend: { position: 'right', labels: {color: isDark ? '#cbd5e1' : '#475569', usePointStyle: true, boxWidth: 8, font: {family: 'Inter', size: 12, weight: '500'}} } } } });
}
</script>
</body></html>
"""

# -------------------------
# 2. Database Layer
# -------------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Original Tables
        db.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, role TEXT DEFAULT 'Admin', full_name TEXT, organization TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, user_email TEXT, scan_date TEXT, risk_score REAL, critical_count INTEGER, findings_json TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS policies (code TEXT PRIMARY KEY, name TEXT, enabled INTEGER DEFAULT 1)''')
        db.execute('''CREATE TABLE IF NOT EXISTS automation_settings (id INTEGER PRIMARY KEY, auto_fix_enabled INTEGER DEFAULT 0)''')
        db.execute('''CREATE TABLE IF NOT EXISTS automation_logs (id INTEGER PRIMARY KEY, action TEXT, resource TEXT, timestamp TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS integration_configs (name TEXT PRIMARY KEY, url TEXT, key TEXT, status TEXT DEFAULT 'Disconnected', last_sync TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS resource_stats (id INTEGER PRIMARY KEY, cpu INTEGER, ram INTEGER, timestamp TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS api_tokens (id INTEGER PRIMARY KEY, user_email TEXT, token TEXT, created_at TEXT)''')
        
        # EDR Tables
        db.execute('''CREATE TABLE IF NOT EXISTS endpoints (
            id INTEGER PRIMARY KEY, 
            hostname TEXT, 
            os TEXT, 
            ip TEXT, 
            status TEXT DEFAULT 'Healthy', 
            av_status TEXT DEFAULT 'Clean',
            firewall INTEGER DEFAULT 1,
            encrypted INTEGER DEFAULT 1,
            last_seen TEXT
        )''')
        
        db.execute('''CREATE TABLE IF NOT EXISTS threats (
            id INTEGER PRIMARY KEY,
            endpoint_id INTEGER,
            threat_name TEXT,
            threat_type TEXT,
            severity TEXT,
            status TEXT DEFAULT 'Active',
            detected_at TEXT,
            FOREIGN KEY(endpoint_id) REFERENCES endpoints(id)
        )''')

        # Alerts Table
        db.execute('''CREATE TABLE IF NOT EXISTS system_alerts (
            id INTEGER PRIMARY KEY,
            user_email TEXT,
            severity TEXT,
            message TEXT,
            timestamp TEXT
        )''')

        # Migrations and Seeding
        try: db.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "Admin"'); db.commit()
        except: pass
        try: db.execute('ALTER TABLE users ADD COLUMN full_name TEXT'); db.execute('ALTER TABLE users ADD COLUMN organization TEXT'); db.commit()
        except: pass
        
        # SUBSCRIPTION COLUMNS
        try: db.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'Free'"); db.commit()
        except: pass
        try: db.execute("ALTER TABLE users ADD COLUMN subscription_expires TEXT"); db.commit()
        except: pass

        cur = db.execute('SELECT * FROM users WHERE email = ?', ('admin@cspm.com',))
        if cur.fetchone() is None:
            db.execute('INSERT INTO users (email, password, role, full_name, organization, subscription_tier) VALUES (?, ?, ?, ?, ?, ?)', ('admin@cspm.com', generate_password_hash("admin123"), 'Admin', 'System Admin', 'CSPM Corp', 'Enterprise'))
        
        db.execute('INSERT OR IGNORE INTO automation_settings (id, auto_fix_enabled) VALUES (1, 0)')
        
        # Seed policies
        defaults = [('CIS-1.1', 'Root Account MFA Enabled'), ('CIS-1.2', 'MFA for IAM users'), ('CIS-2.3', 'S3 Public Access Blocked'), ('PCI-3.4', 'Encryption Data at Rest')]
        for code, name in defaults:
            try: db.execute('INSERT INTO policies (code, name) VALUES (?, ?)', (code, name))
            except: pass
            
        # Seed integrations
        for i in ['AWS', 'Azure', 'Splunk', 'Jira', 'GCP']:
             try: db.execute('INSERT OR IGNORE INTO integration_configs (name, url, key, status, last_sync) VALUES (?,?,?,?,?)', (i, '', '', 'Disconnected', ''))
             except: pass
        
        # Seed EDR Endpoints
        if not db.execute('SELECT * FROM endpoints').fetchone():
            db.executemany('INSERT INTO endpoints (hostname, os, ip, status, av_status, firewall, encrypted) VALUES (?,?,?,?,?,?,?)', [
                ('LAPTOP-WIN-001', 'Windows 11', '192.168.1.101', 'Healthy', 'Clean', 1, 1),
                ('SERVER-LIN-DB', 'Ubuntu 22.04', '10.0.0.5', 'Healthy', 'Clean', 1, 0),
                ('LAPTOP-HR-04', 'Windows 10', '192.168.1.105', 'Infected', 'Malware Detected', 1, 1),
                ('DESKTOP-FIN-02', 'macOS 14', '192.168.1.110', 'Isolated', 'Clean', 1, 1),
                ('WORKSTATION-05', 'Windows 11', '192.168.1.115', 'Healthy', 'Clean', 0, 1)
            ])
             
        db.commit()

# -------------------------
# 3. Global State
# -------------------------
SCAN_STATUS = { "is_scanning": False, "progress": 0, "message": "Ready" }
STATE = {
    "uploaded_df": None,
    "logs": [],
    "latest_metrics": {},
    "continuous_scan_active": False,
    "server_health": {"cpu": 12, "ram": 45},
    "threat_intel": [],
    "alerts": [],
    "scan_config": { "frequency": "15 min", "scopes": [] }
}
DAEMON_STATE = {"is_running": False} # Default to False so it doesn't run until started

# -------------------------
# 4. Backend Logic
# -------------------------
def load_sample_df():
    SAMPLE_CSV = """cloud,resource_id,resource_type,service,region,severity,issue,risk_score,compliance,remediation
AWS,root_account,Identity,IAM,global,CRITICAL,Root account MFA disabled,100,CIS-1.1,Enable MFA on Root
AWS,admin_bob,Identity,IAM,global,CRITICAL,Admin user missing MFA,95,CIS-1.2,Enable MFA for Admins
AWS,i-0a12bc34def,EC2,EC2,us-east-1,CRITICAL,Publicly exposed port 22,95,CIS-4.1,Restrict SSH to known IPs
AWS,s3-logs,S3,S3,us-west-2,HIGH,S3 bucket allows public read,88,CIS-3.1,Enable bucket policy
AWS,rds-prod,RDS,RDS,us-east-2,MEDIUM,RDS unencrypted,65,PCI-3.4,Enable encryption
Azure,vm-prod-01,VM,Compute,eastus,CRITICAL,NSG allows 0.0.0.0/0,93,Azure CIS-1.2,Restrict inbound rules
Azure,store-acct,Storage,StorageAccount,centralus,HIGH,Not encrypted,78,Azure CIS-2.3,Enable encryption
GCP,gce-vm,GCE,Compute,us-central1,CRITICAL,Firewall allows all,96,GCP CIS-1.1,Restrict firewall rules
SaaS,salesforce-org,SaaS,CRM,global,HIGH,External Sharing Enabled,75,GDPR,Restrict External Sharing
SaaS,github-repo,SaaS,Code,global,CRITICAL,Secret Keys in Repo,98,NIST,Revoke Keys
"""
    return pd.read_csv(io.StringIO(SAMPLE_CSV))

def append_log(msg, user=None):
    if not user: user = session.get('email', 'System') if has_request_context() else 'System'
    STATE['logs'].insert(0, {"time": datetime.utcnow().strftime("%H:%M:%S"), "msg": msg, "user": user})

def ensure_df():
    if STATE['uploaded_df'] is None: STATE['uploaded_df'] = load_sample_df()
    return STATE['uploaded_df']

def severity_to_numeric(s):
    return {'CRITICAL': 100, 'HIGH': 75, 'MEDIUM': 50, 'LOW': 25}.get(str(s).upper(), 10)

def generate_threat_intel():
    sources = ['Dark Web Market', 'Russian Forum', 'Pastebin', 'Tor Exit Node']
    data_types = ['Admin Credentials', 'API Keys', 'Customer Database', 'Network Map']
    hits = []
    count = random.randint(1, 4)
    for _ in range(count):
        hits.append({
            "source": random.choice(sources),
            "data": random.choice(data_types),
            "date": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        })
    return hits

def generate_detailed_darkweb_data():
    return [
        {"date": datetime.now().strftime("%Y-%m-%d"), "source": "XSS.is Forum", "leak_type": "Database Sale", "detail": "Selling access to staging environment DB"},
        {"date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "source": "Genesis Market", "leak_type": "Stealer Logs", "detail": "Employee laptop infected (user: j.doe)"},
        {"date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "source": "Tor Hidden Service", "leak_type": "Ransomware Leak", "detail": "Mention of organization in leak preview"},
        {"date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), "source": "Pastebin", "leak_type": "Credential Dump", "detail": "admin@cspm.com:Password123 found in combo list"}
    ]

def filter_by_scope(df, scopes):
    if not scopes: return df
    mask = pd.Series([False] * len(df))
    for s in scopes:
        if s in ['AWS', 'Azure', 'GCP', 'SaaS']:
            mask = mask | (df['cloud'] == s)
    return df[mask]

def generate_k8s_findings():
    return [
        {"cluster": "prod-k8s-us", "resource": "nginx-ingress", "issue": "Running as Root", "severity": "CRITICAL"},
        {"cluster": "dev-cluster", "resource": "api-pod", "issue": "Privileged Container", "severity": "HIGH"},
        {"cluster": "prod-k8s-eu", "resource": "db-service", "issue": "Missing Network Policy", "severity": "MEDIUM"}
    ]

def background_scan_task(user_email, df_source, scopes=[]):
    with app.app_context():
        SCAN_STATUS['is_scanning'] = True
        SCAN_STATUS['progress'] = 10
        SCAN_STATUS['message'] = "Initializing Scopes..."
        
        df = ensure_df() if df_source is None else df_source.copy()
        
        if scopes:
            df = filter_by_scope(df, scopes)
            SCAN_STATUS['message'] = f"Scanning {', '.join(scopes)}..."
        
        time.sleep(1)
        
        df['severity_norm'] = df['severity'].fillna('LOW').str.upper()
        df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0).astype(float)
        
        db = get_db()
        policies = db.execute('SELECT code, enabled FROM policies').fetchall()
        policy_map = {p['code']: p['enabled'] for p in policies}
        df = df[df['compliance'].apply(lambda x: policy_map.get(str(x).split('-')[0] + '-' + str(x).split('-')[1], 1) == 1 if isinstance(x, str) and '-' in x else True)]

        SCAN_STATUS['progress'] = 50
        SCAN_STATUS['message'] = "Analyzing Threats..."
        
        intel = generate_threat_intel()
        STATE['threat_intel'] = intel
        
        alerts = []
        for _, row in df[df['severity_norm'] == 'CRITICAL'].iterrows():
            msg_text = f"{row['issue']} detected in {row['cloud']}"
            alerts.append({
                "severity": "CRITICAL",
                "msg": msg_text,
                "resource": row['resource_id'],
                "time": datetime.now().strftime("%H:%M")
            })
            
            # AUTOMATIC CRITICAL ALERTS TO EMAIL
            alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO system_alerts (user_email, severity, message, timestamp) VALUES (?, ?, ?, ?)",
                       (user_email, "CRITICAL", msg_text, alert_time))
            trigger_email_alert(user_email, "CRITICAL", msg_text)
            
        STATE['alerts'] = alerts

        settings = db.execute('SELECT auto_fix_enabled FROM automation_settings WHERE id=1').fetchone()
        findings = []
        for _, row in df.sort_values(by='risk_score', ascending=False).iterrows():
            f = row.to_dict()
            f['remediation'] = f.get('remediation', 'Consult Admin')
            if settings and settings['auto_fix_enabled'] and (row['risk_score'] < 50 or "MFA" in str(row['issue'])):
                f['remediation'] = "AUTO-FIXED"
                f['issue'] = f"[RESOLVED] {f['issue']}"
                f['risk_score'] = 0
                db.execute('INSERT INTO automation_logs (action, resource, timestamp) VALUES (?, ?, ?)', ("Auto-Remediated", row['resource_id'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            findings.append(f)
        db.commit()

        sev_counts = df['severity_norm'].value_counts().to_dict()
        ai_risk = float(round((df['risk_score'].mean() * 0.6 + 40), 2)) if not df.empty else 0
        
        risk_by_service = df.groupby('service')['risk_score'].mean().to_dict()

        # =================================================================
        # UPDATED & IMPROVED: Realistic Hierarchical Attack Graph Data
        # =================================================================
        nodes_dict = {
            "internet": {
                "id": "internet", 
                "label": "🌐\n<b>Internet</b>", 
                "title": "<b>Source Node</b><br>Public Internet & External Threat Actors",
                "group": "attacker",
                "shape": "box",
                "level": 0,
                "font": {"color": "white", "size": 16, "multi": "html"},
                "color": {"background": "#ef4444", "border": "#991b1b", "highlight": {"background": "#dc2626", "border": "#7f1d1d"}}
            }
        }
        edges = []
        
        for f in findings:
            res_id = f['resource_id']
            group = "critical" if f['risk_score'] > 90 else ("warning" if f['risk_score'] > 50 else "safe")
            
            # Determine hierarchy level based on issue/type
            level = 2 # Default internal layer
            issue_lower = str(f['issue']).lower()
            if "public" in issue_lower or "external" in issue_lower or f['resource_type'] in ['EC2', 'VM', 'GCE']:
                level = 1 # Public facing edge
            elif "root" in issue_lower or "admin" in issue_lower or "iam" in issue_lower or "repo" in issue_lower:
                level = 3 # Deepest internal layer (Identity/Code)
            
            # Use clean emojis for icons to avoid canvas font loading crashes
            icon = "☁️"
            if f['resource_type'] in ['EC2', 'VM', 'GCE']: icon = "🖥️"
            elif f['resource_type'] in ['S3', 'Storage']: icon = "🪣"
            elif f['resource_type'] in ['RDS', 'Database']: icon = "🗄️"
            elif f['resource_type'] in ['IAM', 'Identity']: icon = "🔑"
            elif f['resource_type'] in ['Code']: icon = "💻"
            elif f['resource_type'] in ['CRM']: icon = "💼"
            
            label = f"{icon} {f['resource_type']}\n<b>{res_id}</b>"
            title = f"<b>{res_id}</b><br>Risk Score: {f['risk_score']}<br>Vulnerability: {f['issue']}"
            
            if res_id not in nodes_dict:
                nodes_dict[res_id] = {"id": res_id, "label": label, "title": title, "group": group, "level": level, "shape": "box"}
            elif group == "critical":
                nodes_dict[res_id]["group"] = "critical" # Upgrade existing node priority
                
            # Connect edges with descriptive attack vector labels
            if "public" in issue_lower or "external" in issue_lower: 
                edges.append({"from": "internet", "to": res_id, "color": {"color": "#ef4444"}, "label": "Exposed to Web", "font": {"align": "top"}})
            elif "root" in str(f['resource_id']).lower() or "admin" in str(f['resource_id']).lower() or "repo" in issue_lower:
                edges.append({"from": "internet", "to": res_id, "color": {"color": "#f59e0b"}, "label": "Compromised Credentials", "dashes": True})
            elif f['cloud'] == 'AWS' and res_id != 'i-0a12bc34def':
                edges.append({"from": "i-0a12bc34def", "to": res_id, "color": {"color": "#94a3b8"}, "label": "Lateral Movement"})
            elif f['cloud'] == 'Azure' and res_id != 'vm-prod-01':
                edges.append({"from": "vm-prod-01", "to": res_id, "color": {"color": "#94a3b8"}, "label": "Lateral Movement"})
            elif level == 2 and random.random() > 0.5: # Random fallback connection for demonstration
                 edges.append({"from": list(nodes_dict.keys())[1], "to": res_id, "color": {"color": "#94a3b8"}})
        
        nodes = list(nodes_dict.values())
        
        SCAN_STATUS['progress'] = 80
        SCAN_STATUS['message'] = "Saving Data..."
        
        endpoint_count = db.execute('SELECT COUNT(*) as cnt FROM endpoints').fetchone()['cnt']
        
        db.execute('INSERT INTO scans (user_email, scan_date, risk_score, critical_count, findings_json) VALUES (?, ?, ?, ?, ?)',
                   (user_email, datetime.now().strftime("%d %b"), ai_risk, int(sev_counts.get('CRITICAL', 0)), json.dumps(findings)))
        db.commit()
        
        STATE['latest_metrics'] = {
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "severity_dist": { "critical": int(sev_counts.get('CRITICAL', 0)), "high": int(sev_counts.get('HIGH', 0)), "medium": int(sev_counts.get('MEDIUM', 0)), "low": int(sev_counts.get('LOW', 0)) },
            "ai_risk_score": ai_risk,
            "findings": findings[:50],
            "graph_data": {"nodes": nodes, "edges": edges},
            "risk_by_service": risk_by_service,
            "threat_intel": intel,
            "alerts": alerts,
            "dark_web_count": len(intel),
            "endpoint_count": endpoint_count
        }
        
        append_log(f"Scan Completed. Scopes: {', '.join(scopes)}", user_email)
        SCAN_STATUS['progress'] = 100
        SCAN_STATUS['is_scanning'] = False

# -------------------------
# 5. API Layer
# -------------------------
def get_user_tier(email):
    row = get_db().execute("SELECT subscription_tier FROM users WHERE email = ?", (email,)).fetchone()
    return row['subscription_tier'] if row else 'Free'

@app.route('/api/policies')
def api_policies(): return jsonify({"policies": [dict(r) for r in get_db().execute('SELECT * FROM policies').fetchall()]})

@app.route('/api/toggle_policy', methods=['POST'])
def api_toggle_policy():
    db = get_db()
    curr = db.execute('SELECT enabled FROM policies WHERE code=?', (request.json.get('code'),)).fetchone()
    db.execute('UPDATE policies SET enabled=? WHERE code=?', (0 if curr['enabled'] else 1, request.json.get('code')))
    db.commit()
    return jsonify({"status": "ok"})

@app.route('/api/automation_config')
def api_automation_config(): return jsonify({"auto_fix": bool(get_db().execute('SELECT auto_fix_enabled FROM automation_settings WHERE id=1').fetchone()['auto_fix_enabled'])})

@app.route('/api/toggle_automation', methods=['POST'])
def api_toggle_automation():
    enabled = 1 if request.json.get('enabled') else 0
    get_db().execute('UPDATE automation_settings SET auto_fix_enabled=? WHERE id=1', (enabled,)).connection.commit()
    return jsonify({"status": "ok"})

@app.route('/api/automation_logs')
def api_automation_logs(): return jsonify({"logs": [dict(r) for r in get_db().execute('SELECT * FROM automation_logs ORDER BY id DESC LIMIT 10').fetchall()]})

@app.route('/api/get_integrations_status')
def api_get_integrations_status(): return jsonify({"integrations": [dict(r) for r in get_db().execute('SELECT name, status FROM integration_configs').fetchall()]})

@app.route('/api/configure_integration', methods=['POST'])
def api_configure_integration():
    data = request.json
    get_db().execute('UPDATE integration_configs SET status="Connected", url=?, key=?, last_sync=? WHERE name=?', (data.get('url'), data.get('key'), datetime.now().strftime("%Y-%m-%d %H:%M"), data.get('name'))).connection.commit()
    return jsonify({"status": "ok"})

@app.route("/api/preview_fix")
def api_preview_fix():
    df = ensure_df()
    crit = df[df['severity'].str.upper() == 'CRITICAL']['resource_id'].tolist()
    return jsonify({"resources": crit})

@app.route("/api/fix_all_critical", methods=["POST"])
def api_fix_all_critical():
    tier = get_user_tier(session['email'])
    if tier != 'Enterprise':
        return jsonify({"error": "Upgrade to Enterprise for Auto-Fix"}), 403

    df = ensure_df()
    crit_indices = df[df['severity'].str.upper() == 'CRITICAL'].index
    if len(crit_indices) > 0:
        count = len(crit_indices)
        df.loc[crit_indices, 'severity'] = 'LOW'
        df.loc[crit_indices, 'risk_score'] = 0
        df.loc[crit_indices, 'issue'] = df.loc[crit_indices, 'issue'].apply(lambda x: f"[FIXED] {x}")
        STATE['uploaded_df'] = df
        
        db = get_db()
        for idx in crit_indices:
             db.execute('INSERT INTO automation_logs (action, resource, timestamp) VALUES (?, ?, ?)', ("Manual Fix", df.loc[idx, 'resource_id'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.commit()
        
        background_scan_task(session['email'], df)
        return jsonify({"status": "ok", "message": f"Fixed {count} items"})
    return jsonify({"status": "ok", "message": "No criticals"})

@app.route("/api/toggle_continuous", methods=["POST"])
def api_toggle_continuous():
    tier = get_user_tier(session['email'])
    if tier == 'Free':
        return jsonify({"error": "Upgrade to Pro for Continuous Monitoring"}), 403

    STATE['continuous_scan_active'] = not STATE.get('continuous_scan_active', False)
    if STATE['continuous_scan_active']:
        user_email = session['email']
        
        def monitor_loop(email):
            with app.app_context():
                while STATE.get('continuous_scan_active'):
                    STATE['server_health'] = { "cpu": random.randint(10, 60), "ram": random.randint(40, 90) }
                    
                    # --- AUTOMATIC CONTINUOUS THREAT ALERT GENERATOR ---
                    if random.random() < 0.1:  # 10% chance every 3 seconds
                        db = get_db()
                        alert_msgs = [
                            "Suspicious login attempt from foreign IP", 
                            "Unexpected port 3389 opened on internal host", 
                            "High CPU usage spike detected (Crypto mining suspected)", 
                            "Malware signature matched on Endpoint Agent"
                        ]
                        msg_text = random.choice(alert_msgs)
                        alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        db.execute("INSERT INTO system_alerts (user_email, severity, message, timestamp) VALUES (?, ?, ?, ?)",
                                   (email, "HIGH", msg_text, alert_time))
                        db.commit()
                        
                        # Automatically triggers the email
                        trigger_email_alert(email, "HIGH", msg_text)
                        
                        STATE['alerts'].insert(0, {
                            "severity": "HIGH",
                            "msg": msg_text,
                            "time": datetime.now().strftime("%H:%M")
                        })
                        STATE['alerts'] = STATE['alerts'][:20]
                        
                    time.sleep(3) 
                    
        threading.Thread(target=monitor_loop, args=(user_email,), daemon=True).start()
    return jsonify({"status": "ok"})

@app.route("/api/update_scan_config", methods=["POST"])
def api_update_scan_config():
    STATE['scan_config']['frequency'] = request.json.get('frequency', '15 min')
    return jsonify({"status": "ok"})

@app.route("/api/upload_cloud", methods=["POST"])
def api_upload_cloud():
    file = request.files.get('file')
    if file:
        STATE['uploaded_df'] = pd.read_csv(file)
        STATE['latest_metrics'] = {} 
        return jsonify({"status": "ok"})
    return jsonify({"error": "No file"})

@app.route("/download_demo_template")
def download_demo_template():
    return send_file(io.BytesIO(load_sample_df().to_csv(index=False).encode()), download_name="cspm_template.csv", as_attachment=True, mimetype="text/csv")

@app.route("/api/connect_aws", methods=["POST"])
def api_connect_aws():
    get_db().execute('UPDATE integration_configs SET status="Connected" WHERE name="AWS"').connection.commit()
    return jsonify({"status": "ok"})

@app.route("/api/run_scan", methods=["POST"])
def api_run_scan():
    if SCAN_STATUS['is_scanning']: return jsonify({"status": "busy"})
    scopes = request.json.get('scopes', [])
    threading.Thread(target=background_scan_task, args=(session['email'], ensure_df(), scopes)).start()
    return jsonify({"status": "started"})

@app.route("/api/scan_status")
def api_scan_status(): return jsonify(SCAN_STATUS)

@app.route("/api/metrics")
def api_metrics():
    db = get_db()
    email = session.get('email', 'admin@cspm.com')
    history_rows = db.execute('SELECT scan_date as date, risk_score FROM scans WHERE user_email = ? ORDER BY id DESC LIMIT 12', (email,)).fetchall()
    history = [dict(r) for r in reversed(history_rows)]
    
    data = STATE.get('latest_metrics', {})
    data['history'] = history 
    data['server_health'] = STATE.get('server_health', {'cpu': 0, 'ram': 0})
    return jsonify({"status":"ok", "data": data})

@app.route("/api/compliance_breakdown")
def api_compliance(): return jsonify({"status": "ok", "data": ensure_df()['compliance'].fillna('Other').apply(lambda x: x.split('-')[0]).value_counts().to_dict()})

@app.route("/api/compliance_scorecard")
def api_compliance_scorecard():
    scorecard = [
        {"framework": "SOC 2 Type II", "status": "Passing", "score": 92, "passed": True},
        {"framework": "PCI DSS v4.0", "status": "Failing", "score": 65, "passed": False},
        {"framework": "HIPAA", "status": "Passing", "score": 88, "passed": True},
        {"framework": "ISO 27001", "status": "Passing", "score": 95, "passed": True}
    ]
    return jsonify({"status": "ok", "scorecard": scorecard})

@app.route("/api/k8s_posture")
def api_k8s_posture():
    return jsonify({"status": "ok", "findings": generate_k8s_findings()})

@app.route("/api/darkweb_feed")
def api_darkweb_feed():
    return jsonify({"status": "ok", "data": generate_detailed_darkweb_data()})

@app.route("/api/assets")
def api_assets(): return jsonify({"status":"ok", "assets": ensure_df().fillna('').to_dict(orient='records')})

@app.route("/api/user_history")
def api_user_history():
    if not session.get('email'): return jsonify({"history": []})
    hist = [dict(r) for r in get_db().execute('SELECT scan_date as date, risk_score, critical_count FROM scans WHERE user_email = ? ORDER BY id DESC LIMIT 30', (session['email'],)).fetchall()]
    return jsonify({"status": "ok", "history": list(reversed(hist))})

@app.route("/api/get_profile")
def api_get_profile(): 
    user = get_db().execute('SELECT email, role, full_name, organization, subscription_tier FROM users WHERE email = ?', (session['email'],)).fetchone()
    token_row = get_db().execute('SELECT token FROM api_tokens WHERE user_email = ? ORDER BY id DESC LIMIT 1', (session['email'],)).fetchone()
    if user:
        u_dict = dict(user)
        u_dict['api_token'] = token_row['token'] if token_row else None
        return jsonify(u_dict)
    return jsonify({"error": "User not found"}), 404

@app.route("/api/update_profile", methods=["POST"])
def api_update_profile():
    get_db().execute('UPDATE users SET full_name = ?, organization = ? WHERE email = ?', (request.json.get('full_name'), request.json.get('organization'), session['email'])).connection.commit()
    return jsonify({"status": "ok"})

@app.route("/api/upgrade_plan", methods=["POST"])
def api_upgrade_plan():
    new_tier = request.json.get('tier', 'Free')
    get_db().execute('UPDATE users SET subscription_tier = ? WHERE email = ?', (new_tier, session['email'])).connection.commit()
    return jsonify({"status": "ok", "tier": new_tier})

@app.route("/api/generate_token", methods=["POST"])
def api_generate_token():
    new_token = uuid.uuid4().hex
    get_db().execute('INSERT INTO api_tokens (user_email, token, created_at) VALUES (?, ?, ?)', (session['email'], new_token, datetime.now().strftime("%Y-%m-%d"))).connection.commit()
    return jsonify({"status": "ok", "token": new_token})

@app.route("/api/check_tier")
def api_check_tier():
    feature = request.args.get('feature')
    tier = get_user_tier(session['email'])
    allowed = True
    if feature == 'report' and tier == 'Free': allowed = False
    if feature == 'autofix' and tier != 'Enterprise': allowed = False
    return jsonify({"allowed": allowed, "tier": tier})

@app.route('/api/endpoints')
def api_endpoints():
    db = get_db()
    rows = db.execute('SELECT * FROM endpoints').fetchall()
    return jsonify({"endpoints": [dict(r) for r in rows]})

@app.route('/api/endpoint_action', methods=['POST'])
def api_endpoint_action():
    data = request.json
    eid = data.get('id')
    action = data.get('action')
    db = get_db()
    
    msg = "Action completed"
    if action == 'isolate':
        db.execute("UPDATE endpoints SET status='Isolated', firewall=1 WHERE id=?", (eid,))
        msg = "Host ISOLATED from network. All traffic blocked."
    elif action == 'unisolate':
        db.execute("UPDATE endpoints SET status='Healthy' WHERE id=?", (eid,))
        msg = "Isolation removed. Host reconnected to network."
    elif action == 'scan':
        result = random.choice(['Clean', 'Malware Detected'])
        db.execute("UPDATE endpoints SET av_status=? WHERE id=?", (result, eid,))
        msg = f"Deep scan finished. Status: {result}"
        background_scan_task('system', None)
    elif action == 'memory-dump':
        msg = "Memory dump captured. Saved to forensics folder for analysis."
    elif action == 'kill-process':
        msg = "Suspicious process terminated successfully."
    elif action == 'patch':
        msg = "Security patch deployed to endpoint."
    
    db.commit()
    
    # AUTOMATIC ACTION ALERT TO EMAIL
    trigger_email_alert(session['email'], "INFO", f"Automated EDR Action Executed: {msg}")
    
    return jsonify({"status": "ok", "message": msg})

@app.route('/api/threats')
def api_threats():
    db = get_db()
    
    active = db.execute("SELECT COUNT(*) as cnt FROM threats WHERE status='Active'").fetchone()['cnt']
    all_threats = db.execute('SELECT * FROM threats ORDER BY detected_at DESC LIMIT 10').fetchall()
    
    detections = []
    for t in all_threats:
        endpoint = db.execute('SELECT hostname FROM endpoints WHERE id=?', (t['endpoint_id'],)).fetchone()
        detections.append({
            "id": t['id'],
            "time": t['detected_at'],
            "hostname": endpoint['hostname'] if endpoint else 'Unknown',
            "threat_name": t['threat_name'],
            "severity": t['severity']
        })
    
    return jsonify({
        "active": active,
        "blocked": random.randint(45, 120),
        "quarantine": random.randint(5, 20),
        "false_positives": random.randint(0, 3),
        "detections": detections
    })

@app.route('/api/live_metrics')
def api_live_metrics():
    """Real-time system metrics for live monitoring"""
    cpu = random.randint(15, 85)
    ram = random.randint(30, 70)
    
    events = [
        {"type": "AUTH", "message": "User login: john.doe from 192.168.1.50", "time": datetime.now().strftime("%H:%M:%S")},
        {"type": "SCAN", "message": "Endpoint scan completed on LAPTOP-WIN-001", "time": datetime.now().strftime("%H:%M:%S")},
        {"type": "THREAT", "message": "Suspicious file blocked: malware.exe", "time": datetime.now().strftime("%H:%M:%S")},
        {"type": "UPDATE", "message": "Security definitions updated", "time": datetime.now().strftime("%H:%M:%S")}
    ]
    
    return jsonify({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "cpu": cpu,
        "ram": ram,
        "network_speed": round(random.uniform(0.5, 15.2), 1),
        "upload_speed": round(random.uniform(0.1, 5.0), 1),
        "download_speed": round(random.uniform(0.5, 10.0), 1),
        "events": events
    })

@app.route('/api/system_alerts')
def api_system_alerts():
    if not session.get('email'): return jsonify({"alerts": []})
    db = get_db()
    rows = db.execute('SELECT * FROM system_alerts WHERE user_email = ? ORDER BY id DESC LIMIT 50', (session['email'],)).fetchall()
    return jsonify({"alerts": [dict(r) for r in rows]})

@app.route('/api/alert_daemon_status')
def api_alert_daemon_status():
    """Returns the current status of the global alert daemon"""
    return jsonify({"is_running": DAEMON_STATE["is_running"]})

@app.route('/api/toggle_alert_daemon', methods=['POST'])
def api_toggle_alert_daemon():
    """Starts or stops the background email daemon"""
    action = request.json.get('action')
    if action == 'start':
        DAEMON_STATE["is_running"] = True
    elif action == 'stop':
        DAEMON_STATE["is_running"] = False
    return jsonify({"status": "ok", "is_running": DAEMON_STATE["is_running"]})

@app.route("/download_report")
def download_report():
    if get_user_tier(session['email']) == 'Free':
        return "Upgrade to Pro to download reports!", 403

    last = STATE.get('latest_metrics', {})
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("Nexus Security Executive Report", styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Generated By:</b> {session.get('email')}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Paragraph(f"<b>Organization:</b> Nexus Enterprise Posture", styles['Normal']))
    story.append(Spacer(1, 24))
    
    story.append(Paragraph("Executive Summary", styles['Heading2']))
    story.append(Paragraph(f"Current Risk Score: {last.get('ai_risk_score', 'N/A')}", styles['Heading3']))
    story.append(Paragraph(f"Active Endpoints: {last.get('endpoint_count', 0)}", styles['Normal']))
    
    story.append(Spacer(1, 12))
    story.append(Paragraph("Critical Findings", styles['Heading2']))
    
    table_data = [['Resource ID', 'Issue', 'Remediation']]
    for f in last.get('findings', [])[:20]:
        table_data.append([str(f.get('resource_id', 'N/A')), str(f.get('issue', 'N/A')), str(f.get('remediation', 'N/A'))])
    
    if len(table_data) > 1:
        t = Table(table_data, colWidths=[120, 250, 150])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        story.append(t)
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("Threat Intelligence Summary", styles['Heading2']))
    if last.get('threat_intel'):
        ti_data = [['Source', 'Data Type', 'Date']]
        for ti in last.get('threat_intel'):
            ti_data.append([str(ti.get('source')), str(ti.get('data')), str(ti.get('date'))])
        t2 = Table(ti_data, colWidths=[150, 150, 100])
        t2.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t2)

    doc.build(story)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="security_report.pdf", mimetype="application/pdf")

# -------------------------
# 6. Auth
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_db().execute('SELECT * FROM users WHERE email = ?', (request.form.get("email"),)).fetchone()
        if user and check_password_hash(user['password'], request.form.get("password")):
            session["email"] = user['email']
            
            # AUTOMATIC LOGIN ALERT TO EMAIL
            trigger_email_alert(user['email'], "INFO", "New successful login detected from a new session.")
            
            return redirect(url_for("index"))
        return render_template_string(AUTH_HTML, mode="login", error="Invalid Credentials")
    return render_template_string(AUTH_HTML, mode="login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            user_email = request.form.get("email")
            get_db().execute('INSERT INTO users (email, password, role, full_name, organization, subscription_tier) VALUES (?, ?, ?, ?, ?, ?)', 
                             (user_email, generate_password_hash(request.form.get("password")), 'Viewer', request.form.get("full_name"), request.form.get("org_name"), 'Free')).connection.commit()
            
            # AUTOMATIC REGISTRATION WELCOME EMAIL
            trigger_email_alert(user_email, "INFO", "Welcome to Nexus Security. Your account has been successfully created.")
            
            return redirect(url_for("login"))
        except: return render_template_string(AUTH_HTML, mode="register", error="Error registering")
    return render_template_string(AUTH_HTML, mode="register")

@app.route("/logout")
def logout(): session.pop("email", None); return redirect(url_for("login"))

@app.route("/")
def index():
    if not session.get("email"): return redirect(url_for("login"))
    return render_template_string(DASHBOARD_HTML, user=session['email'])


# ==========================================
# GLOBAL ALERT DAEMON
# ==========================================
def global_alert_daemon():
    """
    Runs continuously in the background independently of web requests.
    Fetches users from the DB and blasts alerts every 10 to 20 seconds.
    """
    while True:
        # Check if the user has enabled the daemon
        if not DAEMON_STATE["is_running"]:
            time.sleep(2)
            continue
            
        # Wait a random time between 10 and 20 seconds
        time.sleep(random.randint(10, 20))
        
        # Double check after sleeping to ensure we don't send if stopped during sleep
        if not DAEMON_STATE["is_running"]:
            continue
        
        try:
            # Create an independent connection for the background thread
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            users = conn.execute('SELECT email FROM users').fetchall()
            
            if users:
                alert_msgs = [
                    "Suspicious login attempt from foreign IP",
                    "Unexpected port 3389 opened on internal host",
                    "High CPU usage spike detected (Crypto mining suspected)",
                    "Malware signature matched on Endpoint Agent",
                    "Unauthorized IAM policy modification detected",
                    "Publicly accessible S3 bucket exposed"
                ]
                
                # Pick a random alert and severity
                msg_text = random.choice(alert_msgs)
                severity = random.choice(["HIGH", "CRITICAL", "WARN"])
                alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                for u in users:
                    user_email = u['email']
                    
                    # 1. Insert alert into the database so it appears in the dashboard
                    conn.execute("INSERT INTO system_alerts (user_email, severity, message, timestamp) VALUES (?, ?, ?, ?)",
                               (user_email, severity, msg_text, alert_time))
                    conn.commit()

                    # 2. Automatically trigger the email to the user
                    trigger_email_alert(user_email, severity, msg_text)
                    
            conn.close()
        except Exception as e:
            print(f"[Daemon Error] Failed to generate global alert: {e}")

if __name__ == '__main__':
    init_db()
    
    # Start the continuous email alerting daemon thread before running the server
    threading.Thread(target=global_alert_daemon, daemon=True).start()
    
    app.run(debug=True, port=5000)