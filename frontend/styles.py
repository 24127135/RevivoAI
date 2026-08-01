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
.q-textarea .q-field__native {{
    border: var(--neo-border) !important;
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    background-color: var(--neo-white) !important;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    color: var(--neo-black) !important;
    padding: 12px !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
}}
.q-textarea .q-field__native:focus {{
    transform: translate(1px, 1px) !important;
    box-shadow: 2px 2px 0px 0px var(--neo-black) !important;
    outline: none !important;
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

/* 
====================================================================
8. WELCOME SCREEN (Use Case 0 — first load, no project imported)
==================================================================== 
*/
.welcome-screen {{
    text-align: center;
    padding: 56px 24px 32px 24px;
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
    font-size: 12rem !important;
    line-height: 0.95 !important;
    color: var(--neo-black) !important;
    text-transform: uppercase !important;
    letter-spacing: -0.02em !important;
    margin-bottom: var(--space-4) !important;
    white-space: nowrap;
}}
.welcome-title-accent {{
    color: var(--neo-black);
}}
.welcome-desc {{
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--neo-black);
    max-width: 900px;
    margin: 0 auto var(--space-2) auto;
    line-height: 1.5;
}}
.welcome-import-card {{
    background: var(--neo-white);
    border: 4px solid var(--neo-black);
    box-shadow: 6px 6px 0px 0px var(--neo-black);
    padding: 24px 16px; /* Reduced footprint */
    text-align: center;
    transition: transform 0.1s, background-color 0.1s, box-shadow 0.1s;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
}}
.welcome-import-title {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif;
    font-weight: 900;
    font-size: 2.5rem; /* Much larger font */
    letter-spacing: 0.01em;
    color: var(--neo-black);
    margin-bottom: 8px;
}}
.welcome-import-desc {{
    font-size: 1.05rem; 
    font-weight: 600; /* Back to normal reading weight */
    color: #444; /* Softer color so it recedes behind the title */
    line-height: 1.45;
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

</style>
"""
