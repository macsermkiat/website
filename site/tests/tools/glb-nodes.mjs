import fs from 'node:fs';
import * as THREE from 'three';
const rd = (p) => { const b = fs.readFileSync(p); const len = b.readUInt32LE(12); return JSON.parse(b.subarray(20, 20 + len).toString('utf8')); };
for (const file of process.argv.slice(2)) {
  const j = rd(`public/models/${file}`);
  const parent = {};
  j.nodes.forEach((n, i) => (n.children || []).forEach((c) => (parent[c] = i)));
  const local = (n) => { const m = new THREE.Matrix4(); if (n.matrix) m.fromArray(n.matrix); else m.compose(new THREE.Vector3(...(n.translation || [0,0,0])), new THREE.Quaternion(...(n.rotation || [0,0,0,1])), new THREE.Vector3(...(n.scale || [1,1,1]))); return m; };
  const world = (i) => { let m = local(j.nodes[i]); for (let p = parent[i]; p !== undefined; p = parent[p]) m = local(j.nodes[p]).multiply(m); return m; };
  const box = new THREE.Box3();
  const out = [];
  j.nodes.forEach((n, i) => {
    const W = world(i);
    if (n.mesh !== undefined) {
      for (const pr of j.meshes[n.mesh].primitives) { const a = j.accessors[pr.attributes.POSITION]; if (!a.min) continue; let mn = a.min, mx = a.max; if (a.normalized) { const s = a.componentType === 5122 ? 32767 : a.componentType === 5120 ? 127 : a.componentType===5123?65535:255; mn = mn.map(v=>v/s); mx = mx.map(v=>v/s);} const b = new THREE.Box3(new THREE.Vector3(...mn), new THREE.Vector3(...mx)).applyMatrix4(W); box.union(b); }
    }
    if (/^(slot_|cam_|light_|write_|act_sign|path_)/.test(n.name)) { const p = new THREE.Vector3().setFromMatrixPosition(W); out.push(`${n.name}=[${p.toArray().map(v=>v.toFixed(2))}]`); }
  });
  console.log(file, 'box', box.min.toArray().map(v=>v.toFixed(2)), box.max.toArray().map(v=>v.toFixed(2)));
  console.log('  ', out.join(' '));
}
