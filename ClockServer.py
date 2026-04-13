#!/usr/bin/env python3
"""
Ultimate Professional Digital Clock Server
Single-file Flask application with full customization and NTP sync
"""

# ============================================================================
# CONFIGURATION
# ============================================================================
PORT = 5100  # Change this to your preferred port
NTP_SERVER = "10.1.248.1"  # NTP server for time synchronization
NTP_SYNC_INTERVAL = 3600  # Sync with NTP every hour (in seconds)

# ============================================================================
# IMPORTS
# ============================================================================
from flask import Flask, render_template_string, jsonify, request
import datetime
import json
import os
import time
import threading

# Try to import ntplib for NTP support
try:
    import ntplib
    NTP_AVAILABLE = True
except ImportError:
    NTP_AVAILABLE = False
    print("Warning: ntplib not installed. Install with: pip install ntplib")
    print("Falling back to system time.")

app = Flask(__name__)

# ============================================================================
# GLOBAL STATE
# ============================================================================
SETTINGS_FILE = 'clock_settings.json'
ntp_offset = 0  # Offset between NTP time and system time
last_ntp_sync = 0
settings_version = time.time()  # Increments when settings change

# Default settings with full customization
DEFAULT_SETTINGS = {
    # Basic settings
    'theme': 'minimal',
    'format': '24hr',
    'showSeconds': True,
    'showDate': True,
    'animation': 'flip',  # 'flip', 'slide', 'fade', 'none'
    
    # Advanced customization
    'customColors': False,
    'timeColor': '#ffffff',
    'dateColor': 'rgba(255, 255, 255, 0.8)',
    'backgroundColor1': '#667eea',
    'backgroundColor2': '#764ba2',
    'clockBackground': 'rgba(255, 255, 255, 0.1)',
    'borderColor': 'rgba(255, 255, 255, 0.2)',
    
    # Typography
    'fontSize': 140,  # Range: 60-600px
    'fontWeight': '200',
    'letterSpacing': 12,
    'fontFamily': 'Segoe UI',
    
    # Effects
    'showBorder': False,
    'borderWidth': 2,
    'borderRadius': 12,
    'shadowIntensity': 'medium',
    'glowEnabled': False,
    'glowColor': '#ffffff',
    'glowIntensity': 'medium',
    
    # Layout
    'clockPadding': 50,
    'dateSize': 32,
    'dateSpacing': 30,
}

# ============================================================================
# NTP SYNCHRONIZATION
# ============================================================================
def sync_ntp_time():
    """Sync with NTP server to get accurate time"""
    global ntp_offset, last_ntp_sync
    
    if not NTP_AVAILABLE:
        return
    
    try:
        client = ntplib.NTPClient()
        response = client.request(NTP_SERVER, version=3, timeout=5)
        
        # Calculate offset between NTP time and system time
        ntp_time = response.tx_time
        system_time = time.time()
        ntp_offset = ntp_time - system_time
        last_ntp_sync = system_time
        
        offset_ms = ntp_offset * 1000
        print(f"NTP sync successful. Offset: {offset_ms:.2f}ms from {NTP_SERVER}")
        
    except Exception as e:
        print(f"NTP sync failed: {e}")
        # Keep previous offset if sync fails

def get_ntp_time():
    """Get current time adjusted for NTP offset"""
    return time.time() + ntp_offset

def ntp_sync_thread():
    """Background thread to periodically sync with NTP"""
    while True:
        sync_ntp_time()
        time.sleep(NTP_SYNC_INTERVAL)

# Start NTP sync thread
if NTP_AVAILABLE:
    sync_ntp_time()  # Initial sync
    thread = threading.Thread(target=ntp_sync_thread, daemon=True)
    thread.start()

# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================
def load_settings():
    """Load settings from file or return defaults"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to handle new settings
                settings = DEFAULT_SETTINGS.copy()
                settings.update(loaded)
                return settings
        except:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to file and update version"""
    global settings_version
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
    settings_version = time.time()
    print(f"Settings saved to {SETTINGS_FILE}")

# ============================================================================
# HTML TEMPLATES
# ============================================================================

