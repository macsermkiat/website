// Development aid: the meshes of a glb whose bounding boxes cross a box (stall-local metres).
// Usage: node tests/tools/glb-region.mjs <file in public/models> minx miny minz maxx maxy maxz
import fs from 'node:fs';
import * as THREE from 'three';
const [file, ...r] = process.argv.slice(2);
const q = new THREE.Box3(new THREE.Vector3(+r[0], +r[1], +r[2]), new THREE.Vector3(+r[3], +r[4], +r[5]));
const b = fs.readFileSync(`public/models/${file}`); const len = b.readUInt32LE(12); const j = JSON.parse(b.subarray(20, 20 + len).toString('utf8'));
const parent = {}; j.nodes.forEach((n, i) => (n.children || []).forEach((c) => (parent[c] = i)));
const local = (n) => { const m = new THREE.Matrix4(); if (n.matrix) m.fromArray(n.matrix); else m.compose(new THREE.Vector3(...(n.translation || [0, 0, 0])), new THREE.Quaternion(...(n.rotation || [0, 0, 0, 1])), new THREE.Vector3(...(n.scale || [1, 1, 1]))); return m; };
const world = (i) => { let m = local(j.nodes[i]); for (let p = parent[i]; p !== undefined; p = parent[p]) m = local(j.nodes[p]).multiply(m); return m; };
j.nodes.forEach((n, i) => {
  if (n.mesh === undefined) return;
  const box = new THREE.Box3();
  for (const pr of j.meshes[n.mesh].primitives) { const a = j.accessors[pr.attributes.POSITION]; if (!a.min) continue; let mn = a.min, mx = a.max; if (a.normalized) { const s = a.componentType === 5122 ? 32767 : a.componentType === 5120 ? 127 : a.componentType === 5123 ? 65535 : 255; mn = mn.map((v) => v / s); mx = mx.map((v) => v / s); } box.union(new THREE.Box3(new THREE.Vector3(...mn), new THREE.Vector3(...mx)).applyMatrix4(world(i))); }
  if (box.intersectsBox(q)) console.log(n.name, box.min.toArray().map((v) => v.toFixed(2)).join(','), '..', box.max.toArray().map((v) => v.toFixed(2)).join(','));
});
