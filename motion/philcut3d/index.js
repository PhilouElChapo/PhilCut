/* PhilCut 3D (1.3.1) : une scène Three.js dans une composition HyperFrames, rendue image par image.
 *
 * Tout dépend du temps t (secondes) : images clefs, particules, physique précalculée une fois (Rapier, pas fixe) puis lue à
 * l'instant demandé. HyperFrames envoie « hf-seek » à chaque image : la scène se dessine pour cet instant ; tant que
 * Rapier, les textures et les polices ne sont pas prêts, la capture attend (waitUntil).
 *
 * API (globale P3), décrite à l'IA dans app/motion_libre.py (CONSIGNE_3D) :
 *   const S = P3.scene({background, camera: {pos, look, fov}, light, shadows, bloom, grain, blur, vignette, exposure});
 *   S.box/sphere/cylinder/cone/torus/plane/image/text/group/floor/particles(...) → objet Three.js (mesh ou groupe)
 *   S.key(obj, t, {pos, rot, scale, opacity, color}, ease) ; S.cameraKey(t, {pos, look, fov}, ease) ; S.animate(fn(t, S))
 *   S.physics({gravity, start, end}) ; S.body(obj, {type, shape, restitution, friction, density, velocity, spin, impulse})
 */
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { BokehPass } from "three/examples/jsm/postprocessing/BokehPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import RAPIER from "@dimforge/rapier3d-compat";

const DEG = Math.PI / 180;

// ------------------------------------------------------------------ courbes (noms de GSAP)
const base = {
  linear: (x) => x, none: (x) => x,
  power1: (x) => x * x, power2: (x) => x * x * x, power3: (x) => x ** 4, power4: (x) => x ** 5,
  sine: (x) => 1 - Math.cos((x * Math.PI) / 2),
  expo: (x) => (x === 0 ? 0 : 2 ** (10 * x - 10)),
  circ: (x) => 1 - Math.sqrt(1 - x * x),
  back: (x) => 2.70158 * x * x * x - 1.70158 * x * x,
  elastic: (x) => (x === 0 || x === 1 ? x : -(2 ** (10 * x - 10)) * Math.sin((x * 10 - 10.75) * ((2 * Math.PI) / 3))),
  bounce: (x) => 1 - bounceOut(1 - x),
};
function bounceOut(x) {
  const n = 7.5625, d = 2.75;
  if (x < 1 / d) return n * x * x;
  if (x < 2 / d) return n * (x -= 1.5 / d) * x + 0.75;
  if (x < 2.5 / d) return n * (x -= 2.25 / d) * x + 0.9375;
  return n * (x -= 2.625 / d) * x + 0.984375;
}
export function ease(nom) {
  if (typeof nom === "function") return nom;
  const [famille, sens] = String(nom || "power2.inOut").split(".");
  const f = base[famille] || base.power2;
  if (famille === "linear" || famille === "none") return f;
  if (sens === "in") return f;
  if (sens === "out") return (x) => 1 - f(1 - x);
  return (x) => (x < 0.5 ? f(2 * x) / 2 : 1 - f(2 - 2 * x) / 2);
}

// ------------------------------------------------------------------ hasard reproductible
export function rng(graine = 1) {
  let a = (typeof graine === "string" ? [...graine].reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 7) : graine) >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ------------------------------------------------------------------ grain et vignette (instant fixé : même image à chaque fois)
const GrainVignette = {
  uniforms: { tDiffuse: { value: null }, temps: { value: 0 }, grain: { value: 0 }, vignette: { value: 0 } },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
  fragmentShader: `uniform sampler2D tDiffuse; uniform float temps; uniform float grain; uniform float vignette; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + temps * 43.0) * 43758.5453); }
    void main(){ vec4 c = texture2D(tDiffuse, vUv);
      float n = (h(vUv * 1000.0) - 0.5) * grain * 0.25; c.rgb += n;
      float d = distance(vUv, vec2(0.5)); c.rgb *= mix(1.0, smoothstep(0.85, 0.25, d), vignette);
      gl_FragColor = c; }`,
};

