/* Shared candy battlefield: ground-space simulation, screen-space drawing. No game balance or UI state. */
(() => {
'use strict';
const TAU = Math.PI * 2, lerp = (a, b, t) => a + (b - a) * t, clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const INK = '#8a5a3c';
const TEAM = {
  player: { main: '#5aa9f0', dark: '#2f72bd', light: '#bfe0ff' },
  enemy:  { main: '#f27384', dark: '#c4485e', light: '#ffd1d8' }
};
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, Math.max(0, Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2))); }
function circle(g, x, y, r) { g.beginPath(); g.arc(x, y, Math.max(0, r), 0, TAU); }

class Path {
  constructor(pts) {
    this.pts = pts; this.cum = [0];
    for (let i = 1; i < pts.length; i++) this.cum.push(this.cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
    this.length = this.cum[this.cum.length - 1];
  }
  at(t) {
    const d = clamp(t, 0, 1) * this.length; let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (this.cum[mid] <= d) lo = mid; else hi = mid; }
    const seg = this.cum[hi] - this.cum[lo] || 1, q = (d - this.cum[lo]) / seg, a = this.pts[lo], b = this.pts[hi];
    return { x: lerp(a.x, b.x, q), y: lerp(a.y, b.y, q) };
  }
  angle(t) { const a = this.at(t - .004), b = this.at(t + .004); return Math.atan2(b.y - a.y, b.x - a.x); }
  nearest(x, y) { let best = { d: Infinity, t: 0 }; for (let i = 0; i <= 200; i++) { const t = i / 200, p = this.at(t), d = Math.hypot(p.x - x, p.y - y); if (d < best.d) best = { d, t }; } return best; }
  trace(g) { g.beginPath(); g.moveTo(this.pts[0].x, this.pts[0].y); for (let i = 1; i < this.pts.length; i++) g.lineTo(this.pts[i].x, this.pts[i].y); }
}
function bez(out, p0, p1, p2, p3, n) {
  for (let i = 1; i <= n; i++) {
    const t = i / n, m = 1 - t;
    out.push({ x: m*m*m*p0.x + 3*m*m*t*p1.x + 3*m*t*t*p2.x + t*t*t*p3.x, y: m*m*m*p0.y + 3*m*m*t*p1.y + 3*m*t*t*p2.y + t*t*t*p3.y });
  }
}

/* ---------- 几何：全部由舞台宽高推导，战场随比例拉伸 ---------- */
function buildGeometry(w, h, mode = 'cross', unit = null) {
  const u = unit || Math.max(4.4, Math.min(h / 65, w * .0097));
  const top = 7.4 * u, bottom = h - 14 * u, band = bottom - top, cy = (top + bottom) / 2;
  const s = Math.min(band * .3, w * .16);          // 车道间距
  const rw = s * .4;                                // 建筑与单位尺度基准
  const road = rw * .7;                             // 路面宽
  const S0 = rw / 50;                               // 线宽/细节基准
  const T = rw * 1.2;                               // 城墙厚度
  const m = Math.max(w * .016, rw * .25);           // 城墙到舞台边缘
  const x1L = m + T, x1R = w - m - T;               // 城墙内侧面
  const rs = x1L + rw * .62, re = x1R - rw * .62;   // 出生平台中心 = 路径起点
  const L = re - rs, cx = w / 2, ys = [cy - s, cy, cy + s];
  const lead = L * .1, hx = L * .15, slope = 1.45 * s / (L / 2 - lead);
  const cross = (y0, y1) => {
    const dir = Math.sign(y1 - y0), pts = [{ x: rs, y: y0 }, { x: rs + lead, y: y0 }];
    bez(pts, { x: rs + lead, y: y0 }, { x: rs + lead + L * .14, y: y0 }, { x: cx - hx, y: cy - dir * hx * slope }, { x: cx, y: cy }, 28);
    bez(pts, { x: cx, y: cy }, { x: cx + hx, y: cy + dir * hx * slope }, { x: re - lead - L * .14, y: y1 }, { x: re - lead, y: y1 }, 28);
    pts.push({ x: re, y: y1 }); return new Path(pts);
  };
  const mid = []; for (let i = 0; i <= 12; i++) mid.push({ x: lerp(rs, re, i / 12), y: cy });
  const paths = mode === 'straight' ? ys.map(y => new Path([{x:rs,y}, {x:re,y}])) : [cross(ys[0], ys[2]), new Path(mid), cross(ys[2], ys[0])];
  return {
    w, h, u, mode, top, bottom, cy, cx, s, rw, road, S0, T, m, x1L, x1R, rs, re, L, ys, paths,
    wy0: ys[0] - rw * 1.05, wy1: ys[2] + rw * 1.05,
    unitR: rw * .3,
    k: L / 1070,                                    // 原版道路长 1070 px → 当前像素的换算系数
    pivot: { player: { x: m + T * .56, y: ys[1] - T * .98 }, enemy: { x: w - m - T * .56, y: ys[1] - T * .98 } }
  };
}

