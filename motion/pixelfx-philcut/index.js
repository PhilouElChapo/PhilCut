/* PhilCut : les effets pixel art de pixelfx (patch-gg/pixelfx, MIT ; sim.js et effets marqués adaptés de Sprite Fusion,
 * Hugo Duprez, MIT ; act.js adapté de Hollow Crown, MIT) dans une composition HyperFrames, image par image.
 *
 *   PFX.effect("fire/campfire", {x, y (pixels de la composition : là où se pose l'origine de l'effet, souvent le sol),
 *     scale (taille d'un pixel, 4 par défaut), start (s), duration (s, pour une boucle ; une animation unique dure ce
 *     qu'elle dure), flip, angle, seed, palette, light, z, parent})
 * Les effets simulés (étincelles, fumée…) sont rejoués depuis leur début à pas fixe de 1/120 s : même image à chaque fois.
 */
import { createFrame, clearFrame, createFx, composite } from "pixelfx";
import { effects } from "pixelfx/fx/index";

const PAS = 1 / 120;
const tous = [];

class Effet {
  constructor(id, o = {}) {
    const mod = effects[id];
    if (!mod) throw new Error("pixelfx : effet inconnu « " + id + " »");
    this.mod = mod; this.id = id; this.o = o;
    const m = mod.meta || {};
    this.meta = m;
    const [w, h] = m.size || [128, 128], [ox, oy] = m.origin || [w / 2, h / 2];
    this.w = w; this.h = h; this.ox = ox; this.oy = oy;
    const k = o.scale ?? 4;
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const gX = o.x ?? (typeof W !== "undefined" ? W / 2 : 960), gY = o.y ?? (typeof H !== "undefined" ? H * 0.7 : 760);
    cv.style.cssText = `position:absolute;left:${gX - ox * k}px;top:${gY - oy * k}px;width:${w * k}px;height:${h * k}px;` +
      `image-rendering:pixelated;pointer-events:none;z-index:${o.z ?? 2};opacity:0`;
    (typeof o.parent === "string" ? document.querySelector(o.parent) : o.parent || document.querySelector("#scenes") || document.body).appendChild(cv);
    this.cv = cv; this.ctx = cv.getContext("2d");
    this.img = this.ctx.createImageData(w, h);
    this.frame = createFrame(w, h, -ox, -oy);
    this.debut = o.start ?? 0;
    // une boucle dure jusqu'à la fin de l'animation (sauf durée donnée) ; un effet unique, ce qu'il dure
    this.duree = m.loop ? (o.duration ?? Infinity) : (o.duration ?? m.duration ?? 1);
    this.inst = null;
  }
  _neuf() {
    const o = Object.assign({}, this.o);
    delete o.x; delete o.y; delete o.scale; delete o.start; delete o.duration; delete o.z; delete o.parent;
    this.inst = createFx(this.mod, Object.assign(o, { x: 0, y: 0 }));
    this.tl = 0;
  }
  render(t) {
    const local = t - this.debut;
    if (local < 0 || local > this.duree) { this.cv.style.opacity = "0"; return; }
    this.cv.style.opacity = "1";
    if (!this.inst || local + 1e-9 < this.tl) this._neuf();
    while (this.tl + PAS <= local + 1e-9) { this.inst.update(PAS); this.tl += PAS; }
    clearFrame(this.frame);
    this.inst.draw(this.frame);
    composite(this.frame, this.img.data, null, 1);
    this.ctx.putImageData(this.img, 0, 0);
  }
}

let branche = false;
function brancher() {
  if (branche) return;
  branche = true;
  window.addEventListener("hf-seek", (e) => {
    const t = e.detail ? e.detail.time : 0;
    for (const x of tous) x.render(t);
  });
}

export function effect(id, o = {}) {
  const x = new Effet(id, o);
  tous.push(x);
  brancher();
  x.render(0);
  return x;
}
export function list() { return Object.keys(effects); }
export function info(id) { return (effects[id] || {}).meta; }
