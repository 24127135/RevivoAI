/*
 * json.worker.js  — Monaco JSON Language Web Worker proxy
 * Served from FastAPI at /monaco-workers/json.worker.js
 *
 * Handles JSON schema validation, completion, and hover off the main thread.
 */
self.MonacoEnvironment = { baseUrl: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/' };
importScripts('https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/language/json/jsonWorker.js');