const LUMIERES = {
  studio: [["amb", 0xffffff, 0.35], ["dir", 0xffffff, 2.2, [4, 8, 6]], ["dir", 0xbcd4ff, 0.8, [-6, 3, -4]]],
  sun: [["hemi", 0xdfefff, 0x6b5a45, 0.8], ["dir", 0xfff1d6, 3.0, [8, 12, 4]]],
  neon: [["amb", 0x1b1035, 0.5], ["point", 0xff3df0, 60, [-3, 3, 3]], ["point", 0x2ee6ff, 60, [3, 2, 2]]],
  night: [["amb", 0x223355, 0.3], ["dir", 0x9fb8ff, 1.0, [-4, 6, 3]], ["point", 0xffb070, 30, [0, 2, 3]]],
  soft: [["hemi", 0xffffff, 0xd8d0c8, 1.3], ["dir", 0xffffff, 1.0, [2, 6, 5]]],
};

function v3(a, d = [0, 0, 0]) {
  if (typeof a === "number") return [a, a, a];
  return Array.isArray(a) ? [a[0] ?? d[0], a[1] ?? d[1], a[2] ?? d[2]] : d.slice();
}

class Scene3D {
  constructor(o = {}) {
    // W, H, D : constantes de la composition PhilCut (portée globale des scripts), sinon window, sinon 1920×1080
    const gW = typeof W !== "undefined" ? W : window.W, gH = typeof H !== "undefined" ? H : window.H;
    const gD = typeof D !== "undefined" ? D : window.D;
    const Wd = o.width || gW || 1920, Hd = o.height || gH || 1080;
    this.W = Wd; this.H = Hd; this.D = o.duration || gD || 10;
    const transparent = typeof TRANSPARENT !== "undefined" ? TRANSPARENT : false;
    const parent = typeof o.parent === "string" ? document.querySelector(o.parent) : o.parent || document.querySelector("#scenes") || document.body;
    const canvas = document.createElement("canvas");
    canvas.className = "p3-canvas";
    canvas.style.cssText = `position:absolute;left:0;top:0;width:${Wd}px;height:${Hd}px;z-index:${o.z ?? 0};pointer-events:none`;
    parent.appendChild(canvas);
    this.canvas = canvas;
    const r = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    r.setPixelRatio(1);
    r.setSize(Wd, Hd, false);
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = o.exposure ?? 1.0;
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.shadowMap.enabled = o.shadows !== false;
    r.shadowMap.type = THREE.PCFShadowMap;
    this.renderer = r;
    const s = new THREE.Scene();
    if (o.background && !transparent) s.background = new THREE.Color(o.background);
    if (o.fog) s.fog = new THREE.Fog(new THREE.Color(o.fog.color || o.background || "#000"), o.fog.near ?? 10, o.fog.far ?? 40);
    const pm = new THREE.PMREMGenerator(r);
    s.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    s.environmentIntensity = o.environment ?? 0.6;
    this.scene = s;
    const c = o.camera || {};
    this.camera = new THREE.PerspectiveCamera(c.fov ?? 35, Wd / Hd, 0.05, 1000);
    this.camera.position.set(...v3(c.pos, [0, 2, 10]));
    this.look = new THREE.Vector3(...v3(c.look, [0, 0, 0]));
    this.camera.lookAt(this.look);
    this.cameraKeys = [];
    this._lumieres(o.light || "studio", o.shadows !== false);
    this.items = new Map();          // objet → images clefs
    this.fns = [];
    this.nuages = [];
    this.bodies = [];
    this.phys = null;
    this.attente = [document.fonts ? document.fonts.ready : Promise.resolve()];
    this.effets = { bloom: o.bloom || 0, grain: o.grain || 0, blur: o.blur || 0, vignette: o.vignette || 0 };
    this.composer = null;
    if (this.effets.bloom || this.effets.grain || this.effets.blur || this.effets.vignette) this._effets(o);
    this.tPrecedent = -1;
  }

