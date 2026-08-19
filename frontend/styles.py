def get_css() -> str:
    return f"""
<style>
/* 
====================================================================
THE GLOBAL OVERRIDE (Align NiceGUI drawer and layout chrome)
==================================================================== 
*/
.q-drawer {{
    border-right: 3px solid var(--neo-black) !important;
    background-color: white !important;
    overflow: visible !important;
    box-sizing: border-box !important;
}}

.q-drawer--left {{
    width: var(--sidebar-width, 350px) !important;
}}

/* Dynamically align Quasar page container with drawer width */
.q-page-container {{
    padding-left: var(--sidebar-width, 350px) !important;
    transition: padding-left 0.1s ease !important;
    min-width: 0 !important;
    width: 100% !important;
    box-sizing: border-box !important;
}}

/* When drawer is closed / hidden (e.g. welcome screen or staging) */
.q-drawer--left.hidden,
.q-drawer--left[aria-hidden="true"],
.q-drawer--left[style*="display: none"] {{
    display: none !important;
}}

body:has(.q-drawer--left.hidden) .q-page-container,
body:has(.q-drawer--left[aria-hidden="true"]) .q-page-container,
body:has(.q-drawer--left[style*="display: none"]) .q-page-container,
body.drawer-hidden .q-page-container {{
    padding-left: 0 !important;
    --sidebar-width: 0px !important;
}}

/* Sidebar Resizer Handle */
.sidebar-resizer {{
    position: absolute;
    top: 0;
    right: -4px;
    bottom: 0;
    width: 8px;
    cursor: col-resize;
    z-index: 1000;
    background: transparent;
    transition: background 0.15s ease;
    user-select: none;
    -webkit-user-select: none;
}}

.sidebar-resizer::after {{
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 3px;
    height: 40px;
    border-radius: 2px;
    background: var(--neo-black);
    opacity: 0;
    transition: opacity 0.15s ease, height 0.15s ease, background 0.15s ease;
}}

.sidebar-resizer:hover::after,
.sidebar-resizer.is-resizing::after {{
    opacity: 1;
    height: 56px;
    background: var(--neo-pink);
    box-shadow: 0 0 6px var(--neo-pink);
}}

.sidebar-resizer:hover,
.sidebar-resizer.is-resizing {{
    background: rgba(255, 95, 209, 0.25);
}}

body.resizing-sidebar {{
    cursor: col-resize !important;
    user-select: none !important;
    -webkit-user-select: none !important;
}}

body.resizing-sidebar * {{
    cursor: col-resize !important;
    user-select: none !important;
    -webkit-user-select: none !important;
    pointer-events: none !important;
}}

body.resizing-sidebar .sidebar-resizer {{
    pointer-events: auto !important;
}}

/* Override default notification bubble for custom HTML alerts */
.q-notification {{
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}}
.q-notification__message {{
    padding: 0 !important;
}}

/* Folder Header Custom Button */
.folder-header-btn > button {{
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--neo-black) !important;
    font-weight: bold !important;
    font-size: 1.1em !important;
    text-transform: uppercase !important;
    padding: 8px 0 4px 0 !important;
    margin-top: 12px !important;
    text-align: left !important;
    justify-content: flex-start !important;
}}
.folder-header-btn > button:hover {{
    background-color: transparent !important;
    color: var(--neo-pink) !important;
}}


/* 
====================================================================
NEOBRUTALISM DESIGN SYSTEM - BASE VARIABLES
==================================================================== 
*/
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700;900&family=Archivo+Black&display=swap');

:root {{
    --sidebar-width: 350px;
    /* Spacing scale — modular 8px base, used consistently across all components */
    --space-1: 8px;
    --space-2: 16px;
    --space-3: 24px;
    --space-4: 32px;
    --space-6: 48px;

    /* Core Palette — see palette notes below for intended role of each color */
    --neo-bg:       #fdfbf7;
    --neo-black:    #101010;
    --neo-white:    #ffffff;
    --neo-yellow:   #f5c518;   /* brand / primary structural accent (header, brand badge) */
    --neo-blue:     #33ccff;   /* informational state (diff, ready) */
    --neo-pink:     #ff5fd1;   /* interactive / selection — "you are here or acting here" */
    --neo-green:    #00c853;   /* success state only */
    --neo-red:      #ff3333;   /* failure / destructive state only */

    /* Diff Colors */
    --diff-added-bg: rgba(0, 230, 118, 0.3); 
    --diff-removed-bg: rgba(255, 51, 51, 0.3); 
    --amber-primary-bg: var(--neo-yellow);
    --amber-related-border: var(--neo-black);

    /* Geometry & Depth */
    --neo-border: 3px solid var(--neo-black);
    
    /* Stark, unblurred shadows for tactile depth */
    --neo-shadow: 6px 6px 0px 0px var(--neo-black);
    --neo-shadow-hover: 4px 4px 0px 0px var(--neo-black);
    --neo-shadow-active: 0px 0px 0px 0px var(--neo-black);
}}

/* Base App Overrides */
body {{
    background-color: var(--neo-bg) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.07) 1px, transparent 1.4px);
    background-size: 10px 10px;
    color: var(--neo-black);
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Space Grotesk', 'Roboto Mono', Consolas, monospace !important;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif !important;
    font-weight: 900 !important;
    text-transform: uppercase !important;
    letter-spacing: -0.01em !important;
}}

/* 
====================================================================
1. SHARED CARD STYLES & COMPONENTS
==================================================================== 
*/
.neo-card {{
    background: var(--neo-white);
    border: var(--neo-border);
    box-shadow: 6px 6px 0px 0px var(--neo-black) !important;
    margin-bottom: var(--space-4) !important;
    display: flex;
    flex-direction: column;
    overflow: hidden !important;
}}

.neo-card.neo-card-light {{
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    margin-bottom: var(--space-3) !important;
}}

/* Spotlight variant — for the AI "thinking" card (translating / sandbox testing).
   Mirrors the brand badge treatment: halftone-on-yellow + heavier border/shadow,
   since this is the core moment of the product (AI actively working). */
.neo-card.neo-card-spotlight {{
    border: 4px solid var(--neo-black) !important;
    box-shadow: 8px 8px 0px 0px var(--neo-black) !important;
    margin-bottom: var(--space-4) !important;
}}
.neo-card.neo-card-spotlight {{
    background-color: var(--neo-yellow) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.02) 1.6px, transparent 1.8px);
    background-size: 7px 7px;
}}
.neo-card.neo-card-spotlight .neo-card-header {{
    background-color: transparent !important;
}}
.neo-card.neo-card-spotlight .num-badge {{
    background: var(--neo-white) !important;
}}

.neo-card-header.compact-header {{
    padding: 8px 16px !important;
}}
.compact-header .neo-card-title-group {{
    font-size: 1rem !important;
}}
.compact-header .header-desc {{
    font-size: 0.72rem !important;
    margin-top: 2px !important;
    margin-left: 0 !important;
}}
.compact-header .stat-pill {{
    font-size: 0.65rem !important;
    padding: 3px 10px !important;
    margin-left: 8px !important;
}}
.neo-card-header.bleed.compact-header {{
    margin-top: 0 !important;
}}

/* Global padding overrides for specific inline styles embedded in the template */


.neo-card > div[style*="padding:16px"] {{ padding: 32px !important; }}
.neo-card > div[style*="padding:16px 0"] {{ padding: 32px 0 !important; }}

.neo-card-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) !important;
    background: var(--neo-white);
}}

.header-left {{
    display: flex;
    flex-direction: column;
}}

.header-desc {{
    font-size: 1rem;
    font-weight: 400; /* Normal weight for description */
    color: var(--neo-black);
    margin-top: 4px;
    margin-left: 64px; /* Align text under the title (48px badge + 16px margin) */
}}

.neo-card-title-group {{
    display: flex;
    align-items: center;
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif;
    font-weight: 900 !important;
    text-transform: uppercase;
    font-size: 1.6rem !important;
    letter-spacing: 0 !important;
}}

.num-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 48px !important;
    height: 48px !important;
    background: var(--neo-white);
    border: 3px solid var(--neo-black) !important; /* THICK BORDER */
    font-weight: 900;
    font-size: 1.4rem !important;
    margin-right: 16px !important;
    color: var(--neo-black);
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important; /* MONOSPACE LAYER */
}}

.stat-pill {{
    font-size: 0.9rem !important;
    padding: 6px 16px !important;
    border: 3px solid var(--neo-black) !important; /* THICK BORDER */
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    text-transform: uppercase;
    margin-left: 12px !important;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important; /* MONOSPACE LAYER */
}}
.stat-pill.red {{ background: var(--neo-red); color: var(--neo-white); }}
.stat-pill.yellow {{ background: var(--neo-yellow); color: var(--neo-black); }}
.stat-pill.green {{ background: var(--neo-green); color: var(--neo-black); }}
.stat-pill.blue {{ background: var(--neo-blue); color: var(--neo-black); }}

.bleed {{
    margin-left: -1rem;
    margin-right: -1rem;
}}
.neo-card-header.bleed {{ margin-top: -1rem; }}

/* 
====================================================================
2. COMPONENT OVERRIDES & BADGES
==================================================================== 
*/
.summary-strip {{ 
    font-size: 1rem; 
    font-weight: 900;
    color: var(--neo-black); 
    padding: var(--space-3) !important;
    border: var(--neo-border); 
    background-color: var(--neo-white);
    box-shadow: var(--neo-shadow);
    margin-bottom: var(--space-4) !important;
    text-transform: uppercase;
}}

.icon-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    font-size: 0.72rem;
    font-weight: 400;
    color: #777;
    margin-bottom: var(--space-3);
    line-height: 1.4;
}}
.icon-legend span {{
    white-space: nowrap;
}}
.warn-badge {{ 
    background-color: var(--neo-red); 
    color: var(--neo-white); 
    border: 2px solid var(--neo-black);
    padding: 2px 6px;
    font-weight: 900; 
    font-size: 0.75rem;
    margin-left: 12px;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', Consolas, monospace !important;
}}
.q-btn {{
    border: 3px solid var(--neo-black) !important; /* THICK BORDER */
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important; /* REDUCED HARD SHADOW */
    font-weight: 900 !important;
    text-transform: uppercase !important;
    color: var(--neo-black) !important;
    background-color: var(--neo-white) !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
}}
.q-btn:hover {{
    transform: translate(1px, 1px) !important;
    box-shadow: 2px 2px 0px 0px var(--neo-black) !important;
}}
.q-btn:active {{
    transform: translate(3px, 3px) !important;
    box-shadow: 0px 0px 0px 0px var(--neo-black) !important;
}}
.q-btn.bg-primary, .q-btn.bg-info {{
    background-color: var(--neo-blue) !important;
    color: var(--neo-black) !important;
}}
.action-bar-container .q-btn {{
    color: var(--neo-white) !important;
    font-size: 1.05rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.03em !important;
}}
.action-bar-container .bg-positive:not(:disabled) {{
    background-color: var(--neo-green) !important;
    color: var(--neo-white) !important;
}}
.action-bar-container .bg-primary:not(:disabled) {{
    background-color: var(--neo-blue) !important;
    color: var(--neo-white) !important;
}}
.action-bar-container .bg-negative:not(:disabled) {{
    background-color: var(--neo-red) !important;
    color: var(--neo-white) !important;
}}
.action-bar-container .q-btn:disabled {{
    background-color: #e0e0e0 !important;
    border-color: #b0b0b0 !important;
    box-shadow: none !important;
    color: #999 !important;
    cursor: not-allowed !important;
}}
/* Reject confirmation button */
.reject-confirm-btn {{
    background-color: var(--neo-red) !important;
    color: var(--neo-white) !important;
}}

/* 
====================================================================
3. STICKY ACTION BAR & TRACEBACK CONTAINERS
==================================================================== 
*/
.st-key-traceback_box, .st-key-edit_mode_box {{
    background: var(--neo-white);
    border: var(--neo-border);
    box-shadow: var(--neo-shadow);
    margin-bottom: var(--space-4) !important;
    overflow: hidden !important;
}}
.action-bar-container {{
    background: var(--neo-bg) !important;
    border: var(--neo-border) !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    margin-top: var(--space-3);
    padding: var(--space-3) !important;
    overflow: hidden !important;
    border-radius: 8px !important;
}}

/* 
====================================================================
4. TRACEBACK STRUCTURE
==================================================================== 
*/
.trace-frame-row {{ font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', "SF Mono", Consolas, monospace; font-size: 0.85rem; padding: 8px 12px; border-left: 4px solid var(--neo-black); background: rgba(245, 197, 24, 0.35); color: var(--neo-black); font-weight: bold; margin-bottom: 8px; border-radius: 2px; }}
.trace-noise-row {{ color: #555; font-size: 0.8rem; font-style: italic; padding: 2px 8px; }}
.feedback-banner {{ background: var(--neo-white); border: var(--neo-border); padding: 32px !important; margin-bottom: 32px !important; font-size: 0.95rem; font-weight: bold; box-shadow: var(--neo-shadow); }}

/* 
====================================================================
4.1 MONACO EDITOR — ERROR LINE DECORATIONS
==================================================================== 
*/
.monaco-error-primary {{
    background-color: rgba(245, 197, 24, 0.35) !important;
    border-left: 3px solid #f5c518 !important;
}}
.monaco-error-related {{
    background-color: rgba(245, 197, 24, 0.12) !important;
    border-left: 2px solid #f5c518 !important;
}}

/* 
====================================================================
5. MANUAL EDIT MODE OVERRIDES
==================================================================== 
*/
/* Clean input and textarea styling without pink focus frame */
.q-field--outlined .q-field__control:before,
.q-field--outlined .q-field__control:after,
.q-field--focused .q-field__control:before,
.q-field--focused .q-field__control:after {{
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}}

.q-field--outlined .q-field__control {{
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
}}

.q-textarea .q-field__native,
.q-input .q-field__native {{
    border: var(--neo-border) !important;
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    background-color: var(--neo-white) !important;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    color: var(--neo-black) !important;
    padding: 10px 12px !important;
    outline: none !important;
}}

.q-textarea .q-field__native:focus,
.q-input .q-field__native:focus {{
    outline: none !important;
    box-shadow: 4px 4px 0px 0px var(--neo-black) !important;
    border-color: var(--neo-black) !important;
}}

input:focus,
textarea:focus,
select:focus {{
    outline: none !important;
    box-shadow: none !important;
}}
[data-testid="stCodeBlock"] {{
    border: var(--neo-border) !important;
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
}}

.pane-label {{
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    font-size: 0.72rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #555;
    margin-bottom: 8px;
}}


/* 
====================================================================
6. THOUGHT PROCESS INDICATOR
==================================================================== 
*/
@keyframes neo-pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.45; transform: scale(0.85); }}
}}
@keyframes neo-dotflash {{
    0%, 20% {{ opacity: 0.2; }}
    50% {{ opacity: 1; }}
    100% {{ opacity: 0.2; }}
}}

.thinking-pulse-dot {{
    width: 14px; height: 14px;
    background: var(--neo-black);
    border-radius: 50%;
    display: inline-block;
    animation: neo-pulse 1.1s ease-in-out infinite;
    flex-shrink: 0;
    margin-right: 8px;
}}
.thinking-step {{
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace;
    font-size: 0.9rem;
    font-weight: 700;
    padding: 6px 16px;
    display: flex;
    align-items: baseline;
    gap: 10px;
}}
.thinking-step .step-icon {{ width: 18px; flex-shrink: 0; font-weight: 900; }}
.thinking-step.step-done {{ color: #2a2a2a; }}
.thinking-step.step-active {{ font-weight: 900; background: rgba(16, 16, 16, 0.12); border-left: 3px solid var(--neo-black); }}
.thinking-step.step-active .step-icon {{ animation: neo-dotflash 1.4s ease-in-out infinite; }}
.thinking-step.step-pending {{ color: #555; font-weight: 600; }}

.persona-badge {{
    display: inline-block;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    font-size: 0.72rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 3px 10px;
    border: 3px solid var(--neo-black);
    background: var(--neo-white);
    margin-left: 10px;
}}
.usecase-badge {{
    display: inline-block;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    font-size: 0.72rem;
    font-weight: 900;
    padding: 3px 10px;
    border: 3px dotted var(--neo-black);
    margin-left: 6px;
    background: transparent;
}}

/* 
====================================================================
7. SIDEBAR ALIGNMENT & FLAT TREE LAYOUT
==================================================================== 
*/
/* Force clean white background, remove all boxed borders */
section[data-testid="stSidebar"], 
[data-testid="stSidebarHeader"] {{
    background-color: white !important;
    border-right: none !important;
    border-bottom: none !important;
}}

/* Ensure all sidebar elements stick to the left */
[data-testid="stSidebar"] * {{
    text-align: left;
}}

/* 1. Re-add your rich text folder styling */
.sidebar-folder {{
    font-weight: 900;
    font-size: 1.05em;
    color: var(--neo-black);
    text-transform: uppercase;
    letter-spacing: 0.02em;
    display: flex;
    align-items: center;
    padding: 12px 0 4px 0;
    transition: color 0.1s;
}}

/* Sidebar brand badge */
.sidebar-brand {{
    display: inline-flex;
    align-items: center;
    background-color: var(--neo-yellow);
    background-image: radial-gradient(circle, rgba(16,16,16,0.18) 1.6px, transparent 1.8px);
    background-size: 7px 7px;
    color: var(--neo-black);
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif;
    font-weight: 900;
    font-size: 1.5rem;
    letter-spacing: 0.01em;
    border: 3px solid var(--neo-black);
    padding: var(--space-1) var(--space-2);
    margin-bottom: var(--space-2);
    width: fit-content;
}}

/* Visual hierarchy: search/filter labels are lower priority than brand & filenames */
.q-drawer .q-field__native {{
    font-weight: 400 !important;
    font-size: 0.85rem !important;
}}

.q-drawer .q-toggle__label {{
    font-weight: 700 !important;
    font-size: 0.85rem !important;
}}

/* Flatten and Left-Align all standard sidebar buttons (The Files) */
.q-drawer .q-btn {{
    display: flex !important;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    background-color: transparent !important;
    border: 3px solid transparent !important;
    box-shadow: none !important; 
    color: #2a2a2a !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    margin: 4px 0 !important;
    border-radius: 0px !important;
    transition: none !important;
    padding-left: 18px !important;
}}

.q-drawer .q-btn .q-btn__content {{
    justify-content: flex-start !important;
    width: 100% !important;
}}

/* Hover State (Grey bg, no shadow) */
.q-drawer .q-btn:hover {{
    background-color: #efefef !important;
    border-color: transparent !important;
    transform: none !important;
    box-shadow: none !important;
}}

/* 🌟 Active/Selected State (Pink bg, Black Border, Hard Shadow) 🌟 */
.q-drawer .q-btn.bg-primary {{
    background-color: var(--neo-pink) !important;
    border: 3px solid var(--neo-black) !important; /* The bold black border */
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important; /* The hard shadow */
    transform: translate(-1px, -1px) !important; /* Pops it out */
    color: var(--neo-black) !important;
}}

.q-drawer .q-btn.bg-primary:hover {{
    filter: brightness(0.95) !important;
    border: 3px solid var(--neo-black) !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    transform: translate(-1px, -1px) !important;
}}

/* Lazy File Tree in Sidebar */
.q-drawer .lazy-file-tree .q-tree__node-header {{
    border-radius: 0px !important;
    padding: 3px 6px !important;
    margin: 1px 0 !important;
    transition: background-color 0.1s ease !important;
}}

.q-drawer .lazy-file-tree .q-tree__node-header:hover {{
    background-color: #efefef !important;
}}

.q-drawer .lazy-file-tree .q-tree__node--selected > .q-tree__node-header {{
    background-color: var(--neo-pink) !important;
    border: 2px solid var(--neo-black) !important;
    box-shadow: 2px 2px 0px 0px var(--neo-black) !important;
    color: var(--neo-black) !important;
}}

/* 
====================================================================
8. WELCOME SCREEN (Use Case 0 — first load, no project imported)
==================================================================== 
*/
.welcome-screen {{
    text-align: center;
    padding: 32px 24px 16px 24px;
}}
.welcome-kicker {{
    display: inline-block;
    background: var(--neo-black);
    color: var(--neo-white);
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace;
    font-weight: 900;
    font-size: 1.1rem;
    letter-spacing: 0.05em;
    padding: 10px 24px;
    margin-bottom: var(--space-4);
}}
.welcome-title {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif !important;
    font-weight: 900 !important;
    font-size: 8.5rem !important;
    line-height: 0.95 !important;
    color: var(--neo-black) !important;
    text-transform: uppercase !important;
    letter-spacing: -0.02em !important;
    margin-bottom: var(--space-2) !important;
    white-space: nowrap;
}}
.welcome-title-accent {{
    color: var(--neo-black);
}}
.welcome-desc {{
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--neo-black);
    max-width: 900px;
    margin: 0 auto 8px auto;
    line-height: 1.4;
}}
.welcome-import-card {{
    background: var(--neo-white);
    border: 4px solid var(--neo-black);
    box-shadow: 4px 4px 0px 0px var(--neo-black);
    padding: 12px 16px;
    text-align: center;
    transition: transform 0.1s, background-color 0.1s, box-shadow 0.1s;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}
.welcome-import-title {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif;
    font-weight: 900;
    font-size: 1.4rem;
    letter-spacing: 0.01em;
    color: var(--neo-black);
    margin-bottom: 4px;
}}
.welcome-import-desc {{
    font-size: 0.82rem;
    font-weight: 500;
    color: #555;
    line-height: 1.35;
}}
.welcome-import-sub {{
    font-family: 'MonoNerdfont', 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace;
    font-weight: 700; /* Normal bold, not ultra-black */
    font-size: 0.85rem; /* Smaller text */
    letter-spacing: 0.05em;
    color: var(--neo-black);
    margin-bottom: 12px;
    text-transform: uppercase;
}}

/* Welcome screen takeover */
.q-page-container:has(.welcome-screen), body:has(.welcome-screen) {{
    background-color: var(--neo-yellow) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.16) 1.5px, transparent 1.5px) !important;
    background-size: 14px 14px !important;
    padding: 0 !important;
    min-height: 100vh !important;
}}

/* 
9. LANGGRAPH STATE MACHINE TRACKER
*/
.langgraph-tracker {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    background: var(--neo-white);
    border: 3px solid var(--neo-black);
    box-shadow: 6px 6px 0px 0px var(--neo-black);
    margin-bottom: 24px;
    font-family: 'Space Grotesk', sans-serif;
    gap: 12px;
}}
.lg-node {{
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    text-transform: uppercase;
    font-size: 0.95rem;
    padding: 8px 16px;
    border: 3px solid var(--neo-black);
    background: var(--neo-white);
    color: var(--neo-black);
    position: relative;
    z-index: 2;
    flex: 1;
    text-align: center;
}}
.lg-node.active {{
    background: var(--neo-yellow);
    box-shadow: 3px 3px 0px 0px var(--neo-black);
    transform: translate(-1px, -1px);
}}
.lg-node.completed {{
    background: var(--neo-green);
    color: var(--neo-black);
}}
.lg-node.pending {{
    background: #f0f0f0;
    color: #999;
    border-color: #999;
}}
.lg-arrow {{
    width: 24px;
    height: 4px;
    background: var(--neo-black);
    position: relative;
    z-index: 1;
    flex-shrink: 0;
}}
.lg-arrow::after {{
    content: '';
    position: absolute;
    right: -6px;
    top: -5px;
    border-top: 7px solid transparent;
    border-bottom: 7px solid transparent;
    border-left: 8px solid var(--neo-black);
}}
.lg-arrow.pending {{
    background: #999;
}}
.lg-arrow.pending::after {{
    border-left-color: #999;
}}

/* 
10. DOCKER TERMINAL UI
*/
.docker-terminal {{
    background-color: #1e1e1e;
    color: #fdfbf7;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    font-size: 0.9rem;
    padding: 16px;
    border: 3px solid var(--neo-black);
    box-shadow: 6px 6px 0px 0px var(--neo-black);
    margin-top: 16px;
    height: 350px;
    overflow-y: auto;
    line-height: 1.5;
    position: relative;
}}
.docker-terminal .term-line {{
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
}}
.docker-terminal .term-error {{
    color: var(--neo-red);
    font-weight: bold;
}}
.docker-terminal .term-warn {{
    color: var(--neo-yellow);
}}
.docker-terminal .term-info {{
    color: var(--neo-blue);
}}
.docker-terminal .term-success {{
    color: var(--neo-green);
}}

/* 
11. ACTION CENTER PEEK & POP
*/
.action-peek {{
    transform: translateY(calc(100% - 80px));
    transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}}
.action-peek:hover {{
    transform: translateY(-24px);
}}

@keyframes action-float {{
    0% {{ transform: translateY(0px) scale(1); }}
    50% {{ transform: translateY(-6px) scale(1.04); }}
    100% {{ transform: translateY(0px) scale(1); }}
}}
.animate-action-float {{
    animation: action-float 1.2s ease-in-out infinite;
}}


/* Clean Action Pill Buttons */
.action-pill-btn {{
    border: none !important;
    box-shadow: none !important;
    border-radius: 9999px !important;
    text-transform: none !important;
}}
.action-pill-btn:hover {{
    transform: none !important;
    box-shadow: none !important;
}}
.action-pill-btn:active {{
    transform: scale(0.95) !important;
    box-shadow: none !important;
}}

/* DropZone outer wrapper */
.dropzone-wrapper {{
    width: 100%;
    margin-bottom: 20px;
    position: relative;
}}

    padding: 12px 16px;
    text-align: center;
    transition: transform 0.1s, background-color 0.1s, box-shadow 0.1s;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}
.welcome-import-title {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif;
    font-weight: 900;
    font-size: 1.4rem;
    letter-spacing: 0.01em;
    color: var(--neo-black);
    margin-bottom: 4px;
}}
.welcome-import-desc {{
    font-size: 0.82rem;
    font-weight: 500;
    color: #555;
    line-height: 1.35;
}}
.welcome-import-sub {{
    font-family: 'MonoNerdfont', 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace;
    font-weight: 700; /* Normal bold, not ultra-black */
    font-size: 0.85rem; /* Smaller text */
    letter-spacing: 0.05em;
    color: var(--neo-black);
    margin-bottom: 12px;
    text-transform: uppercase;
}}

/* Welcome screen takeover */
.q-page-container:has(.welcome-screen), body:has(.welcome-screen) {{
    background-color: var(--neo-yellow) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.16) 1.5px, transparent 1.5px) !important;
    background-size: 14px 14px !important;
    padding: 0 !important;
    min-height: 100vh !important;
}}

/* 
====================================================================
9. LANGGRAPH STATE MACHINE TRACKER
==================================================================== 
*/
.langgraph-tracker {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    background: var(--neo-white);
    border: 3px solid var(--neo-black);
    box-shadow: 6px 6px 0px 0px var(--neo-black);
    margin-bottom: 24px;
    font-family: 'Space Grotesk', sans-serif;
    gap: 12px;
}}
.lg-node {{
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    text-transform: uppercase;
    font-size: 0.95rem;
    padding: 8px 16px;
    border: 3px solid var(--neo-black);
    background: var(--neo-white);
    color: var(--neo-black);
    position: relative;
    z-index: 2;
    flex: 1;
    text-align: center;
}}
.lg-node.active {{
    background: var(--neo-yellow);
    box-shadow: 3px 3px 0px 0px var(--neo-black);
    transform: translate(-1px, -1px);
}}
.lg-node.completed {{
    background: var(--neo-green);
    color: var(--neo-black);
}}
.lg-node.pending {{
    background: #f0f0f0;
    color: #999;
    border-color: #999;
}}
.lg-arrow {{
    width: 24px;
    height: 4px;
    background: var(--neo-black);
    position: relative;
    z-index: 1;
    flex-shrink: 0;
}}
.lg-arrow::after {{
    content: '';
    position: absolute;
    right: -6px;
    top: -5px;
    border-top: 7px solid transparent;
    border-bottom: 7px solid transparent;
    border-left: 8px solid var(--neo-black);
}}
.lg-arrow.pending {{
    background: #999;
}}
.lg-arrow.pending::after {{
    border-left-color: #999;
}}

/* 
====================================================================
10. DOCKER TERMINAL UI
==================================================================== 
*/
.docker-terminal {{
    background-color: #1e1e1e;
    color: #fdfbf7;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    font-size: 0.9rem;
    padding: 16px;
    border: 3px solid var(--neo-black);
    box-shadow: 6px 6px 0px 0px var(--neo-black);
    margin-top: 16px;
    height: 350px;
    overflow-y: auto;
    line-height: 1.5;
    position: relative;
}}
.docker-terminal .term-line {{
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
}}
.docker-terminal .term-error {{
    color: var(--neo-red);
    font-weight: bold;
}}
.docker-terminal .term-warn {{
    color: var(--neo-yellow);
}}
.docker-terminal .term-info {{
    color: var(--neo-blue);
}}
.docker-terminal .term-success {{
    color: var(--neo-green);
}}

/* 
====================================================================
11. ACTION CENTER PEEK & POP
==================================================================== 
*/
.action-peek {{
    transform: translateY(calc(100% - 80px));
    transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}}
.action-peek:hover {{
    transform: translateY(-24px);
}}

@keyframes action-float {{
    0% {{ transform: translateY(0px) scale(1); }}
    50% {{ transform: translateY(-6px) scale(1.04); }}
    100% {{ transform: translateY(0px) scale(1); }}
}}
.animate-action-float {{
    animation: action-float 1.2s ease-in-out infinite;
}}


/* Clean Action Pill Buttons */
.action-pill-btn {{
    border: none !important;
    box-shadow: none !important;
    border-radius: 9999px !important;
    text-transform: none !important;
}}
.action-pill-btn:hover {{
    transform: none !important;
    box-shadow: none !important;
}}
.action-pill-btn:active {{
    transform: scale(0.95) !important;
    box-shadow: none !important;
}}

/* DropZone outer wrapper */
.dropzone-wrapper {{
    width: 100%;
    margin-bottom: 20px;
    position: relative;
}}

/* The actual styled drop area */
.dropzone-area {{
    width: 100%;
    border: 3px solid #101010;
    background: #ffffff;
    box-shadow: 5px 5px 0px 0px #101010;
    transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s, background 0.2s;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 36px 24px 28px 24px;
    min-height: 160px;
    position: relative;
    overflow: hidden;
}}


/* dragover state via JS class */
.dropzone-area.dz-dragover {{
    background: #e6f7ff !important;
    border-color: #007bff !important;
    box-shadow: 0 0 0 3px #007bff, 8px 8px 0px 0px #101010 !important;
    transform: scale(1.015) !important;
}}

.dropzone-title {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif;
    font-weight: 900;
    font-size: 1.5rem;
    color: #101010;
    text-transform: uppercase;
    letter-spacing: -0.01em;
    text-align: center;
    margin-bottom: 6px;
    pointer-events: none;
}}

.dropzone-area.dz-dragover .dropzone-title {{
    color: #007bff;
}}

.dropzone-hint {{
    font-family: 'JetBrainsMono Nerd Font', 'Roboto Mono', Consolas, monospace;
    font-size: 0.85rem;
    font-weight: 700;
    color: #444;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    pointer-events: none;
}}

.dropzone-icon {{
    font-size: 3rem;
    margin-bottom: 8px;
    pointer-events: none;
    transition: transform 0.2s;
}}


/* The q-uploader itself — hidden but functional, overlaid on the dropzone */
.dropzone-uploader {{
    position: absolute !important;
    top: 0; left: 0; right: 0; bottom: 0;
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important;
    z-index: 50 !important;
    cursor: pointer !important;
}}
.dropzone-uploader .q-uploader__header, 
.dropzone-uploader .q-uploader__dnd {{
    width: 100% !important;
    height: 100% !important;
    min-height: 160px !important;
}}

/* FILE LIST AREA (below dropzone) */
.dz-file-list-container {{
    width: 100%;
    max-height: 45vh;
    overflow-y: auto;
    border: 2px solid #101010;
    background: #ffffff;
    padding: 0;
}}

/* Invisible drop overlay for file list */
.list-uploader-overlay {{
    pointer-events: none !important;
}}
body.is-dragging .list-uploader-overlay {{
    pointer-events: auto !important;
}}

/* Custom scrollbar for file list */
.dz-file-list-container::-webkit-scrollbar {{
    width: 12px;
}}
.dz-file-list-container::-webkit-scrollbar-track {{
    background: #f1f1f1;
    border-left: 2px solid #101010;
}}
.dz-file-list-container::-webkit-scrollbar-thumb {{
    background: #101010;
    border-left: 2px solid #101010;
}}

.dz-file-list {{
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0;
}}

.dz-file-row {{
    display: grid;
    grid-template-columns: 50px minmax(140px, 220px) 1fr 90px 90px;
    width: 100%;
    align-items: center;
    column-gap: 12px;
    border: none;
    border-bottom: 1px solid #101010;
    background: transparent;
    padding: 12px 16px;
}}
.dz-file-row:last-child {{
    border-bottom: none;
}}

.dz-merged-icon {{
    display: flex;
    align-items: center;
    border: 2px solid #101010;
    background: #f0f0f0;
    width: fit-content;
}}

.dz-file-icon {{
    width: 24px;
    height: 24px;
    border-left: 2px solid #101010;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
}}

.dz-file-name-container {{
    display: flex;
    align-items: baseline;
    gap: 8px;
    overflow: hidden;
}}

.dz-file-name {{
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', Consolas, monospace;
    font-size: 0.9rem;
    font-weight: 700;
    color: #101010;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.dz-file-size {{
    font-family: 'JetBrainsMono Nerd Font', 'Roboto Mono', Consolas, monospace;
    font-size: 0.75rem;
    font-weight: 600;
    color: #777;
    white-space: nowrap;
}}

.dz-file-progress-area {{
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
}}

.dz-file-progress-wrapper {{
    flex: 1;
    height: 12px;
    border: 2px solid #101010;
    background: #e0e0e0;
    display: flex;
}}

.dz-file-progress-bar {{
    height: 100%;
    background: #00c853;
    transition: width 0.3s ease;
}}

.dz-file-progress-bar.failed {{
    background: #ff3333;
}}

.dz-file-progress-bar.uploading {{
    background: #f5c518;
}}

.dz-file-status-icon {{
    width: 24px;
    height: 24px;
    border: none;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 900;
    flex-shrink: 0;
}}

.dz-file-status-icon.done {{
    background: #00c853;
    color: #101010;
}}

.dz-action-btn {{
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    padding: 0 !important;
    border: 2px solid #101010 !important;
    background: #ffffff !important;
    border-radius: 0 !important;
    font-weight: 900 !important;
    font-size: 10px !important;
    box-shadow: 4px 4px 0px 0px #101010 !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
}}

.dz-action-btn:hover:not(:disabled) {{
    transform: translate(2px, 2px) !important;
    box-shadow: 2px 2px 0px 0px #101010 !important;
}}
.dz-action-btn:active:not(:disabled) {{
    transform: translate(4px, 4px) !important;
    box-shadow: 0px 0px 0px 0px #101010 !important;
}}
.dz-action-btn:disabled {{
    opacity: 0.5 !important;
    box-shadow: none !important;
    transform: none !important;
    background: #f0f0f0 !important;
}}

.dz-replace-btn {{
    color: #101010 !important;
}}
.dz-replace-btn:hover:not(:disabled) {{
    background: #f5c518 !important;
    color: #101010 !important;
}}

.dz-remove-btn {{
    color: #ff3333 !important;
}}
.dz-remove-btn:hover:not(:disabled) {{
    background: #ff3333 !important;
    color: #ffffff !important;
}}

.dz-status-badge {{
    border: 2px solid #101010;
    padding: 4px 12px;
    background: #ffffff;
    font-weight: 900;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}}

/* Checkbox (global override if used) */
.dz-checkbox {{
    width: 18px;
    height: 18px;
    border: 2px solid #101010;
    background: #fff;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 12px;
    color: #101010;
}}
.dz-checkbox.checked {{
    background: #00c853;
}}

</style>
<script>
(function() {{
    function initSidebarResizer() {{
        if (window.__sidebarResizerInitialized) return;
        window.__sidebarResizerInitialized = true;

        const STORAGE_KEY = 'revivo_sidebar_width';
        const DEFAULT_WIDTH = 350;
        const MIN_WIDTH = 240;
        const MAX_RATIO = 0.65;

        function getClampedWidth(w) {{
            const maxW = Math.max(MIN_WIDTH, Math.min(800, window.innerWidth * MAX_RATIO));
            return Math.max(MIN_WIDTH, Math.min(w, maxW));
        }}

        function applyWidth(w, save = true) {{
            const clamped = getClampedWidth(w);
            document.documentElement.style.setProperty('--sidebar-width', clamped + 'px');
            
            const drawer = document.querySelector('.q-drawer--left');
            if (drawer) {{
                drawer.style.width = clamped + 'px';
            }}
            
            const pageContainer = document.querySelector('.q-page-container');
            if (pageContainer) {{
                const isClosed = !drawer || drawer.classList.contains('hidden') || drawer.getAttribute('aria-hidden') === 'true' || drawer.style.display === 'none';
                if (!isClosed) {{
                    pageContainer.style.paddingLeft = clamped + 'px';
                }} else {{
                    pageContainer.style.paddingLeft = '0px';
                }}
            }}
            
            if (save) {{
                try {{ localStorage.setItem(STORAGE_KEY, clamped); }} catch (e) {{}}
            }}
            
            window.dispatchEvent(new Event('resize'));
            return clamped;
        }}

        // Restore saved width on initial load
        try {{
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {{
                const parsed = parseInt(saved, 10);
                if (!isNaN(parsed)) {{
                    applyWidth(parsed, false);
                }}
            }}
        }} catch (e) {{}}

        // Drag handlers with window capture
        let isDragging = false;
        let startX = 0;
        let startWidth = DEFAULT_WIDTH;

        document.addEventListener('mousedown', function(e) {{
            const resizer = e.target.closest('.sidebar-resizer');
            if (!resizer) return;
            
            e.preventDefault();
            e.stopPropagation();

            const drawer = document.querySelector('.q-drawer--left');
            if (!drawer) return;

            isDragging = true;
            startX = e.clientX;
            startWidth = drawer.getBoundingClientRect().width || DEFAULT_WIDTH;

            resizer.classList.add('is-resizing');
            document.body.classList.add('resizing-sidebar');

            function onMouseMove(ev) {{
                if (!isDragging) return;
                const deltaX = ev.clientX - startX;
                applyWidth(startWidth + deltaX, false);
            }}

            function onMouseUp(ev) {{
                if (!isDragging) return;
                isDragging = false;
                resizer.classList.remove('is-resizing');
                document.body.classList.remove('resizing-sidebar');
                
                window.removeEventListener('mousemove', onMouseMove);
                window.removeEventListener('mouseup', onMouseUp);

                const finalDelta = ev.clientX - startX;
                applyWidth(startWidth + finalDelta, true);
            }}

            window.addEventListener('mousemove', onMouseMove, {{ passive: false }});
            window.addEventListener('mouseup', onMouseUp, {{ passive: false }});
        }});

        // Double click to reset to default
        document.addEventListener('dblclick', function(e) {{
            const resizer = e.target.closest('.sidebar-resizer');
            if (!resizer) return;
            e.preventDefault();
            applyWidth(DEFAULT_WIDTH, true);
        }});

        // Dynamic mutation observer to re-apply width to new or refreshed drawers
        const observer = new MutationObserver(() => {{
            const drawer = document.querySelector('.q-drawer--left');
            if (drawer) {{
                const currentVar = getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width');
                if (currentVar && currentVar.trim() && drawer.style.width !== currentVar.trim()) {{
                    drawer.style.width = currentVar.trim();
                }}
            }}
        }});
        observer.observe(document.body, {{ childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] }});
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initSidebarResizer);
    }} else {{
        initSidebarResizer();
    }}
}})();
</script>

<style>
/* ====================================================================
   STRUCTURED TERMINAL  —  btop / GoogleTest aesthetic
   Pure ASCII, monospace, pipe-delimited columns, zero decorations.
   ==================================================================== */

/* Font stack — consistent monospace hierarchy */
.st-root,
.st-root * {{
    font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', 'Cascadia Code', monospace !important;
    box-sizing: border-box;
}}

/* Root container */
.st-root {{
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    background: #000;
    color: #e4e4e7;
    font-size: 12px;
    line-height: 1;
    overflow: hidden;
    border: 1px solid #1e1e1e;
    --st-fg: #e4e4e7;
    --st-dim: #71717a;
    --st-run: #61afef;
    --st-pass: #4ade80;
    --st-fail: #f87171;
    --st-warn: #fbbf24;
}}

/* ── Toolbar ─────────────────────────────────────────────────────── */
.st-toolbar {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    background: #0a0a0a;
    border-bottom: 1px solid #1e1e1e;
    flex-shrink: 0;
    flex-wrap: wrap;
    min-height: 36px;
}}

.st-toolbar-left {{
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
}}

.st-toolbar-filters {{
    display: flex;
    align-items: center;
    gap: 3px;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
}}
.st-toolbar-filters::-webkit-scrollbar {{ display: none; }}

.st-toolbar-right {{
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
}}

/* Live/idle indicator dot */
.st-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}}
.st-dot--live  {{ background: #3ddc84; animation: stPulse 1s ease-in-out infinite; }}
.st-dot--idle  {{ background: #404040; }}

@keyframes stPulse {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.3; }}
}}

.st-title {{
    font-weight: 700;
    letter-spacing: 0.1em;
    font-size: 13px;
    color: var(--st-fg);
    text-transform: uppercase;
}}

.st-count {{
    font-size: 13px;
    color: var(--st-dim);
}}

/* Source filter buttons */
.st-filter-btn {{
    background: #050505;
    border: 1px solid #3a3a3a;
    color: var(--st-fg);
    font-size: 13px;
    font-family: inherit;
    padding: 4px 9px;
    cursor: pointer;
    transition: color 0.1s, border-color 0.1s;
    white-space: nowrap;
    border-radius: 0 !important;
}}
.st-filter-btn:hover {{ color: #ffffff; border-color: #5a5a5a; background: #101010; }}
.st-filter-btn--active {{ color: #ffffff; border-color: #808080; background: #151515; }}

/* Level select + search */
.st-select {{
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    color: #808080;
    font-size: 10px;
    font-family: inherit;
    padding: 1px 4px;
    outline: none;
    cursor: pointer;
    border-radius: 0 !important;
}}
.st-select:focus {{ border-color: #484848; }}

.st-search {{
    background: #0a0a0a;
    border: 1px solid #2a2a2a;
    color: #c8c8c8;
    font-size: 11px;
    font-family: inherit;
    padding: 1px 6px;
    width: 100px;
    outline: none;
    border-radius: 0 !important;
    transition: width 0.15s;
}}
.st-search:focus {{ border-color: #484848; width: 140px; }}
.st-search::placeholder {{ color: #3a3a3a; }}

/* Icon buttons */
.st-btn {{
    background: transparent;
    border: 1px solid #2a2a2a;
    color: #505050;
    font-size: 11px;
    font-family: inherit;
    padding: 1px 5px;
    cursor: pointer;
    border-radius: 0 !important;
    transition: color 0.1s, border-color 0.1s;
    line-height: 1.5;
}}
.st-btn:hover {{ color: #a0a0a0; border-color: #484848; }}
.st-btn--active {{ color: #3ddc84; border-color: #3ddc84; }}
.st-btn--jump {{
    background: #111;
    color: #a0a0a0;
    font-size: 10px;
    border-color: #3a3a3a;
}}

/* ── Column header ──────────────────────────────────────────────── */
.st-colheader {{
    display: flex;
    align-items: center;
    padding: 0 10px;
    background: #0a0a0a;
    border-bottom: 1px solid #2a2a2a;
    border-left: 2px solid transparent;
    color: var(--st-dim);
    font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', 'Cascadia Code', monospace !important;
    font-size: 12px;
    line-height: 28px;
    letter-spacing: normal;
    flex-shrink: 0;
    white-space: pre;
    height: 28px;
    box-sizing: border-box;
}}

/* ── Row layout (all rows share the same column grid) ──────────── */
.st-row {{
    display: flex;
    align-items: center;
    padding: 0 10px;
    cursor: default;
    white-space: nowrap;
    overflow: hidden;
    border-left: 2px solid transparent;
    font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', 'Cascadia Code', monospace !important;
    font-size: 12px;
    letter-spacing: normal;
    box-sizing: border-box;
    transition: background 0.05s;
}}
.st-row:hover {{ background: #080808; }}

/* Left-border accent on error/warn rows only */
.st-row--fail {{ border-left-color: #7a1010; }}
.st-row--warn {{ border-left-color: #6a4a00; }}

/* Fixed-width columns using ch (character width) in monospace for 100% exact alignment */
.st-col-ts   {{ width: 8.5ch;  min-width: 8.5ch;  max-width: 8.5ch;  flex-shrink: 0; display: inline-block; white-space: pre; overflow: hidden; }}
.st-col-src  {{ width: 7ch;    min-width: 7ch;    max-width: 7ch;    flex-shrink: 0; display: inline-block; white-space: pre; overflow: hidden; }}
.st-col-stat {{ width: 5ch;    min-width: 5ch;    max-width: 5ch;    flex-shrink: 0; display: inline-block; font-weight: 700; white-space: pre; overflow: hidden; }}
.st-col-msg  {{ flex: 1 1 0%; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

.st-sep {{
    width: 3ch;
    min-width: 3ch;
    max-width: 3ch;
    flex-shrink: 0;
    display: inline-block;
    text-align: center;
    white-space: pre;
    color: var(--st-dim);
    user-select: none;
}}
.st-dim {{ color: var(--st-dim); }}

.st-expand-btn {{
    flex-shrink: 0;
    margin-left: 8px;
    width: 18px;
    height: 18px;
    padding: 0;
    border: 1px solid #3a3a3a;
    border-radius: 50%;
    background: #050505;
    color: var(--st-fg);
    font-size: 10px;
    line-height: 1;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: background 0.1s, border-color 0.1s, color 0.1s;
}}
.st-expand-btn:hover {{
    background: #111;
    border-color: #5a5a5a;
    color: #ffffff;
}}
.st-expand-btn.is-expanded {{
    border-color: #606060;
    background: #111;
}}

/* ── Status column semantic colors (load-bearing, do not remove) ── */
.st-status--run  {{ color: var(--st-run); }}
.st-status--pass {{ color: var(--st-pass); }}
.st-status--fail {{ color: var(--st-fail); font-weight: 700; }}
.st-status--warn {{ color: var(--st-warn); }}
.st-status--info {{ color: var(--st-run); }}

/* ── Expanded traceback block ──────────────────────────────────── */
.st-trace-row {{
    display: flex;
    flex-direction: column;
    background: #000;
    border-left: 2px solid #1e1e1e;
    overflow: hidden;
}}

.st-trace-inner {{
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 4px 8px 4px 72px;   /* indent aligns with message column */
    overflow: hidden;
}}

.st-trace-header {{
    font-size: 11px;
    font-weight: 700;
    margin-bottom: 4px;
    padding-bottom: 3px;
    border-bottom: 1px solid #1a1a1a;
    flex-shrink: 0;
}}

.st-trace-pre {{
    margin: 0;
    padding: 0;
    font-family: inherit !important;
    font-size: 11px;
    color: var(--st-dim);
    flex: 1;
    overflow-y: auto;
    overflow-x: auto;
    white-space: pre;
    scrollbar-width: thin;
    scrollbar-color: #2a2a2a #000;
    line-height: 1.45;
}}
.st-trace-pre::-webkit-scrollbar {{ width: 5px; height: 5px; }}
.st-trace-pre::-webkit-scrollbar-track {{ background: #000; }}
.st-trace-pre::-webkit-scrollbar-thumb {{ background: #2a2a2a; }}

/* ── Empty state ─────────────────────────────────────────────────── */
.st-empty {{
    position: absolute;
    inset: 60px 0 0 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #2a2a2a;
    font-size: 11px;
    pointer-events: none;
    font-style: italic;
}}

/* ── Jump-to-bottom strip ────────────────────────────────────────── */
.st-jump {{
    display: flex;
    justify-content: center;
    padding: 3px;
    background: #060606;
    border-top: 1px solid #1a1a1a;
    flex-shrink: 0;
}}
</style>
"""