/* ---------- 静态底图：草地 + 道路 + 平台 + 花丛（缓存为离屏画布） ---------- */
function farFromRoads(F, x, y, gap) {
  for (const p of F.paths) if (p.nearest(x, y).d < F.road / 2 + gap) return false;
  return x > F.x1L + F.rw * .9 && x < F.x1R - F.rw * .9;
}
function drawBlades(g, x, y, len, S0, color, rnd) {
  g.strokeStyle = color; g.lineWidth = Math.max(.8, 1.25 * S0); g.lineCap = 'round';
  for (let i = -1; i <= 1; i++) {
    const lean = (rnd() - .5) * .7 + i * .35, l = len * (.75 + rnd() * .45);
    g.beginPath(); g.moveTo(x + i * 1.6 * S0, y);
    g.quadraticCurveTo(x + i * 1.6 * S0 + lean * l * .3, y - l * .6, x + i * 1.6 * S0 + lean * l, y - l); g.stroke();
  }
}
function drawFlower(g, x, y, r, petal, rnd) {
  g.fillStyle = petal;
  for (let i = 0; i < 5; i++) { const a = i * TAU / 5 + rnd(); circle(g, x + Math.cos(a) * r, y + Math.sin(a) * r, r * .78); g.fill(); }
  g.fillStyle = '#ffd65c'; circle(g, x, y, r * .62); g.fill();
}
const CANDY = ['#ff8fb1', '#ffd65c', '#8fe0a6', '#7cc8ff', '#c9a2ff', '#ffb27a'];
function lolly(g, x, y, r, col, S0, stick) {
  if (stick) {
    g.fillStyle = 'rgba(52,96,44,.22)'; g.beginPath(); g.ellipse(x + r * .15, y + r * .1, r * .55, r * .2, 0, 0, TAU); g.fill();
    g.fillStyle = '#fff7ec'; g.strokeStyle = 'rgba(91,68,97,.45)'; g.lineWidth = Math.max(1, 1.4 * S0);
    rr(g, x - r * .08, y - stick, r * .16, stick, r * .08); g.fill(); g.stroke();
    y -= stick;
  }
  circle(g, x, y, r); g.fillStyle = '#fff'; g.fill(); g.strokeStyle = INK; g.lineWidth = Math.max(1.2, 2 * S0); g.stroke();
  g.strokeStyle = col; g.lineWidth = r * .26; g.lineCap = 'round'; g.beginPath();
  for (let a = 0; a < TAU * 2.1; a += .18) { const d = r * .08 + a * r * .066; g.lineTo(x + Math.cos(a) * d, y + Math.sin(a) * d); } g.stroke();
  g.fillStyle = 'rgba(255,255,255,.75)'; g.beginPath(); g.ellipse(x - r * .38, y - r * .42, r * .2, r * .12, -.6, 0, TAU); g.fill();
}
function drawBush(g, x, y, r, rnd, S0) {
  if (rnd() < .36) { lolly(g, x, y, r * .62, CANDY[Math.floor(rnd() * CANDY.length)], S0, r * 1.3); return; }
  g.fillStyle = 'rgba(52,96,44,.22)'; g.beginPath(); g.ellipse(x + r * .15, y + r * .25, r * 1.2, r * .42, 0, 0, TAU); g.fill();
  const drops = [];
  for (let i = 0; i < 4; i++) drops.push({ x: x + (rnd() - .5) * r * 1.5, y: y + (rnd() - .5) * r * .5, r: r * (.38 + rnd() * .2), c: CANDY[Math.floor(rnd() * CANDY.length)] });
  drops.sort((a, b) => a.y - b.y);
  for (const d of drops) {
    g.beginPath(); g.moveTo(d.x - d.r, d.y);
    g.quadraticCurveTo(d.x - d.r, d.y - d.r * 1.3, d.x, d.y - d.r * 1.3); g.quadraticCurveTo(d.x + d.r, d.y - d.r * 1.3, d.x + d.r, d.y);
    g.ellipse(d.x, d.y, d.r, d.r * .32, 0, 0, Math.PI); g.closePath();
    g.fillStyle = d.c; g.fill(); g.strokeStyle = INK; g.lineWidth = Math.max(1, 1.6 * S0); g.stroke();
    g.fillStyle = 'rgba(255,255,255,.6)'; g.beginPath(); g.ellipse(d.x - d.r * .35, d.y - d.r * .75, d.r * .2, d.r * .12, -.5, 0, TAU); g.fill();
    g.fillStyle = 'rgba(255,255,255,.85)';
    for (let k = 0; k < 4; k++) { circle(g, d.x + (rnd() - .5) * d.r * 1.2, d.y - d.r * (.2 + rnd() * .8), Math.max(.8, d.r * .05)); g.fill(); }
  }
}
function roadLayers(F) {
  const { road, S0 } = F;
  return [
    { w: road + 10 * S0, c: 'rgba(78,134,58,.42)' },   // 草地压边：清楚的绿色描边
    { w: road + 4 * S0, c: '#dcb677' },                 // 沙土外沿
    { w: road, c: '#f4dea4' }                           // 路面
  ];
}
// 道路蒙版：先按宽度画出三条路，再模糊后取阈值。凹角（分岔、交汇处）会被填成圆弧，直边基本不动。
function erf(x) { const t = 1 / (1 + .3275911 * x); return 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - .284496736) * t + .254829592) * t * Math.exp(-x * x); }
function roadMask(F, width, color, dpr) {
  const W = Math.round(F.w * dpr), H = Math.round(F.h * dpr);
  const a = document.createElement('canvas'); a.width = W; a.height = H;
  const ga = a.getContext('2d'); ga.setTransform(dpr, 0, 0, dpr, 0, 0);
  ga.strokeStyle = ga.fillStyle = '#fff'; ga.lineWidth = width; ga.lineCap = 'round'; ga.lineJoin = 'round';
  for (const p of F.paths) { p.trace(ga); ga.stroke(); }
  if (F.mode === 'cross') {
    ga.beginPath(); ga.ellipse(F.cx, F.cy, F.road * 1.6 + (width-F.road)/2, F.road * 1.1 + (width-F.road)/2, 0, 0, TAU); ga.fill();
  }
  const b = document.createElement('canvas'); b.width = W; b.height = H;
  const gb = b.getContext('2d', { willReadFrequently: true });
  const sigma = F.road * .8, edge = .5 * erf(width / (sigma * Math.SQRT2)) * 255, lo = edge - 3, hi = edge + 3;
  gb.filter = `blur(${(sigma * dpr).toFixed(1)}px)`; gb.drawImage(a, 0, 0); gb.filter = 'none';
  const img = gb.getImageData(0, 0, W, H), d = img.data;
  for (let i = 3; i < d.length; i += 4) { const v = d[i]; d[i] = v <= lo ? 0 : v >= hi ? 255 : (v - lo) / (hi - lo) * 255; d[i - 3] = d[i - 2] = d[i - 1] = 255; }
  gb.putImageData(img, 0, 0);
  gb.globalCompositeOperation = 'source-in'; gb.fillStyle = color; gb.fillRect(0, 0, W, H);
  return b;
}
function drawRoads(g, F, rnd) {
  const { road: rw, S0, cx, cy } = F, dpr = g.getTransform().a;
  g.save(); g.lineCap = 'round'; g.lineJoin = 'round';
  { const lip = roadMask(F, F.road + 8 * S0, 'rgba(120,88,48,.20)', dpr); g.save(); g.setTransform(1, 0, 0, 1, Math.round(3 * S0 * dpr), Math.round(4 * S0 * dpr)); g.drawImage(lip, 0, 0); g.restore(); }
  for (const layer of roadLayers(F)) {
    const m = roadMask(F, layer.w, layer.c, dpr);
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(m, 0, 0); g.restore();
  }
  if (F.mode === 'cross') {
  // 广场花砖
  g.strokeStyle = 'rgba(214,170,98,.55)'; g.lineWidth = Math.max(1, 1.6 * S0);
  circle(g, cx, cy, rw * .5); g.stroke();
  g.fillStyle = 'rgba(255,214,226,.8)';
  for (let i = 0; i < 6; i++) { const a = i * TAU / 6; g.beginPath(); g.ellipse(cx + Math.cos(a) * rw * .2, cy + Math.sin(a) * rw * .2, rw * .12, rw * .065, a, 0, TAU); g.fill(); }
  g.fillStyle = '#ffd65c'; circle(g, cx, cy, rw * .09); g.fill();
  }
  // 路面小石子
  for (const p of F.paths) {
    const n = Math.round(p.length / (rw * .32));
    for (let i = 0; i < n; i++) {
      const t = (i + rnd()) / n, q = p.at(t);
      if (Math.hypot(q.x - cx, q.y - cy) < rw * .75) continue;
      const a = p.angle(t), off = (rnd() - .5) * rw * .72;
      g.fillStyle = rnd() < .55 ? 'rgba(222,188,124,.75)' : 'rgba(255,248,226,.9)';
      g.beginPath(); g.ellipse(q.x - Math.sin(a) * off, q.y + Math.cos(a) * off, (1.2 + rnd() * 1.6) * S0, (.9 + rnd()) * S0, a + rnd(), 0, TAU); g.fill();
    }
  }
  // 路边草簇
  for (const p of F.paths) {
    const n = Math.round(p.length / (rw * .9));
    for (let i = 0; i < n; i++) {
      const t = (i + rnd()) / n, q = p.at(t), a = p.angle(t), side = rnd() < .5 ? -1 : 1, off = side * (rw * .5 + 3 * S0);
      const x = q.x - Math.sin(a) * off, y = q.y + Math.cos(a) * off;
      if (!farFromRoads(F, x, y, -rw * .05)) continue;
      drawBlades(g, x, y, 6 * S0, S0, rnd() < .5 ? '#5e9f45' : '#86c561', rnd);
    }
  }
  g.restore();
}
function drawPlatforms(g, F) {
  const {rw, S0, ys, T} = F;
  for (const side of ['player','enemy']) for (const y of ys) {
    const gate = side === 'player' ? F.x1L : F.x1R, sign = side === 'player' ? 1 : -1;
    const x0 = sign > 0 ? gate : gate-rw*1.6, width = rw*1.6, hh = rw*.31;
    g.fillStyle = 'rgba(86,99,51,.18)'; rr(g,x0+3*S0,y-hh+5*S0,width,hh*2,rw*.15); g.fill();
    g.fillStyle = '#c9ac85'; rr(g,x0,y-hh+3*S0,width,hh*2,rw*.15); g.fill();
    g.fillStyle = '#f8ead0'; g.strokeStyle = '#bc9771'; g.lineWidth = Math.max(1,S0);
    rr(g,x0,y-hh,width,hh*2,rw*.15); g.fill(); g.stroke();
    g.strokeStyle = 'rgba(168,126,88,.35)'; g.beginPath();
    for(let i=1;i<4;i++){g.moveTo(x0+width*i/4,y-hh);g.lineTo(x0+width*i/4,y+hh);}g.stroke();
  }
}
function drawTree(g, x, y, r, rnd, S0, kind) {
  const lw = Math.max(1, 1.5 * S0);
  g.fillStyle = 'rgba(52,96,44,.25)'; g.beginPath(); g.ellipse(x + r * .3, y + r * .08, r * .95, r * .34, 0, 0, TAU); g.fill();
  if (kind === 'mush') {
    g.fillStyle = '#fff4e2'; g.strokeStyle = '#a07a5a'; g.lineWidth = lw; rr(g, x - r * .22, y - r * .6, r * .44, r * .62, r * .18); g.fill(); g.stroke();
    g.fillStyle = '#ff6b7a'; g.strokeStyle = '#a83a4a'; g.beginPath(); g.ellipse(x, y - r * .58, r * .62, r * .46, 0, Math.PI, 0); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#fffaf2'; for (const [dx, dy, dr] of [[-.3, -.75, .1], [.12, -.88, .12], [.36, -.68, .08]]) { circle(g, x + dx * r, y + dy * r, dr * r); g.fill(); }
    return;
  }
  if (kind === 'cotton') {
    g.fillStyle = '#fffaf2'; g.strokeStyle = '#b89a8a'; g.lineWidth = lw; rr(g, x - r * .07, y - r * 1.15, r * .14, r * 1.15, r * .07); g.fill(); g.stroke();
    const c = rnd() < .5 ? ['#ffc2dc', '#ffe0ee', '#e98aae'] : ['#bfe3ff', '#e2f2ff', '#7cb8e8'];
    const puffs = [[0, -1.6, .5], [-.38, -1.35, .4], [.4, -1.38, .42], [-.15, -1.25, .4], [.18, -1.82, .34]];
    for (const [dx, dy, pr] of puffs) { circle(g, x + dx * r, y + dy * r, pr * r + lw); g.fillStyle = c[2]; g.fill(); }
    for (const [dx, dy, pr] of puffs) { circle(g, x + dx * r, y + dy * r, pr * r); g.fillStyle = c[0]; g.fill(); }
    for (const [dx, dy, pr] of puffs) { circle(g, x + (dx - .12) * r, y + (dy - .12) * r, pr * r * .45); g.fillStyle = c[1]; g.fill(); }
    return;
  }
  g.fillStyle = '#b07a4a'; g.strokeStyle = '#7a4f2c'; g.lineWidth = lw; rr(g, x - r * .12, y - r * .9, r * .24, r * .92, r * .1); g.fill(); g.stroke();
  const leaves = [[0, -1.45, .58], [-.42, -1.15, .45], [.42, -1.12, .46], [0, -1.05, .5]];
  for (const [dx, dy, pr] of leaves) { circle(g, x + dx * r, y + dy * r, pr * r + lw); g.fillStyle = '#3f7f3a'; g.fill(); }
  for (const [dx, dy, pr] of leaves) { circle(g, x + dx * r, y + dy * r, pr * r); g.fillStyle = '#62ad4c'; g.fill(); }
  for (const [dx, dy, pr] of leaves) { circle(g, x + (dx - .14) * r, y + (dy - .14) * r, pr * r * .45); g.fillStyle = '#8fd06a'; g.fill(); }
  g.fillStyle = '#ff6b7a'; for (let k = 0; k < 3; k++) { circle(g, x + (rnd() - .5) * r, y - r * (1.1 + rnd() * .5), r * .07); g.fill(); }
}
const CAKE_SQUASH = .4, CAKE_LINE = '#8a5a3c';
function cream(g, x, y, r, S0) { circle(g, x, y, r); g.fillStyle = '#fffaf2'; g.fill(); g.strokeStyle = 'rgba(138,90,60,.4)'; g.lineWidth = Math.max(.8, S0); g.stroke(); }
function cakeTier(g, F, cx, by, rx, h, team, rnd) {
  const ry = rx * CAKE_SQUASH, rt = rx * .92, rty = rt * CAKE_SQUASH, S0 = F.S0, lw = Math.max(1.2, 2 * S0), ty = by - h;
  const side = new Path2D(); side.moveTo(cx - rt, ty); side.lineTo(cx - rx, by); side.ellipse(cx, by, rx, ry, 0, Math.PI, 0, true); side.lineTo(cx + rt, ty); side.closePath();
  const sg = g.createLinearGradient(cx - rx, 0, cx + rx, 0); sg.addColorStop(0, '#f8d39c'); sg.addColorStop(.35, '#ffe6b8'); sg.addColorStop(1, '#dea063');
  g.fillStyle = sg; g.fill(side); g.strokeStyle = CAKE_LINE; g.lineWidth = lw; g.stroke(side);
  g.save(); g.clip(side); g.strokeStyle = team.main; g.globalAlpha = .55; g.lineWidth = h * .12;
  g.beginPath(); g.ellipse(cx, by - h * .45, (rx + rt) / 2, ry, 0, 0, Math.PI); g.stroke(); g.restore();
  g.fillStyle = '#fffaf2';
  for (let k = 0; k < 8; k++) { const a = .1 * Math.PI + k / 7 * .8 * Math.PI, x = cx + Math.cos(a) * rt, y = ty + Math.sin(a) * rty; rr(g, x - rt * .07, y - rty * .2, rt * .14, h * (.22 + ((k * 37) % 5) * .06), rt * .07); g.fill(); }
  g.beginPath(); g.ellipse(cx, ty, rt * 1.03, rty * 1.05, 0, 0, TAU); g.fill(); g.strokeStyle = 'rgba(138,90,60,.55)'; g.lineWidth = lw * .8; g.stroke();
  g.fillStyle = team.light; g.beginPath(); g.ellipse(cx, ty, rt * .74, rty * .74, 0, 0, TAU); g.fill();
  for (let k = 0; k < 9; k++) {
    const a = rnd() * TAU, d = .15 + rnd() * .45; g.save(); g.translate(cx + Math.cos(a) * rt * d, ty + Math.sin(a) * rty * d); g.rotate(rnd() * TAU);
    g.fillStyle = CANDY[k % CANDY.length]; rr(g, -rt * .05, -rt * .016, rt * .1, rt * .032, rt * .016); g.fill(); g.restore();
  }
  for (let k = 0; k < 16; k++) { const a = k / 16 * TAU; cream(g, cx + Math.cos(a) * rt * .9, ty + Math.sin(a) * rty * .9 - rt * .03, rt * .1, S0); }
  return ty;
}

// Mild perspective is only a drawing transform. Input uses its exact inverse.
function depth(F,y) { return clamp(.8+.2*(y-F.ys[0])/(F.ys[2]-F.ys[0]),.7,1.12); }
function project(F,x,y) { const k=depth(F,y); return {x:F.cx+(x-F.cx)*k,y,k}; }
function unproject(F,x,y) { return {x:F.cx+(x-F.cx)/depth(F,y),y}; }
function atGround(g,F,x,y,paint) { const p=project(F,x,y); g.save();g.translate(p.x,p.y);g.scale(p.k,p.k);paint(p);g.restore(); }

function drawGround(g,F) {
  const {w,h,rw,S0}=F,rnd=rng(20261007);
  const flat=document.createElement('canvas'), pad=w*.26;
  flat.width=Math.ceil(w+pad*2);flat.height=Math.ceil(h);
  const a=flat.getContext('2d');a.translate(pad,0);
  const base=a.createLinearGradient(0,0,0,h);base.addColorStop(0,'#bce694');base.addColorStop(1,'#99cf75');
  a.fillStyle=base;a.fillRect(-pad,0,w+pad*2,h);
  for(let i=0;i<28;i++){
    const x=rnd()*w,y=rnd()*h,r=w*(.04+rnd()*.09),c=a.createRadialGradient(x,y,0,x,y,r);
    c.addColorStop(0,i%2?'rgba(234,249,184,.28)':'rgba(85,156,71,.12)');c.addColorStop(1,'rgba(159,215,113,0)');
    a.fillStyle=c;a.fillRect(x-r,y-r,r*2,r*2);
  }
  for(let i=0;i<w*h/1000;i++)drawBlades(a,rnd()*w,rnd()*h,(3+rnd()*5)*S0,S0,'rgba(83,147,65,.25)',rnd);
  // Road masks are built at 1x once per resize, never in the animation loop.
  const roads=document.createElement('canvas');roads.width=w;roads.height=h;
  drawRoads(roads.getContext('2d'),F,rnd);a.drawImage(roads,0,0);
  drawPlatforms(a,F);
  const flowers=['#fff5df','#ffccde','#e4d5ff','#ffe08e'];
  for(let i=0;i<120;i++){
    const x=rnd()*w,y=rnd()*h;if(!farFromRoads(F,x,y,rw*.35))continue;
    drawFlower(a,x,y,2.2*S0,flowers[i%4],rnd);
  }
  // Row projection includes overscan so the ground fills the entire screen.
  for(let y=0;y<h;y++){
    const k=depth(F,y),left=F.cx+(-pad-F.cx)*k;
    g.drawImage(flat,0,y,flat.width,1,left,y,flat.width*k,1);
  }
  // Tall decorations are projected at their feet and retain their silhouettes.
  const paintTree=(x,y,r,kind)=>atGround(g,F,x,y,()=>drawTree(g,0,0,r,rnd,S0,kind));
  const edgeR=rw*.52;
  for(let x=-edgeR;x<w+edgeR;x+=rw*.68){
    for(const row of [0,1]){
      const top=Math.min(F.top+rw*.65+row*rw*.12,F.ys[0]-rw*.64);
      const bottom=Math.max(F.bottom+rw*.3+row*rw*.24,F.ys[2]+rw*1.4);
      paintTree(x+row*rw*.32,top+(rnd()-.5)*rw*.15,edgeR*(.75+rnd()*.3),rnd()<.7?'cotton':'tree');
      paintTree(x+row*rw*.32,bottom+(rnd()-.5)*rw*.2,edgeR*(.9+rnd()*.4),rnd()<.65?'cotton':'tree');
      if(row===0&&rnd()<.6)atGround(g,F,x,top,()=>lolly(g,0,0,rw*.24,CANDY[Math.floor(rnd()*6)],S0,rw*.75));
    }
  }
  const deco=[];
  for(let i=0;i<220&&deco.length<18;i++){
    const x=lerp(F.rs+rw*1.6,F.re-rw*1.6,rnd()),y=lerp(F.ys[0],F.ys[2]+rw,rnd());
    if(!farFromRoads(F,x,y,rw*.9)||deco.some(d=>Math.hypot(d.x-x,d.y-y)<rw*1.4))continue;
    deco.push({x,y});
  }
  deco.sort((a,b)=>a.y-b.y).forEach(d=>paintTree(d.x,d.y,rw*.38,rnd()<.6?'mush':'cotton'));
  if(F.mode==='straight'){
    // Two pairs of candy milestones between lanes, with clear grass buffers.
    for(const t of [1/3,2/3])for(const y of [(F.ys[0]+F.cy)/2,(F.cy+F.ys[2])/2]){
      const x=lerp(F.rs,F.re,t);
      atGround(g,F,x,y,()=>{
        g.fillStyle='rgba(88,132,67,.16)';g.beginPath();g.ellipse(rw*.08,rw*.08,rw*.55,rw*.25,0,0,TAU);g.fill();
        lolly(g,-rw*.22,0,rw*.15,'#c9a2ff',S0,rw*.44);lolly(g,rw*.22,0,rw*.15,'#ffb1c9',S0,rw*.44);
      });
    }
  }
}
function background(F,dpr=1){const c=document.createElement('canvas');c.width=Math.round(F.w*dpr);c.height=Math.round(F.h*dpr);const g=c.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);drawGround(g,F);return c;}

// A side-view gingerbread portal on the inner facade. Its baseline is the path's y.
function gingerGate(g,F,x,base,w,h,team){
  const lw=Math.max(1.1,F.S0*1.4);
  g.save();g.translate(x,base);g.transform(.48,-.16,0,1,0,0);
  const arch=(width,height)=>{g.beginPath();g.moveTo(-width/2,0);g.lineTo(-width/2,-height+width/2);g.arc(0,-height+width/2,width/2,Math.PI,0);g.lineTo(width/2,0);};
  arch(w,h);g.closePath();g.fillStyle='#c9874c';g.fill();g.strokeStyle='#87552f';g.lineWidth=lw;g.stroke();
  arch(w*.7,h*.86);g.closePath();g.fillStyle='#70482d';g.fill();
  arch(w*.45,h*.72);g.closePath();g.fillStyle='#422b24';g.fill();
  g.fillStyle='#f2bb72';g.globalAlpha=.35;g.fillRect(w*.03,-h*.56,w*.2,h*.56);g.globalAlpha=1;
  arch(w*1.06,h*1.03);g.lineWidth=w*.11;g.strokeStyle='#fff8eb';g.stroke();
  g.setLineDash([w*.11,w*.12]);g.strokeStyle='#ee7380';g.stroke();g.setLineDash([]);
  g.restore();
  // The awning stretches into the battlefield and its scallops face the opening.
  g.beginPath();g.moveTo(x-w*.26,base-h*1.01);g.quadraticCurveTo(x+w*.12,base-h*1.17,x+w*.64,base-h*.91);
  g.lineTo(x+w*.64,base-h*.79);g.quadraticCurveTo(x+w*.1,base-h*.9,x-w*.26,base-h*.93);g.closePath();
  g.fillStyle=team.main;g.fill();g.strokeStyle=team.dark;g.lineWidth=lw;g.stroke();
  for(let i=0;i<4;i++)cream(g,x+w*(.1+i*.15),base-h*(.86-i*.012),w*.085,F.S0);
}
function drawWall(g,F,side,st={}){
  const {T,ys,S0}=F,team=TEAM[side],enemy=side==='enemy',rnd=rng(21),height=T*.48;
  const x0=F.m,x1=F.x1L,y0=ys[0]-T*.44,y1=ys[2]+T*.5;
  const point=(x,y,lift=0)=>{const p=project(F,enemy?F.w-x:x,y);return{x:p.x,y:p.y-lift*p.k,k:p.k};};
  const poly=pts=>{g.beginPath();g.moveTo(pts[0].x,pts[0].y);for(const p of pts.slice(1))g.lineTo(p.x,p.y);g.closePath();};
  g.save();if(st.shake>0)g.translate((Math.random()-.5)*4*S0*st.shake,(Math.random()-.5)*2*S0*st.shake);
  // Shadows always fall down and right, independently of the mirrored team.
  g.fillStyle='rgba(85,100,54,.19)';poly([point(x0,y0),point(x1+T*.24,y0+T*.16),point(x1+T*.24,y1+T*.16),point(x0,y1)]);g.fill();
  const sideFace=[point(x1,y0,height),point(x1,y1,height),point(x1,y1),point(x1,y0)];
  poly(sideFace);g.fillStyle=enemy?'#efc088':'#eac08b';g.fill();g.strokeStyle=CAKE_LINE;g.lineWidth=Math.max(1.2,1.6*S0);g.stroke();
  for(let j=0;j<2;j++){
    g.strokeStyle=j?team.main:'#fff0ce';g.lineWidth=T*(j?.065:.05);
    const a=point(x1,y0,height*(.25+j*.4)),b=point(x1,y1,height*(.25+j*.4));g.beginPath();g.moveTo(a.x,a.y);g.lineTo(b.x,b.y);g.stroke();
  }
  poly([point(x0,y1,height),point(x1,y1,height),point(x1,y1),point(x0,y1)]);g.fillStyle='#dca269';g.fill();g.strokeStyle=CAKE_LINE;g.stroke();
  const roof=[point(x0,y0,height),point(x1,y0,height),point(x1,y1,height),point(x0,y1,height)];
  poly(roof);g.fillStyle='#fff8ea';g.fill();g.strokeStyle=CAKE_LINE;g.stroke();
  poly([point(x0+T*.15,y0+T*.12,height+.5),point(x1-T*.13,y0+T*.12,height+.5),point(x1-T*.13,y1-T*.12,height+.5),point(x0+T*.15,y1-T*.12,height+.5)]);g.fillStyle=team.light;g.fill();
  for(let y=y0+T*.15;y<y1;y+=T*.18){const p=point(x1,y,height);g.fillStyle='#fff8ea';rr(g,p.x-T*.045*p.k,p.y-T*.025,T*.09*p.k,T*.15*p.k,T*.045);g.fill();}
  // Independent depth scaling keeps the upper palace narrower and the towers upright.
  for(let i=0;i<3;i++){
    const tower=point(x0+T*.48,ys[i]-T*.18,height),main=i===1;
    g.save();g.translate(tower.x,tower.y);g.scale(tower.k,tower.k);
    let by=0,top=0;for(const [r,h] of (main?[[.55,.33],[.37,.28]]:[[.43,.31]])){top=cakeTier(g,F,0,by,T*r,T*h,team,rnd);by-=T*h;}
    if(i===0)lolly(g,0,top,T*.23,team.main,S0,T*.52);
    g.restore();
    const gate=point(x1,ys[i]);g.save();g.translate(gate.x,gate.y);g.scale(enemy?-gate.k:gate.k,gate.k);
    gingerGate(g,F,0,0,T*(main?.53:.43),T*(main?.68:.57),team);g.restore();
  }
  const damage=1-(st.hp??1);
  if(damage>.15){g.strokeStyle='#aa7653';g.lineWidth=Math.max(1,S0);for(let i=0;i<Math.floor(damage*9);i++){const p=point(x1,y0+T*.7+i*(y1-y0-T)/9,height*.42);g.beginPath();g.moveTo(p.x,p.y);g.lineTo(p.x+4*S0,p.y+4*S0);g.lineTo(p.x+S0,p.y+9*S0);g.stroke();}}
  if(st.flash>0){g.fillStyle=`rgba(255,255,255,${Math.min(.65,st.flash*.45)})`;poly(sideFace);g.fill();}
  g.restore();
}

function cannonDims(F){return{R:F.T*.32,bl:F.T*.59,bw:F.T*.36,hb:F.T*.18};}
function cannonPose(F,side,angle,recoil=0){
  const p=project(F,F.pivot[side].x,F.pivot[side].y),d=cannonDims(F),rec=recoil*d.R*.22;
  return{x:p.x-Math.cos(angle)*rec*p.k,y:p.y-(d.hb+F.T*.04)*p.k-Math.sin(angle)*.55*rec*p.k,k:p.k,angle};
}
function muzzle(F,side,angle,recoil=0){const p=cannonPose(F,side,angle,recoil),d=cannonDims(F);return{x:p.x+Math.cos(angle)*d.bl*p.k,y:p.y+Math.sin(angle)*.55*d.bl*p.k};}
function drawCannon(g,F,side,st){
  const p=cannonPose(F,side,st.angle,st.recoil||0),{bl,bw,R}=cannonDims(F),team=TEAM[side],lw=Math.max(1,F.S0*1.3);
  g.save();g.translate(p.x,p.y);g.scale(p.k,p.k);
  const ax=Math.cos(st.angle),ay=Math.sin(st.angle)*.55,ex=ax*bl,ey=ay*bl,n=Math.hypot(ax,ay),nx=-ay/n,ny=ax/n;
  g.fillStyle='rgba(115,82,58,.20)';g.beginPath();g.ellipse(R*.28,R*.62,R*1.45,R*.48,0,0,TAU);g.fill();
  const barrel=g.createLinearGradient(0,-bw*.5,0,bw*.5);barrel.addColorStop(0,'#fff1c4');barrel.addColorStop(.45,'#ffe5a4');barrel.addColorStop(1,'#d69d59');
  g.lineCap='round';g.lineWidth=bw+lw*2;g.strokeStyle=CAKE_LINE;g.beginPath();g.moveTo(-ax*R*.45,-ay*R*.45);g.lineTo(ex,ey);g.stroke();
  g.lineWidth=bw;g.strokeStyle=barrel;g.stroke();
  // Dripping frosting covers the top half of the Swiss roll, leaving the mouth open.
  const bx=-ax*R*.5,by=-ay*R*.5;
  g.beginPath();g.moveTo(bx,by-bw*.36);g.quadraticCurveTo(ex*.45,ey*.45-bw*.8,ex-ax*bw*.22,ey-bw*.34);
  g.lineTo(ex-ax*bw*.21,ey-bw*.07);
  for(let i=4;i>=0;i--){const t=i/5,x=lerp(bx,ex-ax*bw*.21,t),y=lerp(by,ey,t);g.quadraticCurveTo(x+bw*.1,y+bw*(i%2?.21:.08),x-bw*.05,y-bw*.04);}
  g.closePath();g.fillStyle=side==='player'?'#b7e2ff':'#ffb4ce';g.fill();g.strokeStyle=side==='player'?'#659bc7':'#ca7793';g.lineWidth=lw;g.stroke();
  g.strokeStyle='rgba(255,255,255,.68)';g.lineWidth=bw*.08;g.beginPath();g.moveTo(bx+R*.1,by-bw*.4);g.quadraticCurveTo(ex*.4,ey*.4-bw*.62,ex-ax*bw*.3,ey-bw*.32);g.stroke();
  // Elliptical mouth, with warm thickness and a visible dark center.
  g.save();g.translate(ex,ey);g.rotate(Math.atan2(ay,ax));
  g.beginPath();g.ellipse(0,0,bw*.25,bw*.49,0,0,TAU);g.fillStyle='#f7cc83';g.fill();g.strokeStyle=CAKE_LINE;g.lineWidth=lw;g.stroke();
  g.beginPath();g.ellipse(0,0,bw*.15,bw*.34,0,0,TAU);g.fillStyle='#743b2c';g.fill();g.restore();
  // A cream spiral wheel remains on the visible lower side as the gun turns.
  const wx=-ax*R*.17+nx*R*.3,wy=-ay*R*.17+Math.abs(ny)*R*.63,wr=R*.67;
  g.beginPath();g.ellipse(wx,wy,wr,wr*.84,0,0,TAU);g.fillStyle=team.main;g.fill();g.strokeStyle=CAKE_LINE;g.lineWidth=lw;g.stroke();
  g.beginPath();g.ellipse(wx-wr*.02,wy-wr*.02,wr*.79,wr*.67,0,0,TAU);g.fillStyle='#fff3dc';g.fill();
  g.strokeStyle=side==='player'?'#96cffa':'#ff9ebb';g.lineWidth=wr*.22;g.beginPath();
  for(let a=0;a<TAU*1.6;a+=.12){const r=wr*(.04+a*.067);g.lineTo(wx+Math.cos(a)*r,wy+Math.sin(a)*r*.84);}g.stroke();
  const cherryX=bx*.25,cherryY=by*.25-bw*.65;
  g.beginPath();g.arc(cherryX,cherryY,bw*.21,0,TAU);g.fillStyle='#d93255';g.fill();g.strokeStyle='#a32a41';g.lineWidth=lw;g.stroke();
  g.fillStyle='#fff1ec';circle(g,cherryX-bw*.055,cherryY-bw*.055,bw*.055);g.fill();
  g.strokeStyle='#7e5140';g.lineWidth=lw;g.beginPath();g.moveTo(cherryX,cherryY-bw*.17);g.bezierCurveTo(cherryX+bw*.1,cherryY-bw*.46,cherryX+bw*.42,cherryY-bw*.38,cherryX+bw*.3,cherryY-bw*.59);g.stroke();
  if(st.glow>0){const glow=g.createRadialGradient(ex,ey,0,ex,ey,bw*.7);glow.addColorStop(0,`rgba(255,241,173,${st.glow*.8})`);glow.addColorStop(1,'rgba(255,231,128,0)');g.fillStyle=glow;circle(g,ex,ey,bw*.7);g.fill();}
  g.restore();
}
function highlightLane(g,F,i,color){
  g.save();g.lineCap='round';g.lineJoin='round';g.strokeStyle=color;g.globalAlpha=.7;g.lineWidth=Math.max(1.5,2.5*F.S0);g.setLineDash([F.rw*.25,F.rw*.2]);g.beginPath();
  for(let j=0;j<=160;j++){const q=F.paths[i].at(j/160),p=project(F,q.x,q.y);j?g.lineTo(p.x,p.y):g.moveTo(p.x,p.y);}g.stroke();g.restore();
}
function nearestLane(F,x,y){let best={i:0,d:Infinity,t:0};F.paths.forEach((p,i)=>{const n=p.nearest(x,y);if(n.d<best.d)best={i,d:n.d,t:n.t};});return best;}
window.CandyField={TEAM,INK,rr,circle,rng,Path,buildGeometry,depth,project,unproject,atGround,drawGround,background,drawWall,drawCannon,cannonPose,cannonDims,muzzle,highlightLane,nearestLane};

})();