CLOCK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Clock</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            width: 1920px;
            height: 1080px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            overflow: hidden;
            position: relative;
            transition: background 0.5s ease;
        }

        /* Connection Indicator */
        .connection-indicator {
            position: absolute;
            top: 30px;
            right: 30px;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }

        .connection-indicator.connected {
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .connection-indicator.disconnected {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            transition: all 0.3s;
        }

        .connected .status-dot {
            background: #10b981;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
            animation: pulse 2s ease-in-out infinite;
        }

        .disconnected .status-dot {
            background: #ef4444;
            animation: blink 1s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(0.95); }
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        /* NTP Indicator */
        .ntp-indicator {
            position: absolute;
            bottom: 30px;
            left: 30px;
            padding: 8px 16px;
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #3b82f6;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            backdrop-filter: blur(10px);
            z-index: 1000;
        }

        /* Clock Container */
        .clock-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            transition: all 0.5s ease;
        }

        /* Time Display */
        .time-display {
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            position: relative;
        }

        .digit-container {
            display: inline-block;
            position: relative;
            overflow: hidden;
            vertical-align: top;
        }

        .digit {
            display: inline-block;
            transition: transform 0.6s cubic-bezier(0.4, 0.0, 0.2, 1);
        }

        /* Flip animation */
        .digit-container.flip .digit {
            transform-origin: center;
        }

        .digit-container.flip .digit.flipping {
            animation: flipAnimation 0.6s cubic-bezier(0.4, 0.0, 0.2, 1);
        }

        @keyframes flipAnimation {
            0% { transform: rotateX(0deg); }
            50% { transform: rotateX(90deg); }
            100% { transform: rotateX(0deg); }
        }

        /* Slide animation */
        .digit-container.slide {
            overflow: hidden;
        }

        .digit-container.slide .digit.sliding-up {
            animation: slideUp 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
        }

        .digit-container.slide .digit.sliding-down {
            animation: slideDown 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
        }

        @keyframes slideUp {
            0% { transform: translateY(100%); opacity: 0; }
            100% { transform: translateY(0); opacity: 1; }
        }

        @keyframes slideDown {
            0% { transform: translateY(-100%); opacity: 0; }
            100% { transform: translateY(0); opacity: 1; }
        }

        /* Fade animation */
        .digit-container.fade .digit.fading {
            animation: fadeInOut 0.3s ease-in-out;
        }

        @keyframes fadeInOut {
            0% { opacity: 0; transform: scale(0.9); }
            50% { opacity: 0.5; }
            100% { opacity: 1; transform: scale(1); }
        }

        .colon {
            opacity: 0.6;
            display: inline-block;
            margin: 0 0.1em;
        }

        .date-display {
            user-select: none;
            transition: all 0.3s ease;
        }

        /* Disconnected overlay */
        .disconnected-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 999;
            backdrop-filter: blur(10px);
        }

        .disconnected-overlay.show {
            display: flex;
        }

        .disconnected-message {
            background: #ffffff;
            padding: 40px 60px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .disconnected-message h2 {
            color: #ef4444;
            font-size: 32px;
            margin-bottom: 16px;
        }

        .disconnected-message p {
            color: #6b7280;
            font-size: 18px;
        }

        /* Keyboard shortcut help */
        .help-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }

        .help-overlay.show {
            display: flex;
        }

        .help-content {
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            max-width: 600px;
        }

        .help-content h2 {
            margin-bottom: 20px;
            color: #1a202c;
        }

        .shortcut {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
        }

        .shortcut kbd {
            background: #f3f4f6;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="connection-indicator connected">
        <div class="status-dot"></div>
        <span class="status-text">Connected</span>
    </div>

    <div class="ntp-indicator" id="ntpIndicator" style="display: none;">
        🕐 NTP Synced
    </div>

    <div class="clock-container">
        <div class="time-display" id="timeDisplay"></div>
        <div class="date-display" id="dateDisplay">Loading...</div>
    </div>

    <div class="disconnected-overlay" id="disconnectedOverlay">
        <div class="disconnected-message">
            <h2>Server Disconnected</h2>
            <p>Connection to clock server lost</p>
        </div>
    </div>

    <div class="help-overlay" id="helpOverlay">
        <div class="help-content">
            <h2>⌨️ Keyboard Shortcuts</h2>
            <div class="shortcut">
                <span>Toggle Fullscreen</span>
                <kbd>F11</kbd>
            </div>
            <div class="shortcut">
                <span>Hide Controls</span>
                <kbd>H</kbd>
            </div>
            <div class="shortcut">
                <span>Cycle Themes</span>
                <kbd>T</kbd>
            </div>
            <div class="shortcut">
                <span>Toggle Date</span>
                <kbd>D</kbd>
            </div>
            <div class="shortcut">
                <span>Toggle Seconds</span>
                <kbd>S</kbd>
            </div>
            <div class="shortcut">
                <span>Show This Help</span>
                <kbd>?</kbd>
            </div>
            <div class="shortcut">
                <span>Close Help</span>
                <kbd>ESC</kbd>
            </div>
        </div>
    </div>

    <script>
        let settings = {};
        let isConnected = true;
        let serverTimeOffset = 0;
        let lastSettingsVersion = 0;
        let currentTime = '';
        let animatingDigits = new Set();
        let controlsVisible = true;

        const themes = ['minimal', 'modern', 'elegant', 'neon', 'corporate', 'matrix', 'retro', 'glass'];

        // Open settings in new window
        function openSettings() {
            window.open('/settings', 'Settings', 'width=900,height=1000');
        }

        // Load settings from server
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                if (!response.ok) throw new Error('Failed to load settings');
                const data = await response.json();
                
                // Check if settings changed
                if (data.version !== lastSettingsVersion && lastSettingsVersion !== 0) {
                    console.log('Settings changed, reloading page...');
                    location.reload();
                    return;
                }
                
                lastSettingsVersion = data.version;
                settings = data.settings;
                applySettings();
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        }

        // Apply settings to display
        function applySettings() {
            const timeDisplay = document.getElementById('timeDisplay');
            const dateDisplay = document.getElementById('dateDisplay');
            const body = document.body;
            const container = document.querySelector('.clock-container');

            if (settings.customColors) {
                // Custom colors
                timeDisplay.style.color = settings.timeColor;
                dateDisplay.style.color = settings.dateColor;
                
                // Background
                body.style.background = `linear-gradient(135deg, ${settings.backgroundColor1} 0%, ${settings.backgroundColor2} 100%)`;
                
                // Clock background
                timeDisplay.style.background = settings.clockBackground;
                
                // Border
                if (settings.showBorder) {
                    timeDisplay.style.border = `${settings.borderWidth}px solid ${settings.borderColor}`;
                } else {
                    timeDisplay.style.border = 'none';
                }
            } else {
                // Apply theme
                applyTheme(settings.theme || 'minimal');
            }

            // Typography
            timeDisplay.style.fontSize = (settings.fontSize || 140) + 'px';
            timeDisplay.style.fontWeight = settings.fontWeight || '200';
            timeDisplay.style.letterSpacing = (settings.letterSpacing || 12) + 'px';
            timeDisplay.style.fontFamily = settings.fontFamily || 'Segoe UI';

            // Effects
            timeDisplay.style.borderRadius = (settings.borderRadius || 12) + 'px';
            timeDisplay.style.padding = `${settings.clockPadding || 50}px ${(settings.clockPadding || 50) * 2}px`;

            // Shadow
            applyShadow(timeDisplay, settings.shadowIntensity || 'medium');

            // Glow
            if (settings.glowEnabled) {
                applyGlow(timeDisplay, settings.glowColor || '#ffffff', settings.glowIntensity || 'medium');
            } else {
                timeDisplay.style.textShadow = '';
            }

            // Date
            dateDisplay.style.fontSize = (settings.dateSize || 32) + 'px';
            container.style.gap = (settings.dateSpacing || 30) + 'px';
        }

        // Apply theme presets
        function applyTheme(theme) {
            const timeDisplay = document.getElementById('timeDisplay');
            const dateDisplay = document.getElementById('dateDisplay');
            const body = document.body;

            // Reset custom styles
            timeDisplay.style.background = '';
            timeDisplay.style.border = '';
            timeDisplay.style.padding = '';

            switch(theme) {
                case 'minimal':
                    body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                    timeDisplay.style.color = '#ffffff';
                    dateDisplay.style.color = 'rgba(255, 255, 255, 0.8)';
                    break;
                case 'modern':
                    body.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)';
                    timeDisplay.style.color = '#1a202c';
                    timeDisplay.style.background = '#ffffff';
                    timeDisplay.style.padding = '50px 100px';
                    dateDisplay.style.color = '#2d3748';
                    break;
                case 'elegant':
                    body.style.background = 'linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%)';
                    timeDisplay.style.color = '#d4af37';
                    timeDisplay.style.background = 'rgba(0, 0, 0, 0.3)';
                    timeDisplay.style.border = '2px solid rgba(212, 175, 55, 0.3)';
                    timeDisplay.style.padding = '60px 120px';
                    dateDisplay.style.color = '#c0c0c0';
                    break;
                case 'neon':
                    body.style.background = '#0a0a0a';
                    timeDisplay.style.color = '#00ff88';
                    dateDisplay.style.color = '#00ccff';
                    break;
                case 'corporate':
                    body.style.background = '#ffffff';
                    timeDisplay.style.color = '#2563eb';
                    timeDisplay.style.borderLeft = '8px solid #2563eb';
                    timeDisplay.style.background = 'linear-gradient(to right, rgba(37, 99, 235, 0.03), transparent)';
                    timeDisplay.style.padding = '50px 100px';
                    dateDisplay.style.color = '#64748b';
                    break;
                case 'matrix':
                    body.style.background = '#000000';
                    timeDisplay.style.color = '#00ff00';
                    timeDisplay.style.fontFamily = 'Courier New, monospace';
                    dateDisplay.style.color = '#00aa00';
                    break;
                case 'retro':
                    body.style.background = 'linear-gradient(135deg, #ff6b6b 0%, #feca57 100%)';
                    timeDisplay.style.color = '#2d3436';
                    timeDisplay.style.background = 'rgba(255, 255, 255, 0.9)';
                    timeDisplay.style.padding = '40px 80px';
                    timeDisplay.style.border = '4px solid #2d3436';
                    dateDisplay.style.color = '#2d3436';
                    break;
                case 'glass':
                    body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                    timeDisplay.style.color = '#ffffff';
                    timeDisplay.style.background = 'rgba(255, 255, 255, 0.1)';
                    timeDisplay.style.backdropFilter = 'blur(20px)';
                    timeDisplay.style.border = '1px solid rgba(255, 255, 255, 0.2)';
                    timeDisplay.style.padding = '50px 100px';
                    dateDisplay.style.color = 'rgba(255, 255, 255, 0.9)';
                    break;
            }
        }

        // Apply shadow effect
        function applyShadow(element, intensity) {
            const shadows = {
                'none': 'none',
                'light': '0 4px 12px rgba(0, 0, 0, 0.1)',
                'medium': '0 10px 25px rgba(0, 0, 0, 0.15)',
                'strong': '0 20px 40px rgba(0, 0, 0, 0.25)'
            };
            element.style.boxShadow = shadows[intensity] || shadows.medium;
        }

        // Apply glow effect
        function applyGlow(element, color, intensity) {
            const glowSizes = {
                'light': '20px',
                'medium': '40px',
                'strong': '60px'
            };
            const size = glowSizes[intensity] || '40px';
            element.style.textShadow = `0 0 ${size} ${color}`;
        }

        // Heartbeat check
        async function checkHeartbeat() {
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 2000);

                const response = await fetch('/api/heartbeat', {
                    signal: controller.signal
                });

                clearTimeout(timeout);

                if (!response.ok) throw new Error('Heartbeat failed');

                if (!isConnected) {
                    isConnected = true;
                    updateConnectionStatus();
                    await syncTime();
                }
            } catch (error) {
                if (isConnected) {
                    isConnected = false;
                    updateConnectionStatus();
                }
            }
        }

        // Update connection status UI
        function updateConnectionStatus() {
            const indicator = document.querySelector('.connection-indicator');
            const statusText = document.querySelector('.status-text');
            const overlay = document.getElementById('disconnectedOverlay');

            if (isConnected) {
                indicator.classList.remove('disconnected');
                indicator.classList.add('connected');
                statusText.textContent = 'Connected';
                overlay.classList.remove('show');
            } else {
                indicator.classList.remove('connected');
                indicator.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                overlay.classList.add('show');
            }
        }

        // Sync time with server
        async function syncTime() {
            try {
                const clientRequestTime = Date.now();
                const response = await fetch('/api/time');
                const clientResponseTime = Date.now();
                const data = await response.json();

                const latency = (clientResponseTime - clientRequestTime) / 2;
                const serverTime = data.timestamp * 1000 + latency;
                serverTimeOffset = serverTime - clientResponseTime;

                // Show NTP indicator if NTP is being used
                if (data.ntp_synced) {
                    document.getElementById('ntpIndicator').style.display = 'block';
                }

                console.log('Time synced. Offset:', serverTimeOffset, 'ms', data.ntp_synced ? '(NTP)' : '(System)');
            } catch (error) {
                console.error('Error syncing time:', error);
            }
        }

        // Get synchronized time
        function getSyncedTime() {
            if (!isConnected) {
                return null;
            }
            return new Date(Date.now() + serverTimeOffset);
        }

        // Create digit element
        function createDigit(char, animation) {
            const container = document.createElement('span');
            container.className = `digit-container ${animation}`;
            
            const digit = document.createElement('span');
            digit.className = 'digit';
            digit.textContent = char;
            
            container.appendChild(digit);
            return container;
        }

        // Update digit with animation
        function updateDigit(container, newChar, animation) {
            const digit = container.querySelector('.digit');
            const oldChar = digit.textContent;

            if (oldChar === newChar) return;

            // Apply animation class
            if (animation === 'flip') {
                digit.classList.add('flipping');
                setTimeout(() => {
                    digit.textContent = newChar;
                }, 300);
                setTimeout(() => {
                    digit.classList.remove('flipping');
                }, 600);
            } else if (animation === 'slide') {
                const direction = newChar > oldChar ? 'sliding-up' : 'sliding-down';
                digit.classList.add(direction);
                digit.textContent = newChar;
                setTimeout(() => {
                    digit.classList.remove(direction);
                }, 400);
            } else if (animation === 'fade') {
                digit.classList.add('fading');
                digit.textContent = newChar;
                setTimeout(() => {
                    digit.classList.remove('fading');
                }, 300);
            } else {
                digit.textContent = newChar;
            }
        }

        // Format time based on settings
        function formatTime(date) {
            let hours = date.getHours();
            const minutes = date.getMinutes();
            const seconds = date.getSeconds();

            let timeString = '';

            if (settings.format === '12hr') {
                const ampm = hours >= 12 ? 'PM' : 'AM';
                hours = hours % 12;
                hours = hours ? hours : 12;
                timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
                if (settings.showSeconds !== false) {
                    timeString += `:${String(seconds).padStart(2, '0')}`;
                }
                timeString += ` ${ampm}`;
            } else {
                timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
                if (settings.showSeconds !== false) {
                    timeString += `:${String(seconds).padStart(2, '0')}`;
                }
            }

            return timeString;
        }

        // Format date
        function formatDate(date) {
            const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            const months = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'];

            return `${days[date.getDay()]}, ${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
        }

        // Update clock display with animation
        function updateClock() {
            if (!isConnected) {
                document.getElementById('timeDisplay').textContent = '--:--:--';
                document.getElementById('dateDisplay').textContent = 'Server Disconnected';
                return;
            }

            const now = getSyncedTime();
            const newTime = formatTime(now);
            
            const timeDisplay = document.getElementById('timeDisplay');
            const animation = settings.animation || 'flip';

            // Initialize display if empty
            if (timeDisplay.children.length === 0 || currentTime === '') {
                timeDisplay.innerHTML = '';
                for (let char of newTime) {
                    if (char === ':') {
                        const colon = document.createElement('span');
                        colon.className = 'colon';
                        colon.textContent = ':';
                        timeDisplay.appendChild(colon);
                    } else if (char === ' ') {
                        timeDisplay.appendChild(document.createTextNode(' '));
                    } else {
                        timeDisplay.appendChild(createDigit(char, animation));
                    }
                }
            } else {
                // Update digits with animation
                let digitIndex = 0;
                const containers = timeDisplay.querySelectorAll('.digit-container');
                
                for (let char of newTime) {
                    if (char !== ':' && char !== ' ') {
                        if (containers[digitIndex]) {
                            updateDigit(containers[digitIndex], char, animation);
                        }
                        digitIndex++;
                    }
                }
            }

            currentTime = newTime;

            // Update date
            if (settings.showDate !== false) {
                document.getElementById('dateDisplay').style.display = 'block';
                document.getElementById('dateDisplay').textContent = formatDate(now);
            } else {
                document.getElementById('dateDisplay').style.display = 'none';
            }
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            switch(e.key.toLowerCase()) {
                case 'h':
                    toggleControls();
                    break;
                case 't':
                    cycleTheme();
                    break;
                case 'd':
                    toggleDate();
                    break;
                case 's':
                    toggleSeconds();
                    break;
                case '?':
                    document.getElementById('helpOverlay').classList.add('show');
                    break;
                case 'escape':
                    document.getElementById('helpOverlay').classList.remove('show');
                    break;
            }
        });

        // Toggle controls visibility
        function toggleControls() {
            controlsVisible = !controlsVisible;
            const controls = [
                document.querySelector('.connection-indicator'),
                document.getElementById('ntpIndicator')
            ];
            controls.forEach(el => {
                if (el) el.style.display = controlsVisible ? '' : 'none';
            });
        }

        // Cycle through themes
        function cycleTheme() {
            const currentTheme = settings.theme || 'minimal';
            const currentIndex = themes.indexOf(currentTheme);
            const nextIndex = (currentIndex + 1) % themes.length;
            settings.theme = themes[nextIndex];
            settings.customColors = false;
            applySettings();
        }

        // Toggle date
        function toggleDate() {
            settings.showDate = !settings.showDate;
            updateClock();
        }

        // Toggle seconds
        function toggleSeconds() {
            settings.showSeconds = !settings.showSeconds;
            currentTime = ''; // Force rebuild
            updateClock();
        }

        // Initialize
        async function init() {
            await loadSettings();
            await syncTime();
            
            updateClock();

            // Update clock every 50ms for smooth display
            setInterval(updateClock, 50);

            // Heartbeat check every second
            setInterval(checkHeartbeat, 1000);

            // Re-sync time every 10 seconds
            setInterval(syncTime, 10000);

            // Check for settings changes every 2 seconds
            setInterval(loadSettings, 2000);
        }

        init();
    </script>
</body>
</html>
"""

BROADCAST_CLOCK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Broadcast Clock</title>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@900&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #050505;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }
  /* Hidden until we have a confirmed sync with the server.
     If the server dies, we hide again — we never show local-clock time. */
  canvas { display: none; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

// ── NTP SYNC (mirrors the / clock's algorithm) ───────────────
// Keep the canvas render loop authoritative against the server's
// NTP-synced time rather than the browser's local clock. If the
// server can no longer be reached, we HIDE the canvas — we must
// never fall back to the browser's local clock on a broadcast feed.
let serverTimeOffset = 0;
let isConnected = false;

function setConnected(state) {
  if (state === isConnected) return;
  isConnected = state;
  canvas.style.display = state ? 'block' : 'none';
  if (!state) console.warn('Broadcast clock hidden: server unreachable');
  else        console.log('Broadcast clock visible: sync OK');
}

async function syncTime() {
  try {
    const ctrl = new AbortController();
    const to   = setTimeout(() => ctrl.abort(), 2000);
    const t0   = Date.now();
    const res  = await fetch('/api/time', { signal: ctrl.signal });
    const t1   = Date.now();
    clearTimeout(to);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    // Half-RTT latency compensation, matching the / clock
    const latency = (t1 - t0) / 2;
    serverTimeOffset = (data.timestamp * 1000 + latency) - t1;
    setConnected(true);
    console.log('Broadcast clock synced. Offset:', serverTimeOffset, 'ms',
                data.ntp_synced ? '(NTP)' : '(System)');
  } catch (err) {
    setConnected(false);
    console.warn('Broadcast clock sync failed:', err);
  }
}

async function checkHeartbeat() {
  try {
    const ctrl = new AbortController();
    const to   = setTimeout(() => ctrl.abort(), 2000);
    const res  = await fetch('/api/heartbeat', { signal: ctrl.signal });
    clearTimeout(to);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    // Came back from a dead state → re-sync before we become visible.
    if (!isConnected) await syncTime();
  } catch (err) {
    setConnected(false);
  }
}

function getSyncedNow() {
  return new Date(Date.now() + serverTimeOffset);
}

function setSize() {
  const s = Math.min(window.innerWidth, window.innerHeight) * 0.88;
  canvas.width = s;
  canvas.height = s;
}
setSize();
window.addEventListener('resize', setSize);

function draw() {
  // If we've lost the server, stay hidden and skip rendering entirely —
  // the canvas is display:none anyway so drawing would be wasted. Keep
  // the rAF loop alive so we resume instantly on reconnect.
  if (!isConnected) {
    requestAnimationFrame(draw);
    return;
  }

  const W = canvas.width;
  const cx = W / 2, cy = W / 2;
  const R = W / 2 * 0.96;

  ctx.clearRect(0, 0, W, W);

  const now   = getSyncedNow();
  const hours   = now.getHours();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  const ms      = now.getMilliseconds();

  // Fraction through current second → drives CCW sweep
  const frac = ms / 1000;

  // ── OUTER DROP SHADOW ──────────────────────────────────────
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.7)';
  ctx.shadowBlur  = W * 0.07;
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.fillStyle = '#111';
  ctx.fill();
  ctx.restore();

  // ── BEZEL BASE ────────────────────────────────────────────
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  const bezelGrad = ctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
  bezelGrad.addColorStop(0,   '#2e2e2e');
  bezelGrad.addColorStop(0.5, '#1a1a1a');
  bezelGrad.addColorStop(1,   '#0e0e0e');
  ctx.fillStyle = bezelGrad;
  ctx.fill();

  // ── TICK MARKS & LABELS ───────────────────────────────────
  const tickOuterR = R * 0.97;
  const tickInnerR = R * 0.895; // uniform length for all ticks
  const labelR     = R * 0.815; // sits in bezel band between tick inner and copper ring

  // Simple broadcast mode: one tick lights per second, fills clockwise, clears every minute
  for (let i = 0; i < 60; i++) {
    const angle  = -Math.PI / 2 + (i / 60) * Math.PI * 2;
    const innerR = tickInnerR;

    const x1 = cx + Math.cos(angle) * tickOuterR;
    const y1 = cy + Math.sin(angle) * tickOuterR;
    const x2 = cx + Math.cos(angle) * innerR;
    const y2 = cy + Math.sin(angle) * innerR;

    const lit = i === 0 || (i > 0 && i <= seconds); // tick 0 always on; 1–59 fill per second

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineWidth   = W * 0.005;
    ctx.lineCap     = 'round';
    ctx.strokeStyle = lit ? '#ff8800' : '#3a3a3a';
    ctx.stroke();
  }

  // ── INNER TICK SEPARATOR RING ────────────────────────────
  ctx.beginPath();
  ctx.arc(cx, cy, tickInnerR - R * 0.008, 0, Math.PI * 2);
  ctx.strokeStyle = '#b8722a';
  ctx.lineWidth   = R * 0.018;
  ctx.stroke();

  // Labels — always static copper
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'middle';
  ctx.font         = `bold ${W * 0.038}px Rubik, sans-serif`;
  ctx.fillStyle    = '#c08040';
  ctx.shadowBlur   = 0;

  for (let i = 5; i <= 60; i += 5) {
    const angle = -Math.PI / 2 + (i / 60) * Math.PI * 2;
    const nx = cx + Math.cos(angle) * labelR;
    const ny = cy + Math.sin(angle) * labelR;
    ctx.fillText(i === 60 ? '60' : String(i), nx, ny);
  }

  // ── DARK SEPARATOR RING (face edge) ──────────────────────
  const faceR = R * 0.73;
  ctx.beginPath();
  ctx.arc(cx, cy, faceR + R * 0.018, 0, Math.PI * 2);
  ctx.strokeStyle = '#222222';
  ctx.lineWidth   = R * 0.007;
  ctx.shadowBlur  = 0;
  ctx.stroke();

  // ── FACE ──────────────────────────────────────────────────
  ctx.beginPath();
  ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
  ctx.fillStyle = '#080808';
  ctx.fill();

  // Red glow — lower hemisphere, grows redder as seconds progress
  const redIntensity = 0.55 + (seconds / 60) * 0.3;
  const redGrad = ctx.createRadialGradient(cx, cy + faceR * 0.45, faceR * 0.05,
                                           cx, cy + faceR * 0.45, faceR * 1.1);
  redGrad.addColorStop(0,   `rgba(160,0,0,${redIntensity})`);
  redGrad.addColorStop(0.45, `rgba(80,0,0,${redIntensity * 0.6})`);
  redGrad.addColorStop(1,    'rgba(0,0,0,0)');

  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = redGrad;
  ctx.fillRect(cx - faceR, cy - faceR, faceR * 2, faceR * 2);
  ctx.restore();

  // Top dark vignette on face
  const topVig = ctx.createRadialGradient(cx, cy - faceR * 0.2, 0, cx, cy, faceR);
  topVig.addColorStop(0,   'rgba(0,0,0,0.65)');
  topVig.addColorStop(0.55,'rgba(0,0,0,0.1)');
  topVig.addColorStop(1,   'rgba(0,0,0,0)');
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, faceR, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = topVig;
  ctx.fillRect(cx - faceR, cy - faceR, faceR * 2, faceR * 2);
  ctx.restore();

  // ── TIME DISPLAY (fixed positions per segment to prevent shifting) ────
  const pad = n => String(n).padStart(2, '0');
  const fs = W * 0.115;
  ctx.font         = `900 ${fs}px Rubik, sans-serif`;
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'middle';

  // Measure a reference digit width for layout
  const dw  = ctx.measureText('0').width;   // single digit
  const cw  = ctx.measureText(':').width;   // colon
  const segW = dw * 2;                       // two-digit segment width

  // Total width: HH + : + MM + : + SS
  const totalW = segW + cw + segW + cw + segW;
  const startX = cx - totalW / 2;

  function drawSeg(text, x) {
    // glow pass
    ctx.shadowColor = 'rgba(255,255,255,0.35)';
    ctx.shadowBlur  = W * 0.03;
    ctx.fillStyle   = '#ffffff';
    ctx.fillText(text, x, cy);
    // crisp pass
    ctx.shadowBlur = 0;
    ctx.fillStyle  = '#f0ead8';
    ctx.fillText(text, x, cy);
  }

  const hhX = startX + segW / 2;
  const c1X = startX + segW + cw / 2;
  const mmX = startX + segW + cw + segW / 2;
  const c2X = startX + segW + cw + segW + cw / 2;
  const ssX = startX + segW + cw + segW + cw + segW / 2;

  drawSeg(pad(hours),   hhX);
  drawSeg(':',          c1X);
  drawSeg(pad(minutes), mmX);
  drawSeg(':',          c2X);
  drawSeg(pad(seconds), ssX);

  requestAnimationFrame(draw);
}

// Gate the first paint on an NTP sync so the broadcast clock never
// displays browser-local time even for a single frame.
(async () => {
  await document.fonts.ready;
  await syncTime();                   // first sync unhides the canvas (or keeps it hidden)
  setInterval(syncTime,     10000);   // re-sync every 10 s, matches / clock
  setInterval(checkHeartbeat, 1000);  // 1 s heartbeat — hides on server death, recovers on restart
  requestAnimationFrame(draw);
})();
</script>
</body>
</html>
"""

SETTINGS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clock Settings</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 850px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-height: 90vh;
            overflow-y: auto;
        }

        h1 {
            color: #1a202c;
            font-size: 32px;
            margin-bottom: 12px;
        }

        .subtitle {
            color: #64748b;
            font-size: 16px;
            margin-bottom: 40px;
        }

        .success-message {
            background: #10b981;
            color: white;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 24px;
            display: none;
        }

        .success-message.show {
            display: block;
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 32px;
            border-bottom: 2px solid #e5e7eb;
        }

        .tab {
            padding: 12px 24px;
            background: none;
            border: none;
            color: #64748b;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
        }

        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .form-group {
            margin-bottom: 24px;
        }

        label {
            display: block;
            color: #374151;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }

        select, input[type="number"], input[type="text"] {
            width: 100%;
            padding: 10px 14px;
            border: 2px solid #e5e7eb;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s;
            font-family: inherit;
        }

        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        input[type="checkbox"] {
            width: auto;
            cursor: pointer;
        }

        .color-input {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        input[type="color"] {
            width: 60px;
            height: 40px;
            border: 2px solid #e5e7eb;
            border-radius: 6px;
            cursor: pointer;
        }

        .color-text {
            flex: 1;
            font-family: monospace;
            font-size: 13px;
        }

        .range-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        input[type="range"] {
            flex: 1;
        }

        .range-value {
            min-width: 60px;
            text-align: right;
            font-weight: 600;
            color: #667eea;
        }

        .button-group {
            display: flex;
            gap: 12px;
            margin-top: 40px;
            padding-top: 24px;
            border-top: 2px solid #e5e7eb;
        }

        button {
            flex: 1;
            padding: 14px 24px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
            background: #e5e7eb;
            color: #374151;
        }

        .btn-secondary:hover {
            background: #d1d5db;
        }

        .theme-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
            margin-top: 12px;
        }

        .theme-card {
            padding: 24px 16px;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
            font-size: 13px;
            font-weight: 600;
        }

        .theme-card:hover {
            transform: translateY(-2px);
        }

        .theme-card.selected {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .theme-card.minimal { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .theme-card.modern { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #1a202c; }
        .theme-card.elegant { background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%); color: #d4af37; }
        .theme-card.neon { background: #0a0a0a; color: #00ff88; }
        .theme-card.corporate { background: #ffffff; color: #2563eb; border: 2px solid #2563eb; }
        .theme-card.matrix { background: #000000; color: #00ff00; }
        .theme-card.retro { background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%); color: #2d3436; }
        .theme-card.glass { background: rgba(102, 126, 234, 0.3); backdrop-filter: blur(10px); color: white; border: 1px solid rgba(255,255,255,0.3); }

        .section-title {
            font-size: 18px;
            font-weight: 700;
            color: #1a202c;
            margin: 32px 0 16px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #e5e7eb;
        }

        .custom-colors-section {
            background: #f9fafb;
            padding: 20px;
            border-radius: 8px;
            margin-top: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ Clock Settings</h1>
        <p class="subtitle">Customize your digital clock display</p>

        <div class="success-message" id="successMessage">
            Settings saved successfully! Clock will update automatically.
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('basic')">Basic</button>
            <button class="tab" onclick="switchTab('appearance')">Appearance</button>
            <button class="tab" onclick="switchTab('advanced')">Advanced</button>
        </div>

        <form id="settingsForm">
            <!-- Basic Tab -->
            <div id="tab-basic" class="tab-content active">
                <div class="form-group">
                    <label>Theme Preset</label>
                    <div class="theme-grid" id="themeGrid">
                        <div class="theme-card minimal" data-theme="minimal">Minimal</div>
                        <div class="theme-card modern" data-theme="modern">Modern</div>
                        <div class="theme-card elegant" data-theme="elegant">Elegant</div>
                        <div class="theme-card neon" data-theme="neon">Neon</div>
                        <div class="theme-card corporate" data-theme="corporate">Corporate</div>
                        <div class="theme-card matrix" data-theme="matrix">Matrix</div>
                        <div class="theme-card retro" data-theme="retro">Retro</div>
                        <div class="theme-card glass" data-theme="glass">Glass</div>
                    </div>
                    <input type="hidden" id="theme" value="minimal">
                </div>

                <div class="form-group">
                    <label for="format">Time Format</label>
                    <select id="format">
                        <option value="24hr">24-hour (23:59:59)</option>
                        <option value="12hr">12-hour (11:59:59 PM)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="animation">Digit Animation</label>
                    <select id="animation">
                        <option value="flip">Flip</option>
                        <option value="slide">Slide</option>
                        <option value="fade">Fade</option>
                        <option value="none">None</option>
                    </select>
                </div>

                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="showSeconds" checked>
                        <label for="showSeconds" style="margin: 0;">Show Seconds</label>
                    </div>
                </div>

                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="showDate" checked>
                        <label for="showDate" style="margin: 0;">Show Date</label>
                    </div>
                </div>
            </div>

            <!-- Appearance Tab -->
            <div id="tab-appearance" class="tab-content">
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="customColors">
                        <label for="customColors" style="margin: 0;">Use Custom Colors (Override Theme)</label>
                    </div>
                </div>

                <div class="custom-colors-section" id="customColorsSection">
                    <div class="section-title">Colors</div>

                    <div class="form-group">
                        <label>Time Color</label>
                        <div class="color-input">
                            <input type="color" id="timeColor" value="#ffffff">
                            <input type="text" id="timeColorText" class="color-text" value="#ffffff">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Date Color</label>
                        <div class="color-input">
                            <input type="color" id="dateColor" value="#ffffff">
                            <input type="text" id="dateColorText" class="color-text" value="rgba(255, 255, 255, 0.8)">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Background Color 1</label>
                        <div class="color-input">
                            <input type="color" id="backgroundColor1" value="#667eea">
                            <input type="text" id="backgroundColor1Text" class="color-text" value="#667eea">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Background Color 2 (Gradient)</label>
                        <div class="color-input">
                            <input type="color" id="backgroundColor2" value="#764ba2">
                            <input type="text" id="backgroundColor2Text" class="color-text" value="#764ba2">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Clock Background</label>
                        <div class="color-input">
                            <input type="color" id="clockBackground" value="#ffffff">
                            <input type="text" id="clockBackgroundText" class="color-text" value="rgba(255, 255, 255, 0.1)">
                        </div>
                    </div>

                    <div class="section-title">Border</div>

                    <div class="form-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="showBorder">
                            <label for="showBorder" style="margin: 0;">Show Border</label>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Border Color</label>
                        <div class="color-input">
                            <input type="color" id="borderColor" value="#ffffff">
                            <input type="text" id="borderColorText" class="color-text" value="rgba(255, 255, 255, 0.2)">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Border Width: <span class="range-value" id="borderWidthValue">2px</span></label>
                        <div class="range-group">
                            <input type="range" id="borderWidth" min="1" max="10" value="2">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Advanced Tab -->
            <div id="tab-advanced" class="tab-content">
                <div class="section-title">Typography</div>

                <div class="form-group">
                    <label>Font Size: <span class="range-value" id="fontSizeValue">140px</span></label>
                    <div class="range-group">
                        <input type="range" id="fontSize" min="60" max="600" value="140">
                    </div>
                </div>

                <div class="form-group">
                    <label>Font Weight: <span class="range-value" id="fontWeightValue">200</span></label>
                    <div class="range-group">
                        <input type="range" id="fontWeight" min="100" max="900" step="100" value="200">
                    </div>
                </div>

                <div class="form-group">
                    <label>Letter Spacing: <span class="range-value" id="letterSpacingValue">12px</span></label>
                    <div class="range-group">
                        <input type="range" id="letterSpacing" min="0" max="40" value="12">
                    </div>
                </div>

                <div class="form-group">
                    <label for="fontFamily">Font Family</label>
                    <select id="fontFamily">
                        <option value="Segoe UI">Segoe UI</option>
                        <option value="Helvetica Neue">Helvetica Neue</option>
                        <option value="Arial">Arial</option>
                        <option value="Courier New">Courier New</option>
                        <option value="Georgia">Georgia</option>
                        <option value="Times New Roman">Times New Roman</option>
                        <option value="Verdana">Verdana</option>
                    </select>
                </div>

                <div class="section-title">Effects</div>

                <div class="form-group">
                    <label for="shadowIntensity">Shadow Intensity</label>
                    <select id="shadowIntensity">
                        <option value="none">None</option>
                        <option value="light">Light</option>
                        <option value="medium">Medium</option>
                        <option value="strong">Strong</option>
                    </select>
                </div>

                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="glowEnabled">
                        <label for="glowEnabled" style="margin: 0;">Enable Glow Effect</label>
                    </div>
                </div>

                <div class="form-group">
                    <label>Glow Color</label>
                    <div class="color-input">
                        <input type="color" id="glowColor" value="#ffffff">
                        <input type="text" id="glowColorText" class="color-text" value="#ffffff">
                    </div>
                </div>

                <div class="form-group">
                    <label for="glowIntensity">Glow Intensity</label>
                    <select id="glowIntensity">
                        <option value="light">Light</option>
                        <option value="medium">Medium</option>
                        <option value="strong">Strong</option>
                    </select>
                </div>

                <div class="section-title">Layout</div>

                <div class="form-group">
                    <label>Clock Padding: <span class="range-value" id="clockPaddingValue">50px</span></label>
                    <div class="range-group">
                        <input type="range" id="clockPadding" min="20" max="120" value="50">
                    </div>
                </div>

                <div class="form-group">
                    <label>Border Radius: <span class="range-value" id="borderRadiusValue">12px</span></label>
                    <div class="range-group">
                        <input type="range" id="borderRadius" min="0" max="50" value="12">
                    </div>
                </div>

                <div class="form-group">
                    <label>Date Font Size: <span class="range-value" id="dateSizeValue">32px</span></label>
                    <div class="range-group">
                        <input type="range" id="dateSize" min="16" max="72" value="32">
                    </div>
                </div>

                <div class="form-group">
                    <label>Date Spacing: <span class="range-value" id="dateSpacingValue">30px</span></label>
                    <div class="range-group">
                        <input type="range" id="dateSpacing" min="10" max="80" value="30">
                    </div>
                </div>
            </div>

            <div class="button-group">
                <button type="submit" class="btn-primary">💾 Save Settings</button>
                <button type="button" class="btn-secondary" onclick="window.close()">Close</button>
            </div>
        </form>
    </div>

    <script>
        let settings = {};

        // Tab switching
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
        }

        // Load settings
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                const data = await response.json();
                settings = data.settings;
                applySettingsToForm();
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        }

        // Apply settings to form
        function applySettingsToForm() {
            // Basic
            document.getElementById('theme').value = settings.theme || 'minimal';
            document.getElementById('format').value = settings.format || '24hr';
            document.getElementById('animation').value = settings.animation || 'flip';
            document.getElementById('showSeconds').checked = settings.showSeconds !== false;
            document.getElementById('showDate').checked = settings.showDate !== false;

            // Appearance
            document.getElementById('customColors').checked = settings.customColors || false;
            setColorInput('timeColor', settings.timeColor || '#ffffff');
            setColorInput('dateColor', settings.dateColor || 'rgba(255, 255, 255, 0.8)');
            setColorInput('backgroundColor1', settings.backgroundColor1 || '#667eea');
            setColorInput('backgroundColor2', settings.backgroundColor2 || '#764ba2');
            setColorInput('clockBackground', settings.clockBackground || 'rgba(255, 255, 255, 0.1)');
            setColorInput('borderColor', settings.borderColor || 'rgba(255, 255, 255, 0.2)');
            document.getElementById('showBorder').checked = settings.showBorder || false;
            setRangeValue('borderWidth', settings.borderWidth || 2, 'px');

            // Advanced
            setRangeValue('fontSize', settings.fontSize || 140, 'px');
            setRangeValue('fontWeight', settings.fontWeight || '200', '');
            setRangeValue('letterSpacing', settings.letterSpacing || 12, 'px');
            document.getElementById('fontFamily').value = settings.fontFamily || 'Segoe UI';
            document.getElementById('shadowIntensity').value = settings.shadowIntensity || 'medium';
            document.getElementById('glowEnabled').checked = settings.glowEnabled || false;
            setColorInput('glowColor', settings.glowColor || '#ffffff');
            document.getElementById('glowIntensity').value = settings.glowIntensity || 'medium';
            setRangeValue('clockPadding', settings.clockPadding || 50, 'px');
            setRangeValue('borderRadius', settings.borderRadius || 12, 'px');
            setRangeValue('dateSize', settings.dateSize || 32, 'px');
            setRangeValue('dateSpacing', settings.dateSpacing || 30, 'px');

            // Update theme cards
            updateThemeCards();
            toggleCustomColors();
        }

        // Helper to set color inputs
        function setColorInput(id, value) {
            const colorPicker = document.getElementById(id);
            const colorText = document.getElementById(id + 'Text');
            
            // Extract hex color if it's rgba
            if (value.startsWith('rgba') || value.startsWith('rgb')) {
                colorText.value = value;
                // Try to extract hex approximation
                const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                if (match) {
                    const r = parseInt(match[1]).toString(16).padStart(2, '0');
                    const g = parseInt(match[2]).toString(16).padStart(2, '0');
                    const b = parseInt(match[3]).toString(16).padStart(2, '0');
                    colorPicker.value = '#' + r + g + b;
                }
            } else {
                colorPicker.value = value;
                colorText.value = value;
            }
        }

        // Helper to set range values
        function setRangeValue(id, value, unit) {
            const range = document.getElementById(id);
            const display = document.getElementById(id + 'Value');
            range.value = value;
            display.textContent = value + unit;
        }

        // Update theme cards
        function updateThemeCards() {
            document.querySelectorAll('.theme-card').forEach(card => {
                card.classList.remove('selected');
                if (card.dataset.theme === settings.theme) {
                    card.classList.add('selected');
                }
            });
        }

        // Theme card clicks
        document.querySelectorAll('.theme-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.theme-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                document.getElementById('theme').value = card.dataset.theme;
                document.getElementById('customColors').checked = false;
                toggleCustomColors();
            });
        });

        // Color picker sync
        ['timeColor', 'dateColor', 'backgroundColor1', 'backgroundColor2', 'clockBackground', 'borderColor', 'glowColor'].forEach(id => {
            const picker = document.getElementById(id);
            const text = document.getElementById(id + 'Text');
            
            picker.addEventListener('input', () => {
                text.value = picker.value;
            });
            
            text.addEventListener('input', () => {
                if (text.value.startsWith('#') && text.value.length === 7) {
                    picker.value = text.value;
                }
            });
        });

        // Range value updates
        ['fontSize', 'fontWeight', 'letterSpacing', 'borderWidth', 'clockPadding', 'borderRadius', 'dateSize', 'dateSpacing'].forEach(id => {
            const range = document.getElementById(id);
            const display = document.getElementById(id + 'Value');
            const unit = id === 'fontWeight' ? '' : 'px';
            
            range.addEventListener('input', () => {
                display.textContent = range.value + unit;
            });
        });

        // Toggle custom colors section
        document.getElementById('customColors').addEventListener('change', toggleCustomColors);

        function toggleCustomColors() {
            const section = document.getElementById('customColorsSection');
            section.style.display = document.getElementById('customColors').checked ? 'block' : 'none';
        }

        // Save settings
        document.getElementById('settingsForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                theme: document.getElementById('theme').value,
                format: document.getElementById('format').value,
                animation: document.getElementById('animation').value,
                showSeconds: document.getElementById('showSeconds').checked,
                showDate: document.getElementById('showDate').checked,
                
                customColors: document.getElementById('customColors').checked,
                timeColor: document.getElementById('timeColorText').value,
                dateColor: document.getElementById('dateColorText').value,
                backgroundColor1: document.getElementById('backgroundColor1Text').value,
                backgroundColor2: document.getElementById('backgroundColor2Text').value,
                clockBackground: document.getElementById('clockBackgroundText').value,
                borderColor: document.getElementById('borderColorText').value,
                
                fontSize: parseInt(document.getElementById('fontSize').value),
                fontWeight: document.getElementById('fontWeight').value,
                letterSpacing: parseInt(document.getElementById('letterSpacing').value),
                fontFamily: document.getElementById('fontFamily').value,
                
                showBorder: document.getElementById('showBorder').checked,
                borderWidth: parseInt(document.getElementById('borderWidth').value),
                borderRadius: parseInt(document.getElementById('borderRadius').value),
                shadowIntensity: document.getElementById('shadowIntensity').value,
                glowEnabled: document.getElementById('glowEnabled').checked,
                glowColor: document.getElementById('glowColorText').value,
                glowIntensity: document.getElementById('glowIntensity').value,
                
                clockPadding: parseInt(document.getElementById('clockPadding').value),
                dateSize: parseInt(document.getElementById('dateSize').value),
                dateSpacing: parseInt(document.getElementById('dateSpacing').value),
            };

            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData),
                });

                if (response.ok) {
                    const successMsg = document.getElementById('successMessage');
                    successMsg.classList.add('show');
                    setTimeout(() => successMsg.classList.remove('show'), 3000);
                }
            } catch (error) {
                console.error('Error saving settings:', error);
                alert('Failed to save settings');
            }
        });

        // Initialize
        loadSettings();
        toggleCustomColors();
    </script>
</body>
</html>
"""

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve the main clock display"""
    return render_template_string(CLOCK_HTML)

@app.route('/broadcast')
def broadcast():
    """Serve the broadcast-style clock display (second output)"""
    return render_template_string(BROADCAST_CLOCK_HTML)

@app.route('/settings')
def settings_page():
    """Serve the settings page"""
    return render_template_string(SETTINGS_HTML)

@app.route('/api/heartbeat')
def heartbeat():
    """Heartbeat endpoint to verify server is alive"""
    return jsonify({
        'status': 'alive',
        'timestamp': get_ntp_time() if NTP_AVAILABLE else time.time()
    })

@app.route('/api/time')
def get_time():
    """API endpoint that returns current time (NTP-synced if available)"""
    current_time = get_ntp_time() if NTP_AVAILABLE else time.time()
    dt = datetime.datetime.fromtimestamp(current_time)
    
    return jsonify({
        'timestamp': current_time,
        'hour': dt.hour,
        'minute': dt.minute,
        'second': dt.second,
        'year': dt.year,
        'month': dt.month,
        'day': dt.day,
        'weekday': dt.strftime('%A'),
        'month_name': dt.strftime('%B'),
        'ntp_synced': NTP_AVAILABLE,
        'ntp_offset_ms': ntp_offset * 1000 if NTP_AVAILABLE else 0
    })

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings with version"""
    return jsonify({
        'settings': load_settings(),
        'version': settings_version
    })

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    new_settings = request.json
    save_settings(new_settings)
    return jsonify({'success': True, 'version': settings_version})

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("         ULTIMATE PROFESSIONAL DIGITAL CLOCK SERVER")
    print("=" * 70)
    print(f"  Clock display:  http://localhost:{PORT}")
    print(f"  Broadcast clock: http://localhost:{PORT}/broadcast")
    print(f"  Settings page:  http://localhost:{PORT}/settings")
    print(f"  Settings file:  {SETTINGS_FILE}")
    if NTP_AVAILABLE:
        print(f"  NTP server:     {NTP_SERVER}")
        print(f"  NTP offset:     {ntp_offset * 1000:.2f}ms")
    else:
        print(f"  NTP:            Not available (install ntplib)")
    print("=" * 70)
    print("\n  Keyboard Shortcuts:")
    print("    H  - Hide controls")
    print("    T  - Cycle themes")
    print("    D  - Toggle date")
    print("    S  - Toggle seconds")
    print("    ?  - Show help")
    print("\n  Press Ctrl+C to stop the server\n")
    
    # Auto-generate settings file if it doesn't exist
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        print(f"  Created default settings file: {SETTINGS_FILE}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)