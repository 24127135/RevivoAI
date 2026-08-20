/**
 * structured_terminal.js
 * -----------------------
 * btop/GoogleTest-inspired log viewer.
 *
 * Row format (pipe-delimited, fixed-width columns):
 *   HH:MM:SS | [SRC] | STAT | message text...
 *
 * Design constraints:
 *   - Pure black background (#000), monospace only, zero rounded corners.
 *   - No emoji, no colored badges/backgrounds, no card shadows.
 *   - Semantic color ONLY on the 4-char status column for scannability.
 *   - q-virtual-scroll for zero DOM bloat on large log sets.
 *
 * Virtual-scroll + dynamic height note:
 *   Quasar's q-virtual-scroll only supports a single fixed item height in
 *   "virtual-scroll-item-size". Collapsed rows = 22px; expanded rows grow
 *   to include a traceback block (variable). This is handled by:
 *     1. Keeping a reactive `expandedIds` Set.
 *     2. Rebuilding a flat `renderItems` array where each expanded entry is
 *        followed by a synthetic {type:'trace', ...} item at a fixed
 *        TRACE_ITEM_SIZE height per visible line capped by MAX_TRACE_LINES.
 *     3. Using the two-item-size approach avoids the "overlap on toggle"
 *        artefact without needing the (Quasar Pro-only) `virtual-scroll-size`
 *        slot. This IS a controlled trade-off: traceback blocks scroll
 *        internally up to MAX_TRACE_LINES visible lines.
 *   Flag: the inner traceback <pre> has overflow-y:auto and a fixed max-height
 *   (MAX_TRACE_LINES * line-height). This keeps the virtual scroll stable at
 *   the cost of a second scrollbar inside expanded rows on very long tracebacks.
 *   Full dynamic-height virtual scroll would require a custom size-provider
 *   callback not exposed by Quasar's OSS build.
 */

const LOG_ROW_H      = 26;   // px — collapsed row height (used by q-virtual-scroll)
const LINE_H         = 18;   // px — traceback line height
const HEADER_H       = 28;   // px — pytest summary row height
const PADDING        = 16;   // px — trace block vertical padding budget
const MIN_TRACE_H    = 60;   // px — keep short tracebacks readable
const MAX_TRACE_H    = 320;  // px — cap before inner <pre> scrolls
const MAX_TRACE_LINES = Math.floor((MAX_TRACE_H - HEADER_H - PADDING) / LINE_H);
const MAX_LOGS       = 1000;  // hard cap on client-side ring buffer

// Status → color class (applied ONLY to the status column)
const STATUS_COLOR = {
    'running': 'st-status--run',
    'success': 'st-status--pass',
    'error':   'st-status--fail',
    'warning': 'st-status--warn',
    'info':    'st-status--info',
};

// Canonical source → display tag (fallback: wrap in brackets)
const SOURCE_TAG = {
    'LLM':  '[LLM ]',
    'DKR':  '[DKR ]',
    'TEST': '[TEST]',
    'TELM': '[TELM]',
    'SYS':  '[SYS ]',
};

function _srcTag(src) {
    const key = (src || 'SYS').toUpperCase();
    // Accept legacy aliases from the ring-buffer (pre-normalization entries)
    const alias = { DOCKER: 'DKR', PYTEST: 'TEST', TELEMETRY: 'TELM', SYSTEM: 'SYS', LLM: 'LLM' };
    const canon = alias[key] || key;
    return SOURCE_TAG[canon] || `[${canon.slice(0, 4).padEnd(4)}]`;
}

function _uid() { return Math.random().toString(36).slice(2, 9); }

function _traceLineCount(text) {
    const trimmed = (text || '').trim();
    if (!trimmed) return 0;
    return trimmed.split(/\r?\n/).length;
}

function _traceHeight(lineCount, hasSummaryHeader) {
    const headerH = hasSummaryHeader ? HEADER_H : 0;
    const visibleLines = Math.min(lineCount, MAX_TRACE_LINES);
    const rawHeight = headerH + PADDING + (visibleLines * LINE_H);
    return Math.max(MIN_TRACE_H, Math.min(MAX_TRACE_H, rawHeight));
}

function _normalize(raw) {
    if (typeof raw === 'string') {
        // Legacy string format: "HH:MM:SS | [SRC] | STAT | msg"  or  "[HH:MM:SS] [SRC] msg"
        let ts = '--:--:--', src = 'SYS', status = 'info', msg = raw;

        // Try pipe format first (new format)
        const pipeM = raw.match(/^(\d{2}:\d{2}:\d{2}) \| (\[.+?\]) \| (\w+)\s*\| (.*)$/s);
        if (pipeM) {
            ts = pipeM[1];
            // extract inner e.g. "DKR" from "[DKR ]"
            src = pipeM[2].replace(/[\[\]\s]/g, '').toUpperCase();
            const sLabel = pipeM[3].trim().toLowerCase();
            const lblMap = { run: 'running', pass: 'success', fail: 'error', warn: 'warning', info: 'info' };
            status = lblMap[sLabel] || sLabel;
            msg = pipeM[4];
        } else {
            // Legacy bracket format: "[HH:MM:SS] [SRC] msg"
            const tsM = raw.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*/);
            if (tsM) { ts = tsM[1]; msg = raw.slice(tsM[0].length); }
            const srcM = msg.match(/^\[([A-Za-z0-9_ ]+)\]\s*/);
            if (srcM) { src = srcM[1].trim().toUpperCase(); msg = msg.slice(srcM[0].length); }
            if (/error|fail|exception|crash/i.test(msg)) status = 'error';
            else if (/warn|refused/i.test(msg)) status = 'warning';
            else if (/pass|success/i.test(msg)) status = 'success';
            else if (/execut|provisi|inject|analyz|start/i.test(msg)) status = 'running';
        }

        return { id: _uid(), type: 'log', timestamp: ts, source: src, source_tag: _srcTag(src),
                 status, status_label: status.slice(0,4).toUpperCase().padEnd(4),
                 message: msg, details: {} };
    }

    const src    = (raw.source || 'SYS').toUpperCase();
    const sLower = (raw.status || 'info').toLowerCase();
    const lblMap = { running: 'RUN ', success: 'PASS', error: 'FAIL', warning: 'WARN', info: 'INFO' };
    return {
        id:           raw.id || _uid(),
        type:         'log',
        timestamp:    raw.timestamp  || '--:--:--',
        source:       src,
        source_tag:   raw.source_tag || _srcTag(src),
        status:       sLower,
        status_label: raw.status_label || lblMap[sLower] || 'INFO',
        message:      raw.message    || '',
        details:      raw.details    || {},
    };
}

export default {
    template: `
<div class="st-root" aria-label="Execution log terminal">

    <!-- ── TOOLBAR ─────────────────────────────────────────────────── -->
    <div class="st-toolbar">
        <div class="st-toolbar-left">
            <span class="st-dot" :class="hasRunning ? 'st-dot--live' : 'st-dot--idle'"></span>
            <span class="st-title">EXEC LOG</span>
            <span class="st-count">{{ filteredItems.length }} / {{ logs.length }}</span>
        </div>

        <div class="st-toolbar-filters">
            <button
                v-for="src in sourceFilters" :key="src.key"
                @click="activeSource = src.key"
                class="st-filter-btn"
                :class="{ 'st-filter-btn--active': activeSource === src.key }"
            >{{ src.label }}</button>
        </div>

        <div class="st-toolbar-right">
            <select v-model="activeLevel" class="st-select">
                <option value="ALL">All</option>
                <option value="FAIL">FAIL only</option>
                <option value="WARN_FAIL">WARN+</option>
            </select>
            <input v-model="searchQuery" placeholder="grep..." class="st-search" spellcheck="false" />
        </div>
    </div>

    <!-- ── COLUMN HEADER ────────────────────────────────────────────── -->
    <div class="st-colheader">
        <span class="st-col-ts">TIME</span>
        <span class="st-sep">|</span>
        <span class="st-col-src">SRC</span>
        <span class="st-sep">|</span>
        <span class="st-col-stat">STAT</span>
        <span class="st-sep">|</span>
        <span class="st-col-msg">MESSAGE</span>
    </div>

    <!-- ── LOG BODY (virtual scroll) ────────────────────────────────── -->
    <q-virtual-scroll
        ref="vscroll"
        :items="renderItems"
        :virtual-scroll-item-size="LOG_ROW_H"
        style="flex:1; min-height:0;"
        v-slot="{ item, index }"
        @virtual-scroll="onVScrolled"
    >
        <!-- Normal log row -->
        <div
            v-if="item.type === 'log'"
            :key="item.id"
            class="st-row"
            :class="getRowClass(item)"
            :style="{ height: LOG_ROW_H + 'px', lineHeight: LOG_ROW_H + 'px' }"
            @click="hasTrace(item) && toggleExpand(item.id)"
        >
            <span class="st-col-ts st-dim">{{ item.timestamp }}</span>
            <span class="st-sep st-dim">|</span>
            <span class="st-col-src st-dim">{{ item.source_tag }}</span>
            <span class="st-sep st-dim">|</span>
            <span class="st-col-stat" :class="getStatusClass(item.status)">{{ item.status_label }}</span>
            <span class="st-sep st-dim">|</span>
            <span class="st-col-msg" :title="item.message">{{ item.message }}</span>
            <button
                v-if="hasTrace(item)"
                type="button"
                class="st-expand-btn"
                :class="{ 'is-expanded': expandedIds.has(item.id) }"
                title="Click to view details"
                :aria-label="expandedIds.has(item.id) ? 'Collapse details' : 'Click to view details'"
                @click.stop="toggleExpand(item.id)"
            >(i)</button>
        </div>

        <!-- Synthetic trace row (immediately follows expanded log row) -->
        <div
            v-else-if="item.type === 'trace'"
            :key="'trace-' + item.id"
            class="st-trace-row"
            :style="{ height: item.height + 'px' }"
        >
            <div class="st-trace-inner">
                <!-- Pytest summary header -->
                <div v-if="item.details.is_test_suite" class="st-trace-header">
                    <span :class="item.details.exit_code === 0 ? 'st-status--pass' : 'st-status--fail'">
                        {{ item.details.exit_code === 0 ? 'RESULT: PASS' : 'RESULT: FAIL (exit ' + item.details.exit_code + ')' }}
                    </span>
                    <span class="st-dim"> | Isolated container</span>
                </div>
                <pre class="st-trace-pre">{{ getTraceText(item) }}</pre>
            </div>
        </div>
    </q-virtual-scroll>

    <!-- ── EMPTY STATE ───────────────────────────────────────────────── -->
    <div v-if="filteredLogs.length === 0" class="st-empty">
        (no logs match current filter)
    </div>

    <!-- ── SCROLL-PAUSED PILL ─────────────────────────────────────────── -->
    <div v-if="!autoScroll && logs.length > 0" class="st-jump">
        <button @click="jumpToBottom" class="st-btn st-btn--jump">scroll paused — click to resume</button>
    </div>

</div>
    `,

    props: {
        initial_logs: { type: Array,  default: () => [] },
        max_logs:     { type: Number, default: MAX_LOGS },
    },
    emits: ['cleared'],

    data() {
        return {
            logs:         [],
            expandedIds:  new Set(),
            activeSource: 'ALL',
            activeLevel:  'ALL',
            searchQuery:  '',
            autoScroll:   true,
            LOG_ROW_H,
            sourceFilters: [
                { key: 'ALL',  label: 'ALL'  },
                { key: 'LLM',  label: 'LLM'  },
                { key: 'DKR',  label: 'DKR'  },
                { key: 'TEST', label: 'TEST' },
                { key: 'TELM', label: 'TELM' },
                { key: 'SYS',  label: 'SYS'  },
            ],
        };
    },

    computed: {
        filteredLogs() {
            const q   = (this.searchQuery || '').trim().toLowerCase();
            const src = this.activeSource;
            const lvl = this.activeLevel;
            return this.logs.filter(log => {
                if (src !== 'ALL') {
                    // match canonical source (may have been normalized)
                    const canon = { DOCKER: 'DKR', PYTEST: 'TEST', TELEMETRY: 'TELM', SYSTEM: 'SYS' };
                    const logSrc = canon[log.source] || log.source;
                    if (logSrc !== src) return false;
                }
                if (lvl === 'FAIL' && log.status !== 'error')   return false;
                if (lvl === 'WARN_FAIL' && log.status !== 'error' && log.status !== 'warning') return false;
                if (q) {
                    const hay = `${log.timestamp} ${log.source_tag} ${log.status_label} ${log.message}`.toLowerCase();
                    if (!hay.includes(q)) return false;
                }
                return true;
            });
        },

        /**
         * Flat render list fed into q-virtual-scroll.
         * Each expanded log is followed immediately by a synthetic {type:'trace'} item.
         * This keeps the virtual-scroll item count accurate so the scroll thumb doesn't jump.
         */
        renderItems() {
            const items = [];
            for (const log of this.filteredLogs) {
                items.push(log);
                if (this.expandedIds.has(log.id) && this.hasTrace(log)) {
                    const traceText = this.getTraceText(log);
                    items.push({
                        type:    'trace',
                        id:      log.id,
                        details: log.details,
                        height:  _traceHeight(_traceLineCount(traceText), !!log.details.is_test_suite),
                    });
                }
            }
            return items;
        },

        filteredItems() { return this.filteredLogs; },

        hasRunning() { return this.logs.some(l => l.status === 'running'); },
    },

    created() {
        if (Array.isArray(this.initial_logs) && this.initial_logs.length) {
            this.logs = this.initial_logs.map(_normalize);
        }
    },

    mounted() {
        this.$nextTick(this._scrollToBottom);
    },

    watch: {
        renderItems() {
            if (this.autoScroll) this.$nextTick(this._scrollToBottom);
        },
    },

    methods: {
        /* ---- Public API (called from Python via run_method) ---------- */
        pushLog(raw) {
            const entry = _normalize(raw);
            this.logs.push(entry);
            if (this.logs.length > this.max_logs) this.logs.shift();
        },
        clearLogs() {
            this.logs = [];
            this.expandedIds = new Set();
            this.$emit('cleared');
        },

        /* ---- Row helpers -------------------------------------------- */
        hasTrace(log) {
            return !!(log.details && (log.details.raw_output || log.details.traceback));
        },

        toggleExpand(id) {
            const next = new Set(this.expandedIds);
            if (next.has(id)) next.delete(id); else next.add(id);
            this.expandedIds = next;
            // Ask q-virtual-scroll to re-measure after the expand; this is
            // the closest the OSS Quasar build exposes without a size provider.
            this.$nextTick(() => {
                if (this.$refs.vscroll && this.$refs.vscroll.refresh) {
                    this.$refs.vscroll.refresh();
                }
            });
        },

        getTraceText(item) {
            return (item.details.raw_output || item.details.traceback || '').trim();
        },

        getRowClass(log) {
            if (log.status === 'error')   return 'st-row--fail';
            if (log.status === 'warning') return 'st-row--warn';
            return '';
        },

        getStatusClass(status) {
            return STATUS_COLOR[status] || 'st-status--info';
        },

        toggleAutoScroll() {
            this.autoScroll = !this.autoScroll;
            if (this.autoScroll) this._scrollToBottom();
        },

        jumpToBottom() {
            this.autoScroll = true;
            this._scrollToBottom();
        },

        // q-virtual-scroll emits this on every scroll event
        onVScrolled({ direction, index }) {
            if (!this.autoScroll) return;
            // If the user scrolled UP, pause auto-scroll
            if (direction === 'decrease') {
                this.autoScroll = false;
            }
        },

        _scrollToBottom() {
            const vs = this.$refs.vscroll;
            if (vs && vs.scrollTo && this.renderItems.length) {
                vs.scrollTo(this.renderItems.length - 1, 'end');
            }
        },
    },
};
