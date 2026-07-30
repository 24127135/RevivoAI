export default {
    template: `
        <div :style="{ width: '100%', height: height, overflow: 'hidden', position: 'relative' }" ref="container">
            <div ref="editorNode" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0;"></div>
        </div>
    `,
    props: {
        value: String,
        language: String,
        readonly: Boolean,
        diff_mode: Boolean,
        original_value: String,
        primary_line: Number,
        height: { type: String, default: '600px' }
    },
    mounted() {
        if (window.monaco) {
            this.initEditor();
            return;
        }
        if (!window.__monacoLoadPromise) {
            window.__monacoLoadPromise = new Promise((resolve) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/loader.js';
                script.onload = () => {
                    require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs' } });
                    require(['vs/editor/editor.main'], () => resolve());
                };
                document.head.appendChild(script);
            });
        }
        window.__monacoLoadPromise.then(() => this.initEditor());
    },
    methods: {
        initEditor() {
            const node = this.$refs.editorNode;
            if (!node) return;

            if (this.diff_mode) {
                this._editor = monaco.editor.createDiffEditor(node, {
                    readOnly: this.readonly,
                    theme: 'vs-dark',
                    automaticLayout: false, // FIXED: Prevents infinite layout loop
                    renderSideBySide: true,
                    scrollBeyondLastLine: false
                });

                const originalModel = monaco.editor.createModel(this.original_value || "", this.language || 'python');
                const modifiedModel = monaco.editor.createModel(this.value || "", this.language || 'python');

                this._editor.setModel({
                    original: originalModel,
                    modified: modifiedModel
                });

                this._editor.getModifiedEditor().onDidChangeModelContent(() => {
                    this.$emit('change', this._editor.getModifiedEditor().getValue());
                });
            } else {
                this._editor = monaco.editor.create(node, {
                    value: this.value || "",
                    language: this.language || 'python',
                    readOnly: this.readonly,
                    theme: 'vs-dark',
                    automaticLayout: false, // FIXED: Prevents infinite layout loop
                    scrollBeyondLastLine: false
                });

                this._editor.onDidChangeModelContent(() => {
                    this.$emit('change', this._editor.getValue());
                });
            }

            // FORCE layout passes — fixed-position parents may not have geometry
            // on the first animation frame, so we do a double-rAF plus a
            // setTimeout fallback to cover all browser timing paths.
            const forceLayout = () => { if (this._editor) this._editor.layout(); };
            window.requestAnimationFrame(() => {
                forceLayout();
                window.requestAnimationFrame(forceLayout);
            });
            setTimeout(forceLayout, 150);

            // FIXED: Safe manual resizing that won't lock the thread
            this._resizeObserver = new ResizeObserver((entries) => {
                if (!entries.length) return;
                const rect = entries[0].contentRect;
                const newWidth = Math.round(rect.width);
                const newHeight = Math.round(rect.height);

                if (this._lastWidth !== newWidth || this._lastHeight !== newHeight) {
                    this._lastWidth = newWidth;
                    this._lastHeight = newHeight;
                    window.requestAnimationFrame(() => {
                        if (this._editor) {
                            this._editor.layout();
                        }
                    });
                }
            });
            this._resizeObserver.observe(this.$refs.container);

            this.applyDecorations();
        },
        applyDecorations() {
            if (!this.primary_line || !this._editor) return;

            const targetEditor = this.diff_mode ? this._editor.getModifiedEditor() : this._editor;

            this._decorations = targetEditor.createDecorationsCollection([
                {
                    range: new monaco.Range(this.primary_line, 1, this.primary_line, 1),
                    options: {
                        isWholeLine: true,
                        className: 'monaco-error-primary'
                    }
                }
            ]);
            targetEditor.revealLineInCenter(this.primary_line);
        }
    },
    watch: {
        value(newValue) {
            if (!this._editor) return;
            const safeNew = newValue || "";

            if (this.diff_mode) {
                const model = this._editor.getModel().modified;
                if (model && safeNew !== model.getValue()) {
                    model.setValue(safeNew);
                }
            } else {
                if (safeNew !== this._editor.getValue()) {
                    this._editor.setValue(safeNew);
                }
            }
        }
    },
    beforeUnmount() {
        if (this._resizeObserver) {
            this._resizeObserver.disconnect();
        }
        if (this._editor) {
            const model = this._editor.getModel();
            this._editor.dispose();
            if (model) {
                if (this.diff_mode) {
                    model.original?.dispose();
                    model.modified?.dispose();
                } else {
                    model.dispose?.();
                }
            }
        }
        this._editor = null;
    }
}