  _lumieres(nom, ombres) {
    for (const l of LUMIERES[nom] || LUMIERES.studio) {
      let x;
      if (l[0] === "amb") x = new THREE.AmbientLight(l[1], l[2]);
      else if (l[0] === "hemi") x = new THREE.HemisphereLight(l[1], l[2], l[3]);
      else if (l[0] === "dir") { x = new THREE.DirectionalLight(l[1], l[2]); x.position.set(...l[3]); }
      else { x = new THREE.PointLight(l[1], l[2], 0, 2); x.position.set(...l[3]); }
      if (ombres && l[0] === "dir" && !this._ombre) {
        x.castShadow = true;
        x.shadow.mapSize.set(2048, 2048);
        Object.assign(x.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 0.5, far: 60 });
        x.shadow.bias = -0.0005;
        x.shadow.radius = 4;
        this._ombre = x;
      }
      this.scene.add(x);
    }
  }

  _effets(o) {
    const cp = new EffectComposer(this.renderer);
    cp.setPixelRatio(1);
    cp.setSize(this.W, this.H);
    cp.addPass(new RenderPass(this.scene, this.camera));
    if (this.effets.blur) {
      const b = typeof this.effets.blur === "object" ? this.effets.blur : { amount: this.effets.blur };
      this.bokeh = new BokehPass(this.scene, this.camera, { focus: b.focus ?? 10, aperture: (b.amount ?? 0.5) * 0.004, maxblur: 0.01 });
      cp.addPass(this.bokeh);
    }
    if (this.effets.bloom) cp.addPass(new UnrealBloomPass(new THREE.Vector2(this.W, this.H), this.effets.bloom, 0.45, o.bloomThreshold ?? 0.9));
    cp.addPass(new OutputPass());
    if (this.effets.grain || this.effets.vignette) {
      this.gv = new ShaderPass(GrainVignette);
      this.gv.uniforms.grain.value = this.effets.grain;
      this.gv.uniforms.vignette.value = this.effets.vignette;
      cp.addPass(this.gv);
    }
    this.composer = cp;
  }

  // ---------------------------------------------- matières et objets
  material(o = {}) {
    const color = new THREE.Color(o.color || "#cccccc");
    const m = o.material || "plastic";
    let mat;
    if (m === "glow" || m === "light") mat = new THREE.MeshBasicMaterial({ color: color.multiplyScalar(o.intensity ?? 2), toneMapped: false });
    else if (m === "glass") mat = new THREE.MeshPhysicalMaterial({ color, roughness: 0.05, transmission: 0.92, thickness: 0.6, ior: 1.45 });
    else if (m === "metal") mat = new THREE.MeshStandardMaterial({ color, metalness: 1, roughness: o.roughness ?? 0.25 });
    else if (m === "toon") mat = new THREE.MeshToonMaterial({ color });
    else if (m === "clay") mat = new THREE.MeshStandardMaterial({ color, roughness: 0.95 });
    else if (m === "matte") mat = new THREE.MeshStandardMaterial({ color, roughness: 0.8 });
    else mat = new THREE.MeshPhysicalMaterial({ color, roughness: o.roughness ?? 0.35, clearcoat: 0.4, clearcoatRoughness: 0.3 });
    if (o.emissive) { mat.emissive = new THREE.Color(o.emissive); mat.emissiveIntensity = o.emissiveIntensity ?? 1; }
    if (o.opacity != null && o.opacity < 1) { mat.transparent = true; mat.opacity = o.opacity; }
    return mat;
  }

  _ajouter(obj, o = {}) {
    obj.position.set(...v3(o.pos, [0, 0, 0]));
    const r = v3(o.rot, [0, 0, 0]);
    obj.rotation.set(r[0] * DEG, r[1] * DEG, r[2] * DEG);
    obj.scale.set(...v3(o.scale ?? 1, [1, 1, 1]));
    obj.traverse((x) => { if (x.isMesh) { x.castShadow = o.castShadow !== false; x.receiveShadow = o.receiveShadow !== false; } });
    (o.parent || this.scene).add(obj);
    obj.userData.p3 = { opacite: o.opacity ?? 1 };
    if (o.opacity != null && o.opacity < 1) this._opacite(obj, o.opacity);
    return obj;
  }

  _mesh(geo, o) { return this._ajouter(new THREE.Mesh(geo, this.material(o)), o); }
  box(o = {}) {
    const [w, h, d] = v3(o.size ?? 1, [1, 1, 1]);
    const g = o.radius ? new RoundedBoxGeometry(w, h, d, 4, Math.min(o.radius, Math.min(w, h, d) / 2)) : new THREE.BoxGeometry(w, h, d);
    const m = this._mesh(g, o); m.userData.forme = { type: "box", taille: [w, h, d] }; return m;
  }
  sphere(o = {}) { const r = o.radius ?? 0.5; const m = this._mesh(new THREE.SphereGeometry(r, 48, 32), o); m.userData.forme = { type: "ball", r }; return m; }
  cylinder(o = {}) {
    const r = o.radius ?? 0.5, h = o.height ?? 1;
    const m = this._mesh(new THREE.CylinderGeometry(o.radiusTop ?? r, r, h, 48), o); m.userData.forme = { type: "cylinder", r, h }; return m;
  }
  cone(o = {}) { const r = o.radius ?? 0.5, h = o.height ?? 1; const m = this._mesh(new THREE.ConeGeometry(r, h, 48), o); m.userData.forme = { type: "cone", r, h }; return m; }
  torus(o = {}) { return this._mesh(new THREE.TorusGeometry(o.radius ?? 0.6, o.tube ?? 0.2, 24, 64), o); }
  plane(o = {}) { const [w, h] = v3(o.size ?? 1, [1, 1, 1]); const m = this._mesh(new THREE.PlaneGeometry(w, h), Object.assign({ material: "matte" }, o)); m.userData.forme = { type: "box", taille: [w, h, 0.02] }; return m; }
  group(o = {}) { return this._ajouter(new THREE.Group(), o); }

  floor(o = {}) {
    const taille = o.size ?? 60;
    const mat = o.shadowOnly ? new THREE.ShadowMaterial({ opacity: o.shadowOpacity ?? 0.3 }) : this.material(Object.assign({ material: "matte", color: "#888888" }, o));
    const m = new THREE.Mesh(new THREE.PlaneGeometry(taille, taille), mat);
    m.rotation.x = -Math.PI / 2;
    m.position.y = o.y ?? 0;
    m.receiveShadow = true;
    this.scene.add(m);
    m.userData.sol = true;
    return m;
  }

  image(src, o = {}) {
    const tex = new THREE.TextureLoader().load(src);
    tex.colorSpace = THREE.SRGBColorSpace;
    const largeur = o.width ?? 2;
    const mat = new THREE.MeshStandardMaterial({ map: tex, transparent: true, alphaTest: 0.02, side: THREE.DoubleSide, roughness: 0.7 });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
    this.attente.push(new Promise((ok) => {
      const fin = () => { const im = tex.image; if (im && im.width) m.scale.y = (im.height / im.width); ok(); };
      if (tex.image && tex.image.complete) fin(); else tex.onUpdate = fin;
      setTimeout(ok, 8000);
    }));
    const g = new THREE.Group();
    m.scale.set(1, 1, 1);
    g.add(m);
    g.scale.setScalar(largeur);
    this._ajouter(g, Object.assign({}, o, { scale: o.scale ?? largeur }));
    g.userData.forme = { type: "box", taille: [largeur, largeur, 0.05] };
    return g;
  }

  text(texte, o = {}) {
    const gF = typeof F !== "undefined" ? F : window.F;
    const px = 160, police = o.font || (gF && gF.titre) || "sans-serif", poids = o.weight || 800;
    const cv = document.createElement("canvas"), ctx = cv.getContext("2d");
    const dessiner = () => {
      ctx.font = `${poids} ${px}px ${police}`;
      const w = Math.ceil(ctx.measureText(texte).width) + px * 0.4;
      cv.width = w; cv.height = Math.ceil(px * 1.4);
      ctx.font = `${poids} ${px}px ${police}`;
      ctx.fillStyle = o.color || "#ffffff";
      ctx.textBaseline = "middle";
      ctx.fillText(texte, px * 0.2, cv.height / 2);
      tex.needsUpdate = true;
      plan.scale.set((o.size ?? 1) * cv.width / cv.height, o.size ?? 1, 1);
    };
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    const mat = o.material === "glow" ? new THREE.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false })
      : new THREE.MeshStandardMaterial({ map: tex, transparent: true, roughness: 0.6 });
    const plan = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
    plan.castShadow = false;
    const g = new THREE.Group();
    g.add(plan);
    dessiner();
    this.attente.push((document.fonts ? document.fonts.ready : Promise.resolve()).then(dessiner));
    return this._ajouter(g, Object.assign({ castShadow: false }, o));
  }

  particles(o = {}) {
    const n = Math.min(o.count ?? 400, 20000), al = rng(o.seed ?? "p3");
    const [ax, ay, az] = v3(o.area ?? [10, 6, 6]);
    const c = v3(o.center ?? [0, 0, 0]);
    const base = new Float32Array(n * 3), vit = new Float32Array(n * 3);
    const s = o.speed ?? 0.3, [gx, gy, gz] = v3(o.drift ?? [0, 0, 0]);
    for (let i = 0; i < n; i++) {
      base[i * 3] = c[0] + (al() - 0.5) * ax; base[i * 3 + 1] = c[1] + (al() - 0.5) * ay; base[i * 3 + 2] = c[2] + (al() - 0.5) * az;
      vit[i * 3] = gx + (al() - 0.5) * s; vit[i * 3 + 1] = gy + (al() - 0.5) * s; vit[i * 3 + 2] = gz + (al() - 0.5) * s;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(base.slice(), 3));
    const mat = new THREE.PointsMaterial({ color: new THREE.Color(o.color || "#ffffff"), size: o.size ?? 0.05, transparent: true,
      opacity: o.opacity ?? 0.9, depthWrite: false, blending: o.glow === false ? THREE.NormalBlending : THREE.AdditiveBlending, toneMapped: false });
    const pts = new THREE.Points(geo, mat);
    this.scene.add(pts);
    pts.userData.p3 = { opacite: o.opacity ?? 0.9 };
    this.nuages.push({ pts, base, vit, n, ax, ay, az, c, wrap: o.wrap !== false });
    return pts;
  }

  // ---------------------------------------------- animation
  key(obj, t, props, e = "power2.inOut") {
    if (!this.items.has(obj)) this.items.set(obj, []);
    const k = this.items.get(obj);
    k.push({ t, p: props, e: ease(e) });
    k.sort((a, b) => a.t - b.t);
    return this;
  }
  keys(obj, liste) { for (const k of liste) this.key(obj, k.t, k, k.ease); return this; }
  cameraKey(t, props, e = "power2.inOut") { this.cameraKeys.push({ t, p: props, e: ease(e) }); this.cameraKeys.sort((a, b) => a.t - b.t); return this; }
  animate(fn) { this.fns.push(fn); return this; }

  _valeur(cles, nom, t, initiale) {
    let avant = null, apres = null;
    for (const k of cles) {
      if (k.p[nom] === undefined) continue;
      if (k.t <= t) avant = k; else { apres = k; break; }
    }
    if (!avant && !apres) return initiale;
    if (!avant) return apres.p[nom] !== undefined ? (initiale ?? apres.p[nom]) : initiale;
    if (!apres || apres.t === avant.t) return avant.p[nom];
    const x = apres.e((t - avant.t) / (apres.t - avant.t));
    const a = avant.p[nom], b = apres.p[nom];
    if (typeof a === "number" && typeof b === "number") return a + (b - a) * x;
    if (typeof a === "string") return new THREE.Color(a).lerp(new THREE.Color(b), x);
    const A = v3(a), B = v3(b);
    return [A[0] + (B[0] - A[0]) * x, A[1] + (B[1] - A[1]) * x, A[2] + (B[2] - A[2]) * x];
  }

  _poser(obj, cles, t) {
    const d = obj.userData;
    if (!d.p3init) d.p3init = { pos: obj.position.toArray(), rot: [obj.rotation.x / DEG, obj.rotation.y / DEG, obj.rotation.z / DEG], scale: obj.scale.toArray() };
    const i = d.p3init;
    const p = this._valeur(cles, "pos", t, i.pos), r = this._valeur(cles, "rot", t, i.rot), s = this._valeur(cles, "scale", t, i.scale);
    obj.position.set(...v3(p)); const R = v3(r); obj.rotation.set(R[0] * DEG, R[1] * DEG, R[2] * DEG); obj.scale.set(...v3(s));
    const op = this._valeur(cles, "opacity", t, d.p3 ? d.p3.opacite : 1);
    this._opacite(obj, op);
    const col = this._valeur(cles, "color", t, null);
    if (col) obj.traverse((x) => { if (x.material && x.material.color) x.material.color.copy(col instanceof THREE.Color ? col : new THREE.Color(col)); });
    obj.visible = op > 0.001;
  }

  _opacite(obj, op) {
    obj.traverse((x) => {
      const ms = x.material ? (Array.isArray(x.material) ? x.material : [x.material]) : [];
      for (const m of ms) {
        if (m.userData.op0 === undefined) m.userData.op0 = m.opacity;
        m.transparent = m.transparent || op < 1;
        m.opacity = m.userData.op0 * op;
      }
    });
  }

  // ---------------------------------------------- physique (Rapier), précalculée une fois
  physics(o = {}) {
    this.phys = { g: v3(o.gravity ?? [0, -9.81, 0]), debut: o.start ?? 0, fin: o.end ?? this.D, hz: o.hz ?? 120, sol: o.floor };
    return this;
  }
  body(obj, o = {}) {
    if (!this.phys) this.physics();
    this.bodies.push({ obj, o });
    return obj;
  }

  async _precalculer() {
    if (!this.bodies.length || this.cuit) return;
    await RAPIER.init();
    const P = this.phys, monde = new RAPIER.World({ x: P.g[0], y: P.g[1], z: P.g[2] });
    monde.timestep = 1 / P.hz;
    if (P.sol !== false) {
      const solY = P.sol && P.sol.y != null ? P.sol.y : 0;
      const rb = monde.createRigidBody(RAPIER.RigidBodyDesc.fixed().setTranslation(0, solY - 0.5, 0));
      monde.createCollider(RAPIER.ColliderDesc.cuboid(200, 0.5, 200).setRestitution(0.2).setFriction(0.8), rb);
    }
    const corps = [];
    for (const { obj, o } of this.bodies) {
      this._poser(obj, this.items.get(obj) || [], P.debut);
      obj.updateMatrixWorld(true);
      const pos = new THREE.Vector3(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
      obj.matrixWorld.decompose(pos, q, sc);
      const type = o.type || "dynamic";
      const desc = type === "fixed" ? RAPIER.RigidBodyDesc.fixed() : type === "kinematic" ? RAPIER.RigidBodyDesc.kinematicPositionBased() : RAPIER.RigidBodyDesc.dynamic();
      desc.setTranslation(pos.x, pos.y, pos.z).setRotation({ x: q.x, y: q.y, z: q.z, w: q.w });
      if (o.velocity) { const v = v3(o.velocity); desc.setLinvel(v[0], v[1], v[2]); }
      if (o.spin) { const w = v3(o.spin).map((x) => x * DEG); desc.setAngvel({ x: w[0], y: w[1], z: w[2] }); }
      if (o.damping) desc.setLinearDamping(o.damping);
      const rb = monde.createRigidBody(desc);
      const f = obj.userData.forme || { type: "box", taille: [1, 1, 1] };
      let cd;
      const forme = o.shape || f.type;
      if (forme === "ball") cd = RAPIER.ColliderDesc.ball((f.r ?? 0.5) * sc.x);
      else if (forme === "cylinder" || forme === "cone") cd = RAPIER.ColliderDesc.cylinder(((f.h ?? 1) * sc.y) / 2, (f.r ?? 0.5) * sc.x);
      else { const t = f.taille || [1, 1, 1]; cd = RAPIER.ColliderDesc.cuboid((t[0] * sc.x) / 2, (t[1] * sc.y) / 2, Math.max(0.01, (t[2] * sc.z) / 2)); }
      cd.setRestitution(o.restitution ?? 0.3).setFriction(o.friction ?? 0.6).setDensity(o.density ?? 1);
      monde.createCollider(cd, rb);
      corps.push({ obj, o, rb, type, parent: obj.parent });
    }
    const n = Math.max(1, Math.ceil((P.fin - P.debut) * P.hz)) + 1;
    for (const c of corps) c.piste = new Float32Array(n * 7);
    for (let i = 0; i < n; i++) {
      const t = P.debut + i / P.hz;
      for (const c of corps) {
        if (c.type === "kinematic") {
          this._poser(c.obj, this.items.get(c.obj) || [], t);
          c.obj.updateMatrixWorld(true);
          const p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
          c.obj.matrixWorld.decompose(p, q, s);
          c.rb.setNextKinematicTranslation(p); c.rb.setNextKinematicRotation(q);
        }
        const imp = c.o.impulse;
        if (imp && Math.abs(t - (imp.t ?? P.debut)) < 0.5 / P.hz) {      // un coup : changement de vitesse en m/s, quelle que soit la masse
          const v = v3(imp.v || imp), m = c.rb.mass();
          c.rb.applyImpulse({ x: v[0] * m, y: v[1] * m, z: v[2] * m }, true);
        }
        const p = c.rb.translation(), q = c.rb.rotation();
        c.piste.set([p.x, p.y, p.z, q.x, q.y, q.z, q.w], i * 7);
      }
      monde.step();
    }
    this.corps = corps;
    this.nPhys = n;
    this.cuit = true;
  }

  _physique(t) {
    if (!this.corps) return;
    const P = this.phys;
    if (t < P.debut) return;                         // avant : les images clefs décident
    const x = Math.min((t - P.debut) * P.hz, this.nPhys - 1), i = Math.floor(x), k = x - i, j = Math.min(i + 1, this.nPhys - 1);
    const qa = new THREE.Quaternion(), qb = new THREE.Quaternion(), pa = new THREE.Vector3(), pb = new THREE.Vector3();
    for (const c of this.corps) {
      if (c.type === "fixed") continue;
      const a = c.piste;
      pa.set(a[i * 7], a[i * 7 + 1], a[i * 7 + 2]); pb.set(a[j * 7], a[j * 7 + 1], a[j * 7 + 2]);
      qa.set(a[i * 7 + 3], a[i * 7 + 4], a[i * 7 + 5], a[i * 7 + 6]); qb.set(a[j * 7 + 3], a[j * 7 + 4], a[j * 7 + 5], a[j * 7 + 6]);
      pa.lerp(pb, k); qa.slerp(qb, k);
      const m = new THREE.Matrix4().compose(pa, qa, c.obj.scale.clone());
      if (c.parent && c.parent !== this.scene) { c.parent.updateMatrixWorld(true); m.premultiply(new THREE.Matrix4().copy(c.parent.matrixWorld).invert()); }
      const s = new THREE.Vector3();
      m.decompose(c.obj.position, c.obj.quaternion, s);
    }
  }

  // ---------------------------------------------- prêt, dessin
  ready() {
    if (!this._pret) this._pret = Promise.all(this.attente).then(() => this._precalculer()).then(() => { this.estPret = true; });
    return this._pret;
  }

  render(t) {
    t = Math.max(0, Number(t) || 0);
    for (const [obj, cles] of this.items) this._poser(obj, cles, t);
    for (const pr of this.nuages) {
      const a = pr.pts.geometry.attributes.position.array;
      for (let i = 0; i < pr.n * 3; i += 3) {
        let x = pr.base[i] + pr.vit[i] * t, y = pr.base[i + 1] + pr.vit[i + 1] * t, z = pr.base[i + 2] + pr.vit[i + 2] * t;
        if (pr.wrap) {
          x = pr.c[0] + ((((x - pr.c[0] + pr.ax / 2) % pr.ax) + pr.ax) % pr.ax) - pr.ax / 2;
          y = pr.c[1] + ((((y - pr.c[1] + pr.ay / 2) % pr.ay) + pr.ay) % pr.ay) - pr.ay / 2;
          z = pr.c[2] + ((((z - pr.c[2] + pr.az / 2) % pr.az) + pr.az) % pr.az) - pr.az / 2;
        }
        a[i] = x; a[i + 1] = y; a[i + 2] = z;
      }
      pr.pts.geometry.attributes.position.needsUpdate = true;
    }
    this._physique(t);
    if (this.cameraKeys.length) {
      const c = this.camera;
      const p = this._valeur(this.cameraKeys, "pos", t, c.position.toArray());
      c.position.set(...v3(p));
      const l = this._valeur(this.cameraKeys, "look", t, this.look.toArray());
      this.look.set(...v3(l));
      const f = this._valeur(this.cameraKeys, "fov", t, c.fov);
      if (f !== c.fov) { c.fov = f; c.updateProjectionMatrix(); }
    }
    this.camera.lookAt(this.look);
    for (const fn of this.fns) fn(t, this);
    if (this.gv) this.gv.uniforms.temps.value = Math.floor(t * 30) / 30;
    if (this.composer) this.composer.render(); else this.renderer.render(this.scene, this.camera);
    this.tPrecedent = t;
  }
}

const scenes = [];
let branche = false;
function brancher() {
  if (branche) return;
  branche = true;
  window.addEventListener("hf-seek", (e) => {
    const t = e.detail ? e.detail.time : 0;
    const pas_prets = scenes.filter((s) => !s.estPret);
    if (pas_prets.length && e.detail && e.detail.waitUntil) {
      e.detail.waitUntil(Promise.all(pas_prets.map((s) => s.ready())).then(() => scenes.forEach((s) => s.render(t))));
    } else {
      scenes.forEach((s) => s.estPret && s.render(t));
    }
  });
}

export function scene(o = {}) {
  const s = new Scene3D(o);
  scenes.push(s);
  brancher();
  s.ready().then(() => s.render(0));
  return s;
}
export function pret() { return Promise.all(scenes.map((s) => s.ready())); }
export { THREE, RAPIER };
