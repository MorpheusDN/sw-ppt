import {build} from 'esbuild';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const directory=path.dirname(fileURLToPath(import.meta.url));
await build({entryPoints:[path.join(directory,'main.jsx')],outfile:path.join(directory,'../web/app.js'),
  bundle:true,minify:true,sourcemap:false,format:'iife',target:['es2020'],jsx:'automatic',
  define:{'process.env.NODE_ENV':'"production"'},legalComments:'linked'});
await fs.copyFile(path.join(directory,'index.html'),path.join(directory,'../web/index.html'));
await fs.copyFile(path.join(directory,'style.css'),path.join(directory,'../web/style.css'));
console.log('Built React + ECharts offline assets into src/web');
