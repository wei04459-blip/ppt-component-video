import {defineConfig} from 'vite';
import plugin from '@motion-canvas/vite-plugin';
const motionCanvas = (plugin as any).default ?? plugin;
export default defineConfig({plugins:[motionCanvas()], server:{host:'127.0.0.1', strictPort:true}});
