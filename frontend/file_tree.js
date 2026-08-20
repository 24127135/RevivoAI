const SVG_ICONS = {
    python: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M7.9 1.5C5 1.5 5.2 2.7 5.2 2.7l.01 1.3h2.8v.4H4.1S2.5 4.2 2.5 7.1c0 2.8 1.4 2.7 1.4 2.7h.8v-1.2s-.04-1.4 1.4-1.4h2.8s1.3.02 1.3-1.3V3.1S9.9 1.5 7.9 1.5zm-1.5.9a.5.5 0 1 1 0 1 .5.5 0 0 1 0-1z" fill="#3776AB"/><path d="M8.1 14.5c2.9 0 2.7-1.2 2.7-1.2l-.01-1.3H8v-.4h3.9s1.6.2 1.6-2.7c0-2.8-1.4-2.7-1.4-2.7h-.8v1.2s.04 1.4-1.4 1.4H7.1s-1.3-.02-1.3 1.3v2.8s.3 1.6 2.3 1.6zm1.5-.9a.5.5 0 1 1 0-1 .5.5 0 0 1 0 1z" fill="#FFD43B"/></svg>`,
    c: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 1.5L13.5 4.7v6.6L8 14.5 2.5 11.3V4.7L8 1.5z" fill="#00599C"/><path d="M10.5 6.2c-.5-.6-1.3-1-2.1-1-1.6 0-2.8 1.2-2.8 2.8s1.2 2.8 2.8 2.8c.8 0 1.6-.4 2.1-1" stroke="#FFF" stroke-width="1.3" stroke-linecap="round"/></svg>`,
    cpp: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 1.5L13.5 4.7v6.6L8 14.5 2.5 11.3V4.7L8 1.5z" fill="#659AD2"/><path d="M6.8 6.2c-.4-.5-1-.8-1.6-.8-1.3 0-2.2 1-2.2 2.3s.9 2.3 2.2 2.3c.7 0 1.2-.3 1.6-.8M8.8 7.6v1.8M7.9 8.5h1.8M11.8 7.6v1.8M10.9 8.5h1.8" stroke="#FFF" stroke-width="1.1" stroke-linecap="round"/></svg>`,
    header: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M8 1.5L13.5 4.7v6.6L8 14.5 2.5 11.3V4.7L8 1.5z" fill="#A074C4"/><path d="M5.5 5.5v5M10.5 5.5v5M5.5 8h5" stroke="#FFF" stroke-width="1.3" stroke-linecap="round"/></svg>`,
    r: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><ellipse cx="8" cy="8" rx="6.5" ry="5.5" fill="#276DC3"/><ellipse cx="8" cy="8" rx="4.5" ry="3.5" fill="#FFF"/><path d="M7 6h2.2c.8 0 1.3.4 1.3 1s-.5 1-1.3 1H7v2.5M7 8h2l1.6 2.5" stroke="#276DC3" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    js: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="1.5" width="13" height="13" rx="1.5" fill="#F7DF1E"/><path d="M6 8.5v3.2c0 .8-.5 1.1-1.2.8l-.5-.3M9.5 11.7c.6.4 1.3.6 2 .3.6-.3.8-.9.4-1.4-.4-.5-1.5-.7-2-1.3-.4-.5-.3-1.4.4-1.8.8-.4 1.8-.2 2.3.2" stroke="#000" stroke-width="1.2" stroke-linecap="round"/></svg>`,
    ts: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="1.5" width="13" height="13" rx="1.5" fill="#3178C6"/><path d="M4 6.5h4M6 6.5v5M9.5 11.2c.5.3 1.1.4 1.7.2.5-.2.7-.7.4-1.1-.3-.4-1.2-.6-1.6-1.1-.3-.4-.2-1.1.3-1.5.6-.3 1.5-.2 1.9.2" stroke="#FFF" stroke-width="1.2" stroke-linecap="round"/></svg>`,
    markdown: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="2.5" width="13" height="11" rx="1" stroke="#083FA1" stroke-width="1.2" fill="#EBF3FF"/><path d="M3.5 10.5V6l2 2.3 2-2.3v4.5M10 8.5l1.5-1.8 1.5 1.8M11.5 6.7v3.8" stroke="#083FA1" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    json: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="2" width="12" height="12" rx="1.5" fill="#CB8E00"/><path d="M5.5 5.5c-.7 0-1 .4-1 1v.7c0 .5-.4.8-.8.8.4 0 .8.3.8.8v.7c0 .6.3 1 1 1M10.5 5.5c.7 0 1 .4 1 1v.7c0 .5.4.8.8.8-.4 0-.8.3-.8.8v.7c0 .6-.3 1-1 1" stroke="#FFF" stroke-width="1.2" stroke-linecap="round"/></svg>`,
    yaml: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="2" y="2" width="12" height="12" rx="1.5" fill="#CB3837"/><path d="M4.5 5.5l2 3v2.5M11.5 5.5l-2 3M6.5 8.5h3" stroke="#FFF" stroke-width="1.2" stroke-linecap="round"/></svg>`,
    sql: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><ellipse cx="8" cy="4.5" rx="5.5" ry="2" fill="#E38C00"/><path d="M2.5 4.5v3.5c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2V4.5" stroke="#B36B00" stroke-width="1" fill="#F5A623"/><path d="M2.5 8v3.5c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2V8" stroke="#B36B00" stroke-width="1" fill="#F5A623"/></svg>`,
    shell: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="1.5" y="2" width="13" height="12" rx="1.5" fill="#2E3440"/><path d="M4.5 5.5l2.5 2.5-2.5 2.5M8.5 10.5h3" stroke="#A3BE8C" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    html: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.5 1.5l1 11.5L8 14.5l4.5-1.5 1-11.5H2.5z" fill="#E44D26"/><path d="M8 2.8v10.3l3.5-1.2.8-9.1H8z" fill="#F16529"/><path d="M5.2 5.2h5.6l-.2 2.2H5.4l.2 2.2 2.4.7 2.4-.7.2-1.3" stroke="#FFF" stroke-width="0.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`,
    css: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M2.5 1.5l1 11.5L8 14.5l4.5-1.5 1-11.5H2.5z" fill="#1572B6"/><path d="M8 2.8v10.3l3.5-1.2.8-9.1H8z" fill="#33A9DC"/><path d="M5.2 5.2h5.6l-.4 4.4L8 10.4l-2.4-.8-.1-1.4" stroke="#FFF" stroke-width="0.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`,
    folder_closed: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1.5 3.5a1 1 0 0 1 1-1h3.3l1.5 1.5h6.2a1 1 0 0 1 1 1v7.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-9z" fill="#D99B26"/><path d="M1.5 5.5h13v6.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-6.5z" fill="#E8B839"/></svg>`,
    folder_open: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1.5 3.5a1 1 0 0 1 1-1h3.3l1.5 1.5h6.2a1 1 0 0 1 1 1v2H2.5v-3.5z" fill="#D99B26"/><path d="M1.5 6.5h12l-1.5 6.5h-11L1.5 6.5z" fill="#F0C34B" stroke="#D99B26" stroke-width="0.8"/></svg>`,
    file: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3.5 2.5a1 1 0 0 1 1-1h4.5l4 4v8a1 1 0 0 1-1 1h-7.5a1 1 0 0 1-1-1v-11z" fill="#F4F4F5" stroke="#71717A" stroke-width="1.1"/><path d="M9 1.5v4h4" fill="#E4E4E7" stroke="#71717A" stroke-width="1.1"/></svg>`
};

