def get_css(pygments_css: str) -> str:
    return f"""
<style>
/* 
====================================================================
THE GLOBAL OVERRIDE (Force Streamlit containers to left-align)
==================================================================== 
*/
div[data-testid="stSidebar"], 
div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
    text-align: left !important;
    align-items: flex-start !important;
    padding-left: 0 !important;
}}

/* Remove default horizontal padding on the sidebar itself */
section[data-testid="stSidebar"] .block-container {{
    padding-left: 1rem !important;
    padding-right: 1rem !important;
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
.stApp {{
    background-color: var(--neo-bg) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.07) 1px, transparent 1.4px);
    background-size: 10px 10px;
    color: var(--neo-black);
    font-family: 'Space Grotesk', 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: 'Archivo Black', 'Space Grotesk', sans-serif !important;
    font-weight: 900 !important;
    text-transform: uppercase !important;
    letter-spacing: -0.01em !important;
}}

.block-container {{ 
    padding-top: 4rem !important; 
    padding-bottom: 2rem !important; 
    max-width: 100% !important; 
    background-color: var(--neo-bg) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.07) 1px, transparent 1.4px);
    background-size: 10px 10px;
}}

[data-testid="stHeader"] {{
    background-color: var(--neo-bg) !important;
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
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important; /* HARD UNBLURRED SHADOW */
    color: var(--neo-black);
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important; /* MONOSPACE LAYER */
}}

.stat-pill {{
    font-size: 0.9rem !important;
    padding: 6px 16px !important;
    border: 3px solid var(--neo-black) !important; /* THICK BORDER */
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important; /* HARD UNBLURRED SHADOW */
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
    box-shadow: 2px 2px 0px 0px var(--neo-black);
    font-weight: 900; 
    font-size: 0.75rem;
    margin-left: 12px;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', Consolas, monospace !important;
}}

.stButton > button {{
    border: 3px solid var(--neo-black) !important; /* THICK BORDER */
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important; /* REDUCED HARD SHADOW */
    font-weight: 900 !important;
    text-transform: uppercase !important;
    color: var(--neo-black) !important;
    background-color: var(--neo-white) !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
}}
.stButton > button:hover {{
    transform: translate(1px, 1px) !important;
    box-shadow: 2px 2px 0px 0px var(--neo-black) !important;
}}
.stButton > button:active {{
    transform: translate(3px, 3px) !important;
    box-shadow: 0px 0px 0px 0px var(--neo-black) !important;
}}
.stButton > button[kind="primary"] {{
    background-color: var(--neo-blue) !important;
    color: var(--neo-black) !important;
}}

/* Action Center — semantic color ONLY when clickable; disabled always wins as grey */
.st-key-action_bar .stButton > button {{
    color: var(--neo-white) !important;
    font-size: 1.05rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.03em !important;
}}
.st-key-action_bar div[class*="st-key-approve__"] button:not(:disabled) {{
    background-color: var(--neo-green) !important;
    color: var(--neo-white) !important;
}}
.st-key-action_bar div[class*="st-key-action_bar_retest__"] button:not(:disabled) {{
    background-color: var(--neo-blue) !important;
    color: var(--neo-white) !important;
}}
.st-key-action_bar div[class*="st-key-reject_btn__"] button:not(:disabled) {{
    background-color: var(--neo-red) !important;
    color: var(--neo-white) !important;
}}
.st-key-action_bar .stButton > button:disabled {{
    background-color: #e0e0e0 !important;
    border-color: #b0b0b0 !important;
    box-shadow: none !important;
    color: #999 !important;
    cursor: not-allowed !important;
}}
/* Reject confirmation button (outside action bar, in the rejection-note section) */
div[class*="st-key-confirm_reject__"] button[kind="primary"] {{
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
.st-key-action_bar {{
    background: var(--neo-bg) !important;
    border: var(--neo-border) !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    position: sticky;
    bottom: 1rem;
    z-index: 999;
    margin-top: var(--space-3);
    margin-bottom: 0 !important;
    padding: var(--space-3) !important;
    overflow: hidden !important;
}}
.st-key-action_bar > div {{
    width: 100% !important;
}}

/* 
====================================================================
4. DIFF VIEWER & TRACEBACK STRUCTURE
==================================================================== 
*/
.diff-scroll {{ max-height: 560px; overflow-y: auto; overflow-x: auto; background: var(--neo-white); }}
table.diff-table {{ width: 100%; border-collapse: collapse; font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', "SF Mono", Consolas, monospace; font-size: 0.85rem; }}
table.diff-table td {{ padding: 2px 8px; white-space: pre; vertical-align: top; border: none; }}
.ln-col {{ width: 42px; color: var(--neo-black); font-weight: bold; text-align: right; user-select: none; background: #e0e0e0; position: sticky; border-right: 2px solid var(--neo-black); }}
.code-col {{ width: 50%; color: var(--neo-black); }}
.filler-cell {{ background: repeating-linear-gradient(135deg, rgba(0,0,0,0.05), rgba(0,0,0,0.05) 6px, transparent 6px, transparent 12px) !important; }}

tr.diff-header-row .header-cell {{ 
    position: sticky; top: 0; background: var(--neo-black); 
    font-weight: 900; font-size: 0.85rem; letter-spacing: 0.05em; 
    color: var(--neo-white); padding: 8px 8px; z-index: 2;
    text-align: center; border-bottom: 2px solid var(--neo-black);
}}
tr.diff-row:hover td.code-col {{ filter: brightness(0.95); }}
.amber-primary {{ background: var(--amber-primary-bg) !important; display: inline-block; width: 100%; box-shadow: inset 0 0 0 2px var(--neo-black); font-weight: bold; }}
.amber-related {{ display: inline-block; width: 100%; box-shadow: inset 0 0 0 2px var(--amber-related-border); }}

{pygments_css}

.trace-frame-row {{ font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', "SF Mono", Consolas, monospace; font-size: 0.85rem; padding: 6px 10px; border: var(--neo-border); background: var(--neo-yellow); color: var(--neo-black); font-weight: bold; margin-bottom: 8px; box-shadow: 3px 3px 0px 0px var(--neo-black); }}
.trace-noise-row {{ color: #555; font-size: 0.8rem; font-style: italic; padding: 2px 8px; }}
.truncation-banner {{ background: var(--neo-yellow); border: var(--neo-border); padding: 16px 24px !important; font-size: 0.95rem; font-weight: 900; margin-bottom: 32px; box-shadow: var(--neo-shadow); }}
.feedback-banner {{ background: var(--neo-white); border: var(--neo-border); padding: 32px !important; margin-bottom: 32px !important; font-size: 0.95rem; font-weight: bold; box-shadow: var(--neo-shadow); }}

/* 
====================================================================
5. MANUAL EDIT MODE OVERRIDES
==================================================================== 
*/
.stTextArea textarea {{
    border: var(--neo-border) !important;
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    background-color: var(--neo-white) !important;
    font-family: 'JetBrainsMono Nerd Font', 'FiraCode Nerd Font', 'Hack Nerd Font', 'Roboto Mono', Consolas, monospace !important;
    color: var(--neo-black) !important;
    padding: 12px !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
}}
.stTextArea textarea:focus {{
    transform: translate(1px, 1px) !important;
    box-shadow: 2px 2px 0px 0px var(--neo-black) !important;
    outline: none !important;
}}
[data-testid="stCodeBlock"] {{
    border: var(--neo-border) !important;
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
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
    box-shadow: 3px 3px 0px 0px var(--neo-black);
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
    box-shadow: 4px 4px 0px 0px var(--neo-black);
    padding: var(--space-1) var(--space-2);
    margin-bottom: var(--space-2);
    width: fit-content;
}}

/* Visual hierarchy: search/filter labels are lower priority than brand & filenames */
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {{
    font-weight: 400 !important;
    font-size: 0.85rem !important;
}}

[data-testid="stSidebar"] .stToggle label p {{
    font-weight: 700 !important;
    font-size: 0.85rem !important;
}}

/* 2. Make the container relative so the button can float over it */
div[class*="st-key-folder_header_"] {{
    position: relative !important;
}}

/* 3. Pull the button's wrapper completely out of the page layout to fix the gap */
div[class*="st-key-folder_header_"] > div:nth-child(2) {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    z-index: 999 !important;
}}

/* 4. Make the button invisible and stretch it */
div[class*="st-key-folder_header_"] div[data-testid="stButton"] button {{
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important; /* Fully invisible */
    cursor: pointer !important;
    background: transparent !important;
    border: none !important;
    margin: 0 !important;
}}

/* 5. Add the hover effect back to the HTML when hovered */
div[class*="st-key-folder_header_"]:hover .sidebar-folder {{
    color: var(--neo-pink);
}}

/* Flatten and Left-Align all standard sidebar buttons (The Files) */
[data-testid="stSidebar"] .stButton > button {{
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

[data-testid="stSidebar"] .stButton > button div,
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {{
    text-align: left !important;
    justify-content: flex-start !important;
    width: 100% !important;
}}

/* Target the tiny folder expansion toggle specifically (Column 1) */
[data-testid="stSidebar"] [data-testid="column"]:first-child .stButton > button {{
    padding-left: 0px !important;
    padding-right: 0px !important;
    font-size: 1em !important;
    color: #777 !important;
    border: none !important; /* No border for the tiny arrow */
}}

/* Hover State (Grey bg, no shadow) */
[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: #efefef !important;
    border-color: transparent !important;
    transform: none !important;
    box-shadow: none !important;
}}

/* 🌟 Active/Selected State (Pink bg, Black Border, Hard Shadow) 🌟 */
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"],
[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {{
    background-color: var(--neo-pink) !important;
    border: 3px solid var(--neo-black) !important; /* The bold black border */
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important; /* The hard shadow */
    transform: translate(-1px, -1px) !important; /* Pops it out */
    color: var(--neo-black) !important;
}}

/* Keep the shadow and border intact when hovering over the active item */
[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover,
[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover {{
    filter: brightness(0.95) !important;
    border: 3px solid var(--neo-black) !important;
    box-shadow: 3px 3px 0px 0px var(--neo-black) !important;
    transform: translate(-1px, -1px) !important;
}}

/* Highlight the entire folder block (Header + Files) */
div[class*="st-key-folder_group_"] {{
    background-color: var(--neo-bg) !important;
    border: 3px solid var(--neo-black) !important; /* Keeps the Neobrutalism theme */
    padding: 0px 8px 22px 8px !important;
    margin-bottom: 10px !important;
}}

/* Decoupled Selection & Toggles Alignment */
[data-testid="stSidebar"] .stToggle {{
    padding-left: 0 !important;
}}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
    gap: 0rem !important;
    align-items: center;
}}
[data-testid="stSidebar"] [data-testid="column"] {{
    min-width: max-content !important; 
    padding: 0 !important;
    display: flex;
    align-items: center;
}}
[data-testid="stSidebar"] .stCheckbox {{
    margin-top: 4px;
    margin-left: 8px;
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
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--neo-black);
    max-width: 640px;
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

/* 
====================================================================
THE SIDEBAR FOLDER OVERLAY TRICK FOR WELCOME CARDS
==================================================================== 
*/
/* 1. Make the container relative so the button can float over it */
div[class*="st-key-welcome_card_"] {{
    position: relative !important;
    cursor: pointer;
}}

/* 2. Expand the button wrapper slightly outward to cover the 4px border and 6px shadow */
div[class*="st-key-welcome_card_"] > div:nth-child(2) {{
    position: absolute !important;
    top: -6px !important;
    left: -6px !important;
    right: -12px !important; /* Reach out over the shadow */
    bottom: -12px !important; /* Reach out over the shadow */
    width: auto !important;
    height: auto !important;
    z-index: 999 !important;
}}

/* Force all intermediate Streamlit divs inside the button to stretch fully */
div[class*="st-key-welcome_card_"] > div:nth-child(2) div {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
}}

/* 3. Make the button itself completely invisible but explicitly absolute-fill */
div[class*="st-key-welcome_card_"] button {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important; 
    cursor: pointer !important;
    background: transparent !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    display: block !important;
}}

/* 4. Hover effect on the wrapper applies styling to the HTML card inside */
div[class*="st-key-welcome_card_"]:hover .welcome-import-card {{
    background-color: var(--neo-blue) !important;
    transform: translate(2px, 2px) !important;
    box-shadow: 4px 4px 0px 0px var(--neo-black) !important;
}}
/* Welcome screen takeover — cleaner, professional background for as long as
   no project has been imported yet (Use Case 0). */
.block-container:has(.welcome-screen) {{
    background-color: var(--neo-yellow) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.16) 1.5px, transparent 1.5px) !important;
    background-size: 14px 14px !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 56px !important;
    min-height: 100vh !important;
}}

/* Belt-and-suspenders: also tint the outer app shell in case viewport height
   exceeds the block-container's own height (prevents a white gap at the bottom). */
.stApp:has(.welcome-screen) {{
    background-color: var(--neo-yellow) !important;
    background-image: radial-gradient(circle, rgba(16,16,16,0.16) 1.5px, transparent 1.5px) !important;
    background-size: 14px 14px !important;
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
</style>
"""