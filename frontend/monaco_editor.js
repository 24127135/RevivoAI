/**
 * monaco_editor.js
 * ----------------
 * Vue 3 component wrapping Monaco Editor.
 *
 * Web Worker Architecture
 * -----------------------
 * Monaco offloads language processing (tokenization, bracket matching, diff
 * computation) to Web Workers. Because browsers require workers to come from
 * the same origin as the page, we cannot point directly to CDN worker URLs.
 *
 * Solution: before the AMD loader is invoked, we set `window.MonacoEnvironment`
 * to redirect worker URLs to our FastAPI static endpoint
 * (`/monaco-workers/<type>.worker.js`). Each proxy script at that URL calls
 * `importScripts()` to fetch the real Monaco worker bundle from the CDN inside
 * the worker scope — which IS permitted by the browser.
 *
 * Worker URL routing:
 *   typescript / javascript  →  /monaco-workers/ts.worker.js
 *   json                     →  /monaco-workers/json.worker.js
 *   css / less / scss        →  /monaco-workers/css.worker.js
 *   everything else          →  /monaco-workers/editor.worker.js  (general)
 *
 * Diff Editor
 * -----------
 * When `diff_mode=True`, Python passes both `value` (modified/AI side) and
 * `original_value` (legacy side). Monaco computes line-level diff natively
 * client-side inside the diff worker — no Python involvement after mount.
 */

const MONACO_CDN   = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs';
const MONACO_LOADER = `${MONACO_CDN}/loader.js`;
// FastAPI serves worker proxies at this base (port 8000)
const WORKERS_BASE  = 'http://localhost:8000/monaco-workers';

/** Inject MonacoEnvironment BEFORE loading editor.main so workers are routed. */
function _installWorkerEnv() {
    if (window.__monacoWorkerEnvInstalled) return;
    window.__monacoWorkerEnvInstalled = true;
    window.MonacoEnvironment = {
        getWorkerUrl(_moduleId, label) {
            if (label === 'typescript' || label === 'javascript') {
                return `${WORKERS_BASE}/ts.worker.js`;
            }
            if (label === 'json') {
                return `${WORKERS_BASE}/json.worker.js`;
            }
            if (label === 'css' || label === 'less' || label === 'scss') {
                return `${WORKERS_BASE}/css.worker.js`;
            }
            // Default: general editor worker (handles Python, C, C++, plaintext, etc.)
            return `${WORKERS_BASE}/editor.worker.js`;
        }
    };
}

/** Singleton promise — only one <script> tag is ever injected. */
function _loadMonaco() {
    if (window.__monacoLoadPromise) return window.__monacoLoadPromise;
    _installWorkerEnv();   // Must be set before AMD loader fires
    window.__monacoLoadPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = MONACO_LOADER;
        script.onerror = () => reject(new Error(`Failed to load Monaco loader from ${MONACO_LOADER}`));
        script.onload = () => {
            require.config({ paths: { vs: MONACO_CDN } });
            require(['vs/editor/editor.main'], resolve, reject);
        };
        document.head.appendChild(script);
    });
    return window.__monacoLoadPromise;
}

