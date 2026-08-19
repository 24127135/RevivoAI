/*
 * css.worker.js  — Monaco CSS/HTML/TypeScript Language Web Worker proxy
 * Served from FastAPI at /monaco-workers/css.worker.js
 *
 * Handles CSS, LESS, SCSS, HTML, and TypeScript language features off
 * the main thread (used when language is 'typescript' or 'css').
 */
self.MonacoEnvironment = { baseUrl: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/' };
importScripts('https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/language/css/cssWorker.js');