export default {
    template: `
        <div ref="treeWrapper" class="lazy-file-tree-wrapper" :style="{ width: '100%', height: height, overflowY: 'auto' }">
            <q-tree
                :nodes="formattedNodes"
                node-key="id"
                :tick-strategy="tick_strategy"
                v-model:ticked="ticked"
                v-model:selected="selected"
                v-model:expanded="expanded"
                @lazy-load="onLazyLoad"
                @update:ticked="onUpdateTicked"
                @update:selected="onUpdateSelected"
                @update:expanded="onUpdateExpanded"
                dense
                class="lazy-file-tree font-mono text-sm select-none"
            >
                <template v-slot:default-header="prop">
                    <div 
                        class="row items-center no-wrap tree-node-row q-py-xs w-full pr-1 cursor-pointer"
                        @click="onNodeHeaderClick(prop, $event)"
                    >
                        <span class="tree-icon q-mr-xs flex-shrink-0 flex items-center justify-center w-4 h-4 leading-none" v-html="getNodeSvgIcon(prop.node, prop.expanded)"></span>
                        <span class="tree-label truncate flex-1 text-xs" :class="{ 'font-bold text-black uppercase tracking-tight': prop.node.is_dir, 'text-gray-900 font-semibold': !prop.node.is_dir }">
                            {{ prop.node.label }}
                        </span>
                        <span v-if="prop.node.status_badge" class="tree-status-badge q-ml-xs text-[10px] px-1 rounded font-mono font-bold flex-shrink-0" :class="getStatusBadgeClass(prop.node.status)">
                            {{ prop.node.status_badge }}
                        </span>
                        <span v-else-if="prop.node.badge" class="tree-warn-badge q-ml-xs text-[10px] bg-yellow-300 text-black px-1 border border-black font-bold flex-shrink-0">
                            {{ prop.node.badge }}
                        </span>
                    </div>
                </template>
            </q-tree>
        </div>
    `,
    props: {
        nodes: { type: Array, default: () => [] },
        tick_strategy: { type: String, default: 'none' }, // 'none', 'strict', 'leaf'
        initial_ticked: { type: Array, default: () => [] },
        initial_selected: { type: String, default: null },
        initial_expanded: { type: Array, default: () => [] },
        height: { type: String, default: '300px' }
    },
    data() {
        return {
            treeNodes: this.formatNodeList(this.nodes || []),
            ticked: [...(this.initial_ticked || [])],
            selected: this.initial_selected || null,
            expanded: [...(this.initial_expanded || [])],
            _lazyCallbacks: {},
            _isRestoringScroll: false
        };
    },
    computed: {
        formattedNodes() {
            return this.treeNodes;
        }
    },
    mounted() {
        this.restoreScrollPosition();
        if (this.$refs.treeWrapper) {
            this.$refs.treeWrapper.addEventListener('scroll', this.handleScroll, { passive: true });
        }
    },
    beforeUnmount() {
        if (this.$refs.treeWrapper) {
            this.$refs.treeWrapper.removeEventListener('scroll', this.handleScroll);
        }
    },
    watch: {
        nodes(newVal) {
            this.treeNodes = this.formatNodeList(newVal || []);
            this.$nextTick(() => {
                this.restoreScrollPosition();
            });
        },
        initial_ticked(newVal) {
            this.ticked = [...(newVal || [])];
        },
        initial_selected(newVal) {
            this.selected = newVal;
        },
        initial_expanded(newVal) {
            if (Array.isArray(newVal)) {
                const set = new Set([...this.expanded, ...newVal]);
                this.expanded = Array.from(set);
            }
        }
    },
    methods: {
        formatNodeList(nodeList) {
            if (!Array.isArray(nodeList)) return [];
            return nodeList.map(n => {
                const node = { ...n };
                node.header = 'default';
                if (node.children && Array.isArray(node.children)) {
                    node.children = this.formatNodeList(node.children);
                }
                return node;
            });
        },
        getNodeSvgIcon(node, isExpanded) {
            const isOpen = isExpanded !== undefined ? isExpanded : (this.expanded && this.expanded.includes(node.id));
            if (node.is_dir || node.children || node.lazy) {
                return isOpen ? SVG_ICONS.folder_open : SVG_ICONS.folder_closed;
            }
            const label = node.label || node.path || node.id || '';
            const ext = (node.ext || (label.includes('.') ? label.split('.').pop() : '')).toLowerCase();
            
            const map = {
                py: SVG_ICONS.python,
                c: SVG_ICONS.c,
                h: SVG_ICONS.header,
                cpp: SVG_ICONS.cpp,
                hpp: SVG_ICONS.header,
                r: SVG_ICONS.r,
                rmd: SVG_ICONS.r,
                js: SVG_ICONS.js,
                jsx: SVG_ICONS.js,
                ts: SVG_ICONS.ts,
                tsx: SVG_ICONS.ts,
                json: SVG_ICONS.json,
                yaml: SVG_ICONS.yaml,
                yml: SVG_ICONS.yaml,
                toml: SVG_ICONS.yaml,
                ini: SVG_ICONS.yaml,
                md: SVG_ICONS.markdown,
                txt: SVG_ICONS.file,
                sql: SVG_ICONS.sql,
                sh: SVG_ICONS.shell,
                bat: SVG_ICONS.shell,
                html: SVG_ICONS.html,
                css: SVG_ICONS.css
            };
            return map[ext] || SVG_ICONS.file;
        },
        getStatusBadgeClass(status) {
            const s = String(status || '').toUpperCase();
            if (s.includes('PASSED') || s.includes('APPROVED')) return 'bg-green-100 text-green-800 border border-green-500';
            if (s.includes('FAILED') || s.includes('REJECTED')) return 'bg-red-100 text-red-800 border border-red-500';
            if (s.includes('TRANSLATING') || s.includes('SANDBOX')) return 'bg-blue-100 text-blue-800 border border-blue-500 animate-pulse';
            if (s.includes('EDITED')) return 'bg-yellow-100 text-yellow-800 border border-yellow-500';
            return 'bg-gray-100 text-gray-700 border border-gray-400';
        },
        handleScroll() {
            if (this.$refs.treeWrapper && !this._isRestoringScroll) {
                try {
                    sessionStorage.setItem('revivo_tree_scroll_top', String(this.$refs.treeWrapper.scrollTop));
                } catch (e) {}
            }
        },
        restoreScrollPosition() {
            try {
                const saved = sessionStorage.getItem('revivo_tree_scroll_top');
                if (saved !== null && this.$refs.treeWrapper) {
                    this._isRestoringScroll = true;
                    this.$refs.treeWrapper.scrollTop = parseInt(saved, 10) || 0;
                    setTimeout(() => {
                        if (this.$refs.treeWrapper) {
                            this.$refs.treeWrapper.scrollTop = parseInt(saved, 10) || 0;
                        }
                        this._isRestoringScroll = false;
                    }, 50);
                }
            } catch (e) {}
        },
        onNodeHeaderClick(prop, event) {
            const key = prop.node.id || prop.node.key;
            if (prop.node.is_dir || prop.node.children || prop.node.lazy) {
                const idx = this.expanded.indexOf(key);
                if (idx >= 0) {
                    this.expanded.splice(idx, 1);
                } else {
                    this.expanded.push(key);
                }
                this.$emit('expanded_change', this.expanded);
            } else {
                this.selected = key;
                this.$emit('selected_change', key);
            }
        },
        onLazyLoad({ node, key, done, fail }) {
            this._lazyCallbacks[key] = { done, fail, node };
            this.$emit('lazy_load', {
                key: key,
                path: node.path || key,
                id: node.id || key,
                label: node.label
            });
        },
        resolveLazyLoad(key, children) {
            const cb = this._lazyCallbacks[key];
            if (cb && typeof cb.done === 'function') {
                const formattedChildren = this.formatNodeList(children || []);
                if (!Array.isArray(cb.node.children)) {
                    cb.node.children = [];
                }
                cb.node.children.splice(0, cb.node.children.length, ...formattedChildren);
                cb.node.lazy = false;
                cb.done(formattedChildren);
                delete this._lazyCallbacks[key];
            }
        },
        failLazyLoad(key) {
            const cb = this._lazyCallbacks[key];
            if (cb && typeof cb.fail === 'function') {
                cb.fail();
                delete this._lazyCallbacks[key];
            }
        },
        onUpdateTicked(newTicked) {
            this.ticked = newTicked;
            this.$emit('ticked_change', newTicked);
        },
        onUpdateSelected(newSelected) {
            this.selected = newSelected;
            this.$emit('selected_change', newSelected);
        },
        onUpdateExpanded(newExpanded) {
            this.expanded = newExpanded;
            this.$emit('expanded_change', newExpanded);
        },
        setTicked(tickedArray) {
            this.ticked = Array.isArray(tickedArray) ? [...tickedArray] : [];
            this.$emit('ticked_change', this.ticked);
        },
        setSelected(selectedKey) {
            this.selected = selectedKey;
            this.$emit('selected_change', this.selected);
        },
        setExpanded(expandedArray) {
            this.expanded = Array.isArray(expandedArray) ? [...expandedArray] : [];
            this.$emit('expanded_change', this.expanded);
        },
        collapseAll() {
            this.expanded = [];
            this.$emit('expanded_change', this.expanded);
        },
        expandAll() {
            const allFolders = [];
            const collect = (nodes) => {
                for (const n of nodes) {
                    if (n.is_dir || n.children) {
                        allFolders.push(n.id);
                        if (n.children) collect(n.children);
                    }
                }
            };
            collect(this.formattedNodes);
            this.expanded = allFolders;
            this.$emit('expanded_change', this.expanded);
        }
    }
};
