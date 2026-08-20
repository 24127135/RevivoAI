/*
 * ts.worker.js  — Monaco TypeScript/JavaScript Language Web Worker proxy
 * Served from FastAPI at /monaco-workers/ts.worker.js
 *
 * Handles TypeScript and JavaScript IntelliSense, type checking, and
 * formatting off the main thread.
 */
self.MonacoEnvironment = { baseUrl: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/' };
importScripts('https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/language/typescript/tsWorker.js');
