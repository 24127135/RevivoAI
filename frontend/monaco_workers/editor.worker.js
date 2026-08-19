/*
 * editor.worker.js  — Monaco Editor Web Worker proxy
 * Served from FastAPI at /monaco-workers/editor.worker.js
 *
 * Monaco will spawn this script as a Web Worker when processing general
 * language features (tokenization, folding, bracket matching).
 *
 * The worker imports the actual heavy worker bundle from the CDN using
 * importScripts(), which is allowed inside Worker scope.  This avoids
 * bundling ~2MB of worker code into the app's main thread.
 */
self.MonacoEnvironment = { baseUrl: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/' };
importScripts('https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/base/worker/workerMain.js');