export default {
    template: `
        <div :style="{ width: '100%', height: height, overflow: 'hidden', position: 'relative' }" ref="container">
            <div ref="editorNode" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0;"></div>
        </div>
    `,
    props: {
        value:          { type: String,  default: '' },
        language:       { type: String,  default: 'python' },
        readonly:       { type: Boolean, default: false },
        diff_mode:      { type: Boolean, default: false },
        original_value: { type: String,  default: '' },
        primary_line:   { type: Number,  default: 0 },
        height:         { type: String,  default: '600px' },
        debounce_delay: { type: Number,  default: 1000 },
    },
    emits: ['change', 'save'],

    data() {
        return {
            _lastEmittedValue: this.value || '',
        };
    },

    mounted() {
        this._debounceTimer = null;
        this._lastEmittedValue = this.value || '';
        _installWorkerEnv();

        if (window.monaco) {
            this.initEditor();
            return;
        }
        _loadMonaco().then(() => this.initEditor()).catch(err => {
            console.error('[MonacoEditor] Failed to load Monaco:', err);
        });
    },

    methods: {
        getCurrentValue() {
            if (!this._editor) return this._lastEmittedValue;
            if (this.diff_mode) {
                return this._modifiedModel ? this._modifiedModel.getValue() : '';
            }
            return this._editor.getValue ? this._editor.getValue() : '';
        },

        /**
         * Flush pending changes to Python (Canonical state).
         * @param {boolean} isManualSave - Whether triggered explicitly by user save action.
         */
        flushChange(isManualSave = false) {
            if (this._debounceTimer) {
                clearTimeout(this._debounceTimer);
                this._debounceTimer = null;
            }

            const current = this.getCurrentValue();
            if (current !== this._lastEmittedValue || isManualSave) {
                this._lastEmittedValue = current;
                this.$emit('change', current);
                if (isManualSave) {
                    this.$emit('save', current);
                }
            }
        },

        /**
         * Schedule local debounced sync (1000ms delay).
         */
        scheduleDebouncedChange() {
            if (this.readonly) return;
            if (this._debounceTimer) {
                clearTimeout(this._debounceTimer);
            }
            const delay = typeof this.debounce_delay === 'number' ? this.debounce_delay : 1000;
            this._debounceTimer = setTimeout(() => {
                this.flushChange(false);
            }, delay);
        },

        initEditor() {
            const node = this.$refs.editorNode;
            if (!node) return;

            const commonOpts = {
                theme: 'vs-dark',
                automaticLayout: false,
                scrollBeyondLastLine: false,
                minimap: { enabled: false },
                fontSize: 13,
                lineHeight: 20,
            };

            if (this.diff_mode) {
                // -------------------------------------------------------
                // DIFF EDITOR
                // -------------------------------------------------------
                this._editor = monaco.editor.createDiffEditor(node, {
                    ...commonOpts,
                    readOnly: this.readonly,
                    renderSideBySide: true,
                    ignoreTrimWhitespace: false,
                    renderIndicators: true,
                    originalEditable: false,
                });

                this._originalModel = monaco.editor.createModel(
                    this.original_value || '', this.language || 'python'
                );
                this._modifiedModel = monaco.editor.createModel(
                    this.value || '', this.language || 'python'
                );

                this._editor.setModel({
                    original: this._originalModel,
                    modified: this._modifiedModel,
                });

                // Debounced content change listener
                this._modifiedModel.onDidChangeContent(() => {
                    this.scheduleDebouncedChange();
                });

                // Flush on editor blur (Ephemeral -> Canonical)
                const modifiedEditor = this._editor.getModifiedEditor();
                if (modifiedEditor) {
                    modifiedEditor.onDidBlurEditorText(() => {
                        this.flushChange(false);
                    });

                    // Ctrl+S / Cmd+S manual save handler
                    modifiedEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
                        this.flushChange(true);
                    });
                }

            } else {
                // -------------------------------------------------------
                // PLAIN EDITOR
                // -------------------------------------------------------
                this._editor = monaco.editor.create(node, {
                    ...commonOpts,
                    value: this.value || '',
                    language: this.language || 'python',
                    readOnly: this.readonly,
                });

                // Debounced content change listener
                this._editor.onDidChangeModelContent(() => {
                    this.scheduleDebouncedChange();
                });

                // Flush on editor blur
                this._editor.onDidBlurEditorText(() => {
                    this.flushChange(false);
                });

                // Ctrl+S / Cmd+S manual save handler
                this._editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
                    this.flushChange(true);
                });
            }

            // Force layout passes
            const forceLayout = () => { if (this._editor) this._editor.layout(); };
            requestAnimationFrame(() => {
                forceLayout();
                requestAnimationFrame(forceLayout);
            });
            setTimeout(forceLayout, 200);

            // ResizeObserver
            this._resizeObserver = new ResizeObserver(entries => {
                if (!entries.length) return;
                const { width, height } = entries[0].contentRect;
                const w = Math.round(width), h = Math.round(height);
                if (this._lastW !== w || this._lastH !== h) {
                    this._lastW = w; this._lastH = h;
                    requestAnimationFrame(() => { if (this._editor) this._editor.layout(); });
                }
            });
            this._resizeObserver.observe(this.$refs.container);

            this._applyDecorations();
        },

        _applyDecorations() {
            if (!this.primary_line || this.primary_line <= 0 || !this._editor) return;
            const target = this.diff_mode
                ? this._editor.getModifiedEditor()
                : this._editor;
            this._decorations = target.createDecorationsCollection([{
                range: new monaco.Range(this.primary_line, 1, this.primary_line, 1),
                options: { isWholeLine: true, className: 'monaco-error-primary' }
            }]);
            target.revealLineInCenter(this.primary_line);
        },

        // Client-side methods exposed for Python run_method
        flush() {
            this.flushChange(false);
        },
        save() {
            this.flushChange(true);
        },
    },

    watch: {
        /** Update the modified (AI) model content when Python pushes a new canonical value. */
        value(newVal) {
            if (!this._editor) return;
            const safe = newVal || '';
            const current = this.getCurrentValue();
            if (safe !== current) {
                this._lastEmittedValue = safe;
                if (this.diff_mode) {
                    if (this._modifiedModel) this._modifiedModel.setValue(safe);
                } else {
                    this._editor.setValue(safe);
                }
            }
        },

        /** Update the original (legacy) model content when Python changes it. */
        original_value(newVal) {
            if (!this._editor || !this.diff_mode) return;
            const safe = newVal || '';
            if (this._originalModel && safe !== this._originalModel.getValue()) {
                this._originalModel.setValue(safe);
            }
        },

        /** Re-apply decorations when the error line changes (e.g., after retest). */
        primary_line() {
            if (this._decorations) {
                this._decorations.clear();
                this._decorations = null;
            }
            this._applyDecorations();
        },
    },

    beforeUnmount() {
        if (this._debounceTimer) {
            this.flushChange(false);
        }
        if (this._resizeObserver) this._resizeObserver.disconnect();
        if (this._editor) {
            if (this.diff_mode) {
                this._originalModel?.dispose();
                this._modifiedModel?.dispose();
            } else {
                this._editor.getModel()?.dispose();
            }
            this._editor.dispose();
        }
        this._editor = this._originalModel = this._modifiedModel = null;
    },
};
