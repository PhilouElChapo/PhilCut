"""Fabrique catalogue/effets_gl.json : shaders GLSL (communs PC / Android) et variantes nommées en 5 langues.
Lancer : python outils_dev/fabriquer_effets_gl.py (le fichier produit est livré et publié en ligne)."""
import json
import os


def T(fr, en, de, es, it):
    return {"fr": fr, "en": en, "de": de, "es": es, "it": it}


P_FORCE = {"cle": "force", "nom": T("Force", "Strength", "Stärke", "Fuerza", "Intensità"), "type": "float", "defaut": 0.6, "min": 0.0, "max": 1.5}

SHADERS = {
    # ------------------------------------------------------------------ rétro (film ancien)
    "retro": {
        "description": T('Film ancien : grain, rayures, poussières, couleurs passées, image qui tremble.', 'Old film: grain, scratches, dust, faded colours, gate weave.', 'Alter Film: Körnung, Kratzer, Staub, verblasste Farben, Bildstandzittern.', 'Película antigua: grano, rayas, polvo, colores desvaídos, imagen temblorosa.', "Pellicola d'epoca: grana, graffi, polvere, colori sbiaditi, immagine tremolante."),
        "parametres": [
            {"cle": "grain", "nom": T("Grain", "Grain", "Körnung", "Grano", "Grana"), "defaut": 0.35, "min": 0.0, "max": 1.0},
            {"cle": "rayures", "nom": T("Rayures et poussières", "Scratches and dust", "Kratzer und Staub", "Rayas y polvo", "Graffi e polvere"), "defaut": 0.4, "min": 0.0, "max": 1.0},
            {"cle": "delave", "nom": T("Couleurs délavées", "Faded colours", "Verblasste Farben", "Colores desvaídos", "Colori sbiaditi"), "defaut": 0.5, "min": 0.0, "max": 1.0},
            {"cle": "sepia", "nom": T("Sépia", "Sepia", "Sepia", "Sepia", "Seppia"), "defaut": 0.0, "min": 0.0, "max": 1.0},
            {"cle": "vignette", "nom": T("Vignettage", "Vignette", "Vignette", "Viñeta", "Vignettatura"), "defaut": 0.5, "min": 0.0, "max": 1.0},
            {"cle": "tremble", "nom": T("Image qui tremble", "Gate weave", "Bildstand-Zittern", "Imagen temblorosa", "Immagine tremolante"), "defaut": 0.3, "min": 0.0, "max": 1.0},
            {"cle": "chaleur", "nom": T("Chaleur", "Warmth", "Wärme", "Calidez", "Calore"), "defaut": 0.2, "min": -1.0, "max": 1.0},
        ],
        "ffmpeg": "curves=preset=vintage,noise=alls=10:allf=t,vignette=PI/4",
        "glsl": """
void main() {
    float j = floor(temps * 12.0);
    vec2 p = uv + vec2((hash(vec2(j, 2.0)) - 0.5) * 0.002, (hash(vec2(j, 1.0)) - 0.5) * 0.004) * p_tremble;
    vec3 c = lire(p).rgb;
    float l = lum(c);
    c = mix(c, vec3(l), p_delave * 0.6);
    c = mix(c, vec3(l) * vec3(1.07, 0.95, 0.78), p_sepia);
    c += vec3(0.06, 0.03, -0.03) * p_chaleur;
    c = mix(vec3(0.08), c, 1.0 - 0.25 * p_delave);
    c += (hash(uv * taille * 0.5 + vec2(j * 13.1, j * 7.7)) - 0.5) * 0.18 * p_grain;
    float x = uv.x * taille.x;
    for (int k = 0; k < 3; k++) {
        float fk = float(k);
        float xr = hash(vec2(j, fk)) * taille.x;
        float vis = step(0.6, hash(vec2(j, fk + 9.0)));
        c -= vis * p_rayures * 0.35 * smoothstep(1.5, 0.0, abs(x - xr));
    }
    float d = hash(floor(uv * taille / 3.0) + vec2(j * 3.0, j));
    c = mix(c, vec3(0.05), step(0.9993, d) * p_rayures);
    c *= 1.0 - p_vignette * smoothstep(0.35, 0.8, distance(uv, vec2(0.5)));
    couleur = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ VHS / caméscope
    "vhs": {
        "description": T('Cassette vidéo : couleurs qui bavent, lignes, bande de défilement.', 'Video tape: colour bleed, scan lines, tracking band.', 'Videokassette: Farbverlauf, Zeilen, Spurband.', 'Cinta de vídeo: color corrido, líneas, banda de arrastre.', 'Videocassetta: colori che sbavano, linee, banda di tracking.'),
        "parametres": [
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.6, "min": 0.0, "max": 1.5},
            {"cle": "lignes", "nom": T("Lignes de balayage", "Scan lines", "Zeilen", "Líneas de barrido", "Linee di scansione"), "defaut": 0.5, "min": 0.0, "max": 1.0},
            {"cle": "bavure", "nom": T("Couleurs qui bavent", "Colour bleed", "Farbverlauf", "Sangrado de color", "Sbavatura colori"), "defaut": 0.5, "min": 0.0, "max": 1.5},
            {"cle": "bande", "nom": T("Bande de défilement", "Tracking band", "Spurband", "Banda de arrastre", "Banda di tracking"), "defaut": 0.5, "min": 0.0, "max": 1.0},
        ],
        "ffmpeg": "rgbashift=rh=3:bh=-3,noise=alls=14:allf=t,eq=saturation=1.15",
        "glsl": """
void main() {
    float yb = fract(temps * 0.15);
    float dans = smoothstep(0.06, 0.0, abs(uv.y - yb));
    vec2 p = uv;
    p.x += dans * p_bande * 0.03 * (hash(vec2(floor(uv.y * taille.y), floor(temps * 30.0))) - 0.5);
    p.x += (bruit(vec2(uv.y * 40.0, temps * 2.0)) - 0.5) * 0.004 * p_force;
    float o = 0.004 * p_bavure;
    vec3 c = vec3(lire(p + vec2(o, 0.0)).r, lire(p).g, lire(p - vec2(o, 0.0)).b);
    vec3 fl = (lire(p + vec2(2.0 * o, 0.0)).rgb + lire(p - vec2(2.0 * o, 0.0)).rgb) * 0.5;
    c = vec3(lum(c)) + (mix(c, fl, 0.5 * p_bavure) - vec3(lum(fl))) * 1.1;
    c *= 1.0 - p_lignes * 0.18 * step(0.5, fract(uv.y * taille.y * 0.5));
    c += (hash(uv * taille + temps) - 0.5) * 0.08 * p_force;
    c += dans * p_bande * 0.15 * hash(vec2(uv.x * taille.x, floor(temps * 30.0)));
    c *= vec3(1.03, 1.0, 1.06);
    couleur = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ séparation RVB
    "rvb": {
        "description": T('Les trois couleurs se décalent, fixes ou au rythme.', 'The three colours shift, steady or on the beat.', 'Die drei Farben verschieben sich, fest oder im Takt.', 'Los tres colores se desplazan, fijos o al ritmo.', 'I tre colori si spostano, fissi o a ritmo.'),
        "parametres": [
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.6, "min": 0.0, "max": 2.0},
            {"cle": "angle", "nom": T("Direction (°)", "Direction (°)", "Richtung (°)", "Dirección (°)", "Direzione (°)"), "defaut": 0.0, "min": -180.0, "max": 180.0},
            {"cle": "rythme", "nom": T("Pulsations par seconde (0 = fixe)", "Pulses per second (0 = steady)", "Pulse pro Sekunde (0 = fest)", "Pulsos por segundo (0 = fijo)", "Pulsazioni al secondo (0 = fisso)"), "defaut": 0.0, "min": 0.0, "max": 4.0},
        ],
        "ffmpeg": "rgbashift=rh=8:bh=-8",
        "glsl": """
void main() {
    float a = radians(p_angle);
    float pul = p_rythme > 0.0 ? pow(max(0.0, 1.0 - fract(temps * p_rythme) * 3.0), 2.0) : 1.0;
    vec2 d = vec2(cos(a), sin(a)) * 0.012 * p_force * pul;
    couleur = vec4(lire(uv + d).r, lire(uv).g, lire(uv - d).b, 1.0);
}"""},
    # ------------------------------------------------------------------ glitch numérique
    "glitch": {
        "description": T('Interférences numériques : bandes décalées, blocs, bruit.', 'Digital interference: shifted bands, blocks, noise.', 'Digitale Störungen: versetzte Streifen, Blöcke, Rauschen.', 'Interferencias digitales: bandas desplazadas, bloques, ruido.', 'Interferenze digitali: bande sfalsate, blocchi, rumore.'),
        "parametres": [
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.6, "min": 0.0, "max": 1.5},
            {"cle": "frequence", "nom": T("Fréquence", "Frequency", "Häufigkeit", "Frecuencia", "Frequenza"), "defaut": 0.5, "min": 0.0, "max": 1.0},
            {"cle": "blocs", "nom": T("Blocs", "Blocks", "Blöcke", "Bloques", "Blocchi"), "defaut": 0.5, "min": 0.0, "max": 1.0},
        ],
        "ffmpeg": "rgbashift=rh=6:bh=-6:gv=2,noise=alls=18:allf=t+u",
        "glsl": """
void main() {
    float t = floor(temps * 15.0);
    float actif = step(1.0 - p_frequence * 0.7, hash(vec2(t, 3.1)));
    vec2 p = uv;
    float bande = floor(uv.y * mix(8.0, 40.0, hash(vec2(t, 5.0))));
    p.x += (hash(vec2(bande, t)) - 0.5) * 0.12 * p_force * actif * step(0.55, hash(vec2(bande, t + 1.0)));
    vec2 bloc = floor(uv * vec2(16.0, 9.0));
    float b = step(1.0 - 0.15 * p_blocs * actif, hash(bloc + t));
    p = mix(p, p + (vec2(hash(bloc + t + 2.0), hash(bloc + t + 4.0)) - 0.5) * 0.1, b);
    float o = 0.01 * p_force * actif;
    vec3 c = vec3(lire(p + vec2(o, 0.0)).r, lire(p).g, lire(p - vec2(o, 0.0)).b);
    c = mix(c, vec3(hash(uv * taille + t)), 0.25 * b);
    couleur = vec4(c, 1.0);
}"""},
    # ------------------------------------------------------------------ lentille
    "lentille": {
        "description": T("Effets d'objectif : vignettage, lampe de poche, flou de bord, fish-eye.", 'Lens effects: vignette, flashlight, edge blur, fish-eye.', 'Objektiveffekte: Vignette, Taschenlampe, Randunschärfe, Fischauge.', 'Efectos de objetivo: viñeta, linterna, desenfoque de bordes, ojo de pez.', 'Effetti obiettivo: vignettatura, torcia, sfocatura ai bordi, fish-eye.'),
        "parametres": [
            {"cle": "mode", "nom": T("Genre", "Kind", "Art", "Tipo", "Tipo"), "type": "choix", "defaut": 0,
             "choix": [T("Vignettage", "Vignette", "Vignette", "Viñeta", "Vignettatura"),
                       T("Lampe de poche", "Flashlight", "Taschenlampe", "Linterna", "Torcia"),
                       T("Flou de bord", "Edge blur", "Randunschärfe", "Desenfoque de bordes", "Sfocatura ai bordi"),
                       T("Flou granuleux", "Grainy blur", "Körnige Unschärfe", "Desenfoque granulado", "Sfocatura granulosa"),
                       T("Grand angle (fish-eye)", "Fish-eye", "Fischauge", "Ojo de pez", "Fish-eye")]},
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.6, "min": 0.0, "max": 1.5},
            {"cle": "taille", "nom": T("Taille", "Size", "Größe", "Tamaño", "Dimensione"), "defaut": 0.35, "min": 0.05, "max": 1.0},
            {"cle": "mouvement", "nom": T("Mouvement", "Movement", "Bewegung", "Movimiento", "Movimento"), "defaut": 0.3, "min": 0.0, "max": 1.0},
        ],
        "ffmpeg": "vignette=PI/4",
        "glsl": """
vec3 flou(vec2 p, float r) {
    vec3 s = vec3(0.0);
    for (int i = -3; i <= 3; i++) { for (int j = -3; j <= 3; j++) { s += lire(p + vec2(float(i), float(j)) * r / taille).rgb; } }
    return s / 49.0;
}
void main() {
    int m = int(p_mode + 0.5);
    vec3 c = lire(uv).rgb;
    vec2 centre = vec2(0.5) + p_mouvement * 0.25 * vec2(sin(temps * 0.7), cos(temps * 0.53));
    float d = length((uv - centre) * vec2(taille.x / taille.y, 1.0));
    if (m == 0) { c *= 1.0 - p_force * smoothstep(p_taille * 0.8, p_taille * 0.8 + 0.6, d); }
    else if (m == 1) { c *= mix(1.0 - 0.9 * min(1.0, p_force), 1.15, smoothstep(p_taille, p_taille * 0.6, d)); }
    else if (m == 2) { c = mix(c, flou(uv, 6.0 * p_force), smoothstep(p_taille * 0.6, p_taille * 0.6 + 0.4, abs(uv.y - 0.5) * 2.0)); }
    else if (m == 3) {
        vec2 j = (vec2(hash(uv * taille + temps), hash(uv * taille - temps)) - 0.5) * 0.03 * p_force;
        c = lire(uv + j).rgb + (hash(uv * taille * 0.7 + temps) - 0.5) * 0.12 * p_force;
    } else {
        vec2 q = uv - 0.5;
        c = lire(0.5 + q * (1.0 - p_force * dot(q, q))).rgb;
        c *= 1.0 - smoothstep(0.45, 0.75, length(q) * 1.4) * p_force * 0.5;
    }
    couleur = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ ouverture et fermeture
    "ouverture": {
        "description": T("Le plan s'ouvre ou se ferme par une forme : cercle, cœur, losange, rideau…", 'The shot opens or closes through a shape: circle, heart, diamond, curtain…', 'Die Einstellung öffnet oder schließt sich durch eine Form: Kreis, Herz, Raute, Vorhang…', 'El plano se abre o se cierra con una forma: círculo, corazón, rombo, telón…', "L'inquadratura si apre o si chiude con una forma: cerchio, cuore, rombo, sipario…"),
        "parametres": [
            {"cle": "forme", "nom": T("Forme", "Shape", "Form", "Forma", "Forma"), "type": "choix", "defaut": 0,
             "choix": [T("Cercle", "Circle", "Kreis", "Círculo", "Cerchio"), T("Vertical", "Vertical", "Vertikal", "Vertical", "Verticale"),
                       T("Horizontal", "Horizontal", "Horizontal", "Horizontal", "Orizzontale"), T("Losange", "Diamond", "Raute", "Rombo", "Rombo"),
                       T("Cœur", "Heart", "Herz", "Corazón", "Cuore"), T("Rideau", "Curtain", "Vorhang", "Telón", "Sipario")]},
            {"cle": "sens", "nom": T("Quand", "When", "Wann", "Cuándo", "Quando"), "type": "choix", "defaut": 0,
             "choix": [T("S'ouvre au début", "Opens at the start", "Öffnet am Anfang", "Se abre al principio", "Si apre all'inizio"),
                       T("Se ferme à la fin", "Closes at the end", "Schließt am Ende", "Se cierra al final", "Si chiude alla fine"),
                       T("Les deux", "Both", "Beides", "Ambos", "Entrambi")]},
            {"cle": "duree", "nom": T("Durée (s)", "Duration (s)", "Dauer (s)", "Duración (s)", "Durata (s)"), "defaut": 0.8, "min": 0.1, "max": 3.0},
            {"cle": "adouci", "nom": T("Bord adouci", "Soft edge", "Weiche Kante", "Borde suave", "Bordo morbido"), "defaut": 0.02, "min": 0.0, "max": 0.3},
        ],
        "ffmpeg": "fade=t=in:st=0:d={duree}",
        "glsl": """
float forme(vec2 q, int f) {
    if (f == 0) return length(q);
    if (f == 1) return abs(q.x);
    if (f == 2) return abs(q.y);
    if (f == 3) return (abs(q.x) + abs(q.y)) * 0.75;
    if (f == 4) {
        vec2 h = vec2(q.x, -q.y) * 2.0;
        h.y -= 0.25;
        float a = atan(h.x, h.y) / 3.141593;
        float hh = abs(a);
        float dd = (13.0 * hh - 22.0 * hh * hh + 10.0 * hh * hh * hh) / (6.0 - 5.0 * hh);
        return length(h) / max(0.05, dd) * 0.5;
    }
    return 1.0 - (q.x + 0.5);
}
void main() {
    int f = int(p_forme + 0.5);
    float ar = taille.x / taille.y;
    vec2 q = (uv - 0.5) * vec2(ar, 1.0);
    if (f == 5) q = uv - 0.5;
    int s = int(p_sens + 0.5);
    float d = max(0.05, p_duree);
    float o = 1.0;
    if (s != 1) o = min(o, clamp(temps / d, 0.0, 1.0));
    if (s != 0) o = min(o, clamp((duree - temps) / d, 0.0, 1.0));
    o = o * o * (3.0 - 2.0 * o);
    float rmax = f == 0 ? length(vec2(ar * 0.5, 0.5)) : f == 1 ? ar * 0.5 : f == 2 ? 0.5 : f == 3 ? (ar * 0.5 + 0.5) * 0.75 : f == 4 ? 1.3 * ar : 1.0;
    rmax += p_adouci + 0.01;
    float masque = 1.0 - smoothstep(o * rmax - p_adouci - 0.001, o * rmax, forme(q, f));
    couleur = vec4(lire(uv).rgb * masque, 1.0);
}"""},
    # ------------------------------------------------------------------ flash et beat
    "flash": {
        "description": T('Flashs, zoom, stroboscope ou secousse calés sur un rythme (coups par seconde).', 'Flashes, zoom, strobe or shake on a beat (beats per second).', 'Blitze, Zoom, Stroboskop oder Wackeln im Takt (Schläge pro Sekunde).', 'Destellos, zoom, estroboscopio o sacudida al ritmo (golpes por segundo).', 'Flash, zoom, stroboscopio o scossa a ritmo (colpi al secondo).'),
        "parametres": [
            {"cle": "mode", "nom": T("Genre", "Kind", "Art", "Tipo", "Tipo"), "type": "choix", "defaut": 0,
             "choix": [T("Flash noir", "Black flash", "Schwarzer Blitz", "Destello negro", "Flash nero"),
                       T("Flash blanc", "White flash", "Weißer Blitz", "Destello blanco", "Flash bianco"),
                       T("Zoom pulsé", "Zoom pulse", "Zoom-Puls", "Zoom pulsado", "Zoom pulsante"),
                       T("Stroboscope", "Strobe", "Stroboskop", "Estroboscopio", "Stroboscopio"),
                       T("Secousse", "Shake", "Wackeln", "Sacudida", "Scossa")]},
            {"cle": "rythme", "nom": T("Coups par seconde", "Beats per second", "Schläge pro Sekunde", "Golpes por segundo", "Colpi al secondo"), "defaut": 2.0, "min": 0.25, "max": 6.0},
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.7, "min": 0.0, "max": 1.0},
            {"cle": "decalage", "nom": T("Décalage du temps", "Beat offset", "Taktversatz", "Desfase", "Sfasamento"), "defaut": 0.0, "min": 0.0, "max": 1.0},
        ],
        "glsl": """
void main() {
    int m = int(p_mode + 0.5);
    float ph = fract(temps * p_rythme + p_decalage);
    float coup = pow(max(0.0, 1.0 - ph * 4.0), 2.0);
    vec3 c;
    if (m == 2) { float z = 1.0 + 0.12 * p_force * coup; c = lire(0.5 + (uv - 0.5) / z).rgb + 0.15 * coup * p_force; }
    else if (m == 4) { vec2 s = vec2(sin(temps * 53.0), cos(temps * 47.0)) * 0.02 * p_force * coup; c = lire(0.5 + (uv - 0.5) * 0.96 + s).rgb; }
    else { c = lire(uv).rgb; }
    if (m == 0) c = mix(c, vec3(0.0), coup * p_force);
    if (m == 1) c = mix(c, vec3(1.0), coup * p_force);
    if (m == 3) c = mix(c, vec3(1.0) - c * 0.2, step(0.5, fract(temps * p_rythme * 2.0)) * p_force * 0.8);
    couleur = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ zoom et mouvement
    "zoom": {
        "description": T('Mouvements de caméra calculés : zoom progressif, tourbillon, flou de zoom.', 'Computed camera moves: slow zoom, swirl, zoom blur.', 'Berechnete Kamerabewegungen: langsamer Zoom, Wirbel, Zoom-Unschärfe.', 'Movimientos de cámara calculados: zoom lento, remolino, desenfoque de zoom.', 'Movimenti di camera calcolati: zoom lento, vortice, sfocatura zoom.'),
        "parametres": [
            {"cle": "mode", "nom": T("Genre", "Kind", "Art", "Tipo", "Tipo"), "type": "choix", "defaut": 0,
             "choix": [T("Zoom avant progressif", "Slow zoom in", "Langsamer Zoom hinein", "Zoom de acercamiento", "Zoom in progressivo"),
                       T("Zoom arrière progressif", "Slow zoom out", "Langsamer Zoom heraus", "Zoom de alejamiento", "Zoom out progressivo"),
                       T("Tourbillon", "Swirl", "Wirbel", "Remolino", "Vortice"),
                       T("Flou de zoom", "Zoom blur", "Zoom-Unschärfe", "Desenfoque de zoom", "Sfocatura zoom")]},
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.6, "min": 0.0, "max": 1.5},
        ],
        "glsl": """
void main() {
    int m = int(p_mode + 0.5);
    vec2 q = uv - 0.5;
    vec3 c;
    if (m == 0) { c = lire(0.5 + q / (1.0 + p_force * 0.5 * progres)).rgb; }
    else if (m == 1) { c = lire(0.5 + q / (1.0 + p_force * 0.5 * (1.0 - progres))).rgb; }
    else if (m == 2) {
        float a = p_force * 3.0 * (1.0 - progres) * smoothstep(0.6, 0.0, length(q));
        float s = sin(a); float co = cos(a);
        c = lire(0.5 + vec2(co * q.x - s * q.y, s * q.x + co * q.y)).rgb;
    } else {
        vec3 s = vec3(0.0);
        for (int i = 0; i < 12; i++) { s += lire(0.5 + q * (1.0 - float(i) * 0.012 * p_force)).rgb; }
        c = s / 12.0;
    }
    couleur = vec4(c, 1.0);
}"""},
    # ------------------------------------------------------------------ cinématique
    "cinema": {
        "description": T('Allure de film : bandes noires, bleu et orange, noir et blanc, projecteur.', 'Film look: black bars, teal and orange, black and white, projector.', 'Kinolook: schwarze Balken, Blau-Orange, Schwarzweiß, Projektor.', 'Aspecto de cine: bandas negras, azul y naranja, blanco y negro, proyector.', 'Aspetto cinema: bande nere, blu e arancio, bianco e nero, proiettore.'),
        "parametres": [
            {"cle": "mode", "nom": T("Genre", "Kind", "Art", "Tipo", "Tipo"), "type": "choix", "defaut": 0,
             "choix": [T("Bandes qui entrent", "Sliding bars", "Einfahrende Balken", "Bandas que entran", "Bande che entrano"),
                       T("Bleu-orange (teal & orange)", "Teal & orange", "Blau-Orange", "Azul y naranja", "Blu e arancio"),
                       T("Film noir et blanc", "Black & white film", "Schwarzweißfilm", "Película en blanco y negro", "Film in bianco e nero"),
                       T("Projecteur", "Projector", "Projektor", "Proyector", "Proiettore")]},
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.7, "min": 0.0, "max": 1.0},
            {"cle": "bandes", "nom": T("Bandes noires", "Black bars", "Schwarze Balken", "Bandas negras", "Bande nere"), "defaut": 0.12, "min": 0.0, "max": 0.3},
        ],
        "glsl": """
void main() {
    int m = int(p_mode + 0.5);
    vec3 c = lire(uv).rgb;
    float l = lum(c);
    if (m == 1) { vec3 g = mix(vec3(0.0, 0.45, 0.55), vec3(1.0, 0.6, 0.3), smoothstep(0.2, 0.8, l)); c = mix(c, c * 0.6 + g * l * 0.8, 0.6 * p_force); }
    if (m == 2) { c = vec3(smoothstep(0.05, 0.95, l)) + (hash(uv * taille + temps) - 0.5) * 0.06 * p_force; }
    if (m == 3) {
        c *= mix(1.0, 0.92 + 0.08 * hash(vec2(floor(temps * 24.0), 1.0)), p_force);
        c *= 1.0 - p_force * 0.5 * smoothstep(0.3, 0.75, distance(uv, vec2(0.5)));
        c += vec3(0.04, 0.03, 0.0) * p_force;
    }
    float b = p_bandes;
    if (m == 0) b *= smoothstep(0.0, 1.0, clamp(temps / 0.8, 0.0, 1.0));
    if (uv.y < b || uv.y > 1.0 - b) c = vec3(0.0);
    couleur = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ néon / contours lumineux
    "neon": {
        "description": T("Les contours de l'image s'allument comme des néons.", 'The edges of the image light up like neon tubes.', 'Die Konturen des Bildes leuchten wie Neonröhren.', 'Los contornos de la imagen se encienden como neones.', "I contorni dell'immagine si accendono come neon."),
        "parametres": [
            {"cle": "couleur", "nom": T("Couleur", "Colour", "Farbe", "Color", "Colore"), "type": "choix", "defaut": 0,
             "choix": [T("Rose", "Pink", "Rosa", "Rosa", "Rosa"), T("Bleu", "Blue", "Blau", "Azul", "Blu"), T("Vert", "Green", "Grün", "Verde", "Verde"),
                       T("Or", "Gold", "Gold", "Oro", "Oro"), T("Couleurs de l'image", "Image colours", "Bildfarben", "Colores de la imagen", "Colori dell'immagine")]},
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.8, "min": 0.1, "max": 2.0},
            {"cle": "garder", "nom": T("Image d'origine", "Original image", "Originalbild", "Imagen original", "Immagine originale"), "defaut": 0.3, "min": 0.0, "max": 1.0},
        ],
        "glsl": """
void main() {
    vec2 px = 1.0 / taille;
    float tl = lum(lire(uv + px * vec2(-1.0, -1.0)).rgb); float t = lum(lire(uv + px * vec2(0.0, -1.0)).rgb); float tr = lum(lire(uv + px * vec2(1.0, -1.0)).rgb);
    float ml = lum(lire(uv + px * vec2(-1.0, 0.0)).rgb); float mr = lum(lire(uv + px * vec2(1.0, 0.0)).rgb);
    float bl = lum(lire(uv + px * vec2(-1.0, 1.0)).rgb); float b = lum(lire(uv + px * vec2(0.0, 1.0)).rgb); float br = lum(lire(uv + px * vec2(1.0, 1.0)).rgb);
    float gx = -tl - 2.0 * ml - bl + tr + 2.0 * mr + br;
    float gy = -tl - 2.0 * t - tr + bl + 2.0 * b + br;
    float e = clamp(length(vec2(gx, gy)) * 2.0 * p_force, 0.0, 1.0);
    int k = int(p_couleur + 0.5);
    vec3 col = k == 0 ? vec3(1.0, 0.2, 0.7) : k == 1 ? vec3(0.2, 0.7, 1.0) : k == 2 ? vec3(0.3, 1.0, 0.4) : k == 3 ? vec3(1.0, 0.8, 0.3) : lire(uv).rgb * 1.5;
    float pul = 0.85 + 0.15 * sin(temps * 6.0);
    couleur = vec4(clamp(lire(uv).rgb * p_garder + col * e * pul, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ pixels et trame
    "pixels": {
        "description": T("L'image en gros pixels ou en trame de points façon bande dessinée.", 'The image in big pixels or comic-style halftone dots.', 'Das Bild in großen Pixeln oder als Comic-Rasterpunkte.', 'La imagen en píxeles grandes o en trama de puntos tipo cómic.', "L'immagine a grandi pixel o con retino a punti stile fumetto."),
        "parametres": [
            {"cle": "mode", "nom": T("Genre", "Kind", "Art", "Tipo", "Tipo"), "type": "choix", "defaut": 0,
             "choix": [T("Pixels", "Pixels", "Pixel", "Píxeles", "Pixel"), T("Trame de points", "Halftone dots", "Rasterpunkte", "Trama de puntos", "Retino a punti")]},
            {"cle": "taille", "nom": T("Taille (pixels)", "Size (pixels)", "Größe (Pixel)", "Tamaño (píxeles)", "Dimensione (pixel)"), "defaut": 24.0, "min": 2.0, "max": 120.0},
            {"cle": "animer", "nom": T("Animé", "Animated", "Animiert", "Animado", "Animato"), "type": "bool", "defaut": 0.0, "min": 0.0, "max": 1.0},
        ],
        "ffmpeg": "scale=iw/{taille}:-1:flags=neighbor,scale=iw*{taille}:-1:flags=neighbor",
        "glsl": """
void main() {
    float s = max(2.0, p_taille * (p_animer > 0.5 ? (0.6 + 0.4 * sin(temps * 3.0)) : 1.0));
    vec2 cell = s / taille;
    vec2 c0 = (floor(uv / cell) + 0.5) * cell;
    vec3 c = lire(c0).rgb;
    if (int(p_mode + 0.5) == 1) { c *= step(length((uv - c0) / cell), 0.55 * sqrt(lum(c)) + 0.05); }
    couleur = vec4(c, 1.0);
}"""},
    # ------------------------------------------------------------------ particules calculées (sans fichier)
    "particules": {
        "description": T("Particules calculées sur l'image : étoiles, lucioles, poussière dorée, neige, confettis (sans fichier à télécharger).", 'Particles computed over the image: stars, fireflies, golden dust, snow, confetti (no file to download).', 'Über dem Bild berechnete Partikel: Sterne, Glühwürmchen, Goldstaub, Schnee, Konfetti (ohne Download).', 'Partículas calculadas sobre la imagen: estrellas, luciérnagas, polvo dorado, nieve, confeti (sin descarga).', "Particelle calcolate sull'immagine: stelle, lucciole, polvere dorata, neve, coriandoli (senza download)."),
        "parametres": [
            {"cle": "genre", "nom": T("Genre", "Kind", "Art", "Tipo", "Tipo"), "type": "choix", "defaut": 0,
             "choix": [T("Étoiles scintillantes", "Twinkling stars", "Funkelnde Sterne", "Estrellas centelleantes", "Stelle scintillanti"),
                       T("Lucioles", "Fireflies", "Glühwürmchen", "Luciérnagas", "Lucciole"),
                       T("Poussière dorée", "Golden dust", "Goldstaub", "Polvo dorado", "Polvere dorata"),
                       T("Neige", "Snow", "Schnee", "Nieve", "Neve"),
                       T("Confettis", "Confetti", "Konfetti", "Confeti", "Coriandoli")]},
            {"cle": "quantite", "nom": T("Quantité", "Amount", "Menge", "Cantidad", "Quantità"), "defaut": 0.5, "min": 0.0, "max": 1.0},
            {"cle": "taille", "nom": T("Taille", "Size", "Größe", "Tamaño", "Dimensione"), "defaut": 1.0, "min": 0.3, "max": 3.0},
        ],
        "glsl": """
vec3 couche(vec2 p, float t, float k, int g) {
    float n = mix(4.0, 14.0, p_quantite) * (1.0 + k * 0.5);
    vec2 q = p * vec2(taille.x / taille.y, 1.0) * n;
    if (g == 3) q.y -= t * (1.0 + k * 0.4) * n * 0.08;
    if (g == 4) q.y -= t * (1.2 + k * 0.4) * n * 0.1;
    if (g == 1) q += vec2(sin(t * 0.5 + k), cos(t * 0.4 + k * 2.0)) * 0.6;
    if (g == 2) q.y += t * 0.015 * n;
    vec2 id = floor(q);
    vec2 f = fract(q) - 0.5;
    float h = hash(id + k * 17.0);
    vec2 o = (vec2(hash(id + 3.1 + k), hash(id + 7.7 + k)) - 0.5) * 0.7;
    if (g == 3 || g == 4) o.x += sin(t * 1.5 + h * 6.0) * 0.15;
    float d = length(f - o);
    float r = 0.07 * p_taille * (0.5 + h) * (1.0 + k * 0.3);
    float l = smoothstep(r, 0.0, d);
    if (g == 1 || g == 2) l += smoothstep(min(r * 4.0, 0.5 - length(o) * 0.7), 0.0, d) * 0.35;
    if (g == 0) {
        float tw = 0.5 + 0.5 * sin(t * (2.0 + h * 4.0) + h * 30.0);
        l += (smoothstep(0.015 * p_taille, 0.0, abs(f.x - o.x)) * smoothstep(r * 4.0, 0.0, abs(f.y - o.y))
            + smoothstep(0.015 * p_taille, 0.0, abs(f.y - o.y)) * smoothstep(r * 4.0, 0.0, abs(f.x - o.x))) * 0.7;
        l += smoothstep(r * 3.0, 0.0, d) * 0.25;
        l *= tw;
    }
    if (g == 1) l *= 0.5 + 0.5 * sin(t * 1.5 + h * 20.0);
    if (g == 4) { vec2 e = abs(f - o); l = step(e.x, r * 0.9) * step(e.y, r * 0.45); }
    vec3 col = g == 0 ? vec3(1.0, 0.97, 0.85) : g == 1 ? vec3(0.75, 1.0, 0.3) : g == 2 ? vec3(1.0, 0.8, 0.35) : g == 3 ? vec3(1.0) :
               vec3(hash(id + 1.0), hash(id + 2.0), hash(id + 3.0)) * 0.8 + 0.2;
    return col * l * step(0.55, h);
}
void main() {
    int g = int(p_genre + 0.5);
    vec3 c = lire(uv).rgb;
    vec3 a = vec3(0.0);
    for (int k = 0; k < 3; k++) { a += couche(uv, temps, float(k), g); }
    if (g == 4) c = mix(c, a, clamp(max(a.r, max(a.g, a.b)) * 3.0, 0.0, 1.0));
    else c += clamp(a, 0.0, 1.5);
    couleur = vec4(clamp(c, 0.0, 1.0), 1.0);
}"""},
    # ------------------------------------------------------------------ fuite de lumière
    "fuite": {
        "description": T("Un voile de lumière colorée traverse l'image.", 'A veil of coloured light drifts across the image.', 'Ein farbiger Lichtschleier zieht über das Bild.', 'Un velo de luz de color atraviesa la imagen.', "Un velo di luce colorata attraversa l'immagine."),
        "parametres": [
            {"cle": "couleur", "nom": T("Couleur", "Colour", "Farbe", "Color", "Colore"), "type": "choix", "defaut": 0,
             "choix": [T("Chaude", "Warm", "Warm", "Cálida", "Calda"), T("Rose", "Pink", "Rosa", "Rosa", "Rosa"), T("Bleue", "Blue", "Blau", "Azul", "Blu")]},
            {"cle": "force", "nom": P_FORCE["nom"], "defaut": 0.6, "min": 0.0, "max": 1.0},
            {"cle": "vitesse", "nom": T("Vitesse", "Speed", "Geschwindigkeit", "Velocidad", "Velocità"), "defaut": 1.0, "min": 0.2, "max": 4.0},
        ],
        "glsl": """
void main() {
    vec3 c = lire(uv).rgb;
    int k = int(p_couleur + 0.5);
    vec3 col = k == 0 ? vec3(1.0, 0.55, 0.2) : k == 1 ? vec3(1.0, 0.3, 0.6) : vec3(0.3, 0.6, 1.0);
    float t = temps * p_vitesse;
    vec2 cen = vec2(-0.2 + fract(t * 0.08) * 1.4, 0.3 + 0.2 * sin(t * 0.3));
    float l = smoothstep(0.9, 0.0, length((uv - cen) * vec2(0.7, 1.2))) * (0.6 + 0.4 * bruit(uv * 3.0 + t * 0.2));
    couleur = vec4(clamp(1.0 - (1.0 - c) * (1.0 - col * l * p_force), 0.0, 1.0), 1.0);
}"""},
}

FAMILLES = [
    {"id": "retro", "nom": T("Rétro", "Retro", "Retro", "Retro", "Retrò")},
    {"id": "glitch", "nom": T("Glitch", "Glitch", "Glitch", "Glitch", "Glitch")},
    {"id": "lentille", "nom": T("Lentille", "Lens", "Objektiv", "Lente", "Obiettivo")},
    {"id": "ouverture", "nom": T("Ouverture et fermeture", "Open and close", "Öffnen und Schließen", "Apertura y cierre", "Apertura e chiusura")},
    {"id": "cinematique", "nom": T("Cinématique", "Cinematic", "Kino", "Cinemático", "Cinematografico")},
    {"id": "motion", "nom": T("Motion et beat", "Motion and beat", "Bewegung und Beat", "Movimiento y ritmo", "Movimento e ritmo")},
    {"id": "lumieres", "nom": T("Lumières et particules", "Lights and particles", "Lichter und Partikel", "Luces y partículas", "Luci e particelle")},
]

# (id, famille, shader, nom, réglages)
VARIANTES = [
    ("gl_retro_8mm", "retro", "retro", T("Film 8 mm", "8 mm film", "8-mm-Film", "Película de 8 mm", "Pellicola 8 mm"), {}),
    ("gl_retro_super8", "retro", "retro", T("Super 8 chaud", "Warm Super 8", "Warmer Super 8", "Super 8 cálido", "Super 8 caldo"), {"chaleur": 0.7, "delave": 0.3, "grain": 0.45}),
    ("gl_retro_sepia", "retro", "retro", T("Sépia ancien", "Old sepia", "Altes Sepia", "Sepia antiguo", "Seppia antico"), {"sepia": 1.0, "delave": 0.8, "rayures": 0.6}),
    ("gl_retro_delave", "retro", "retro", T("Couleurs délavées", "Faded colours", "Verblasste Farben", "Colores desvaídos", "Colori sbiaditi"), {"delave": 0.9, "rayures": 0.0, "grain": 0.2, "tremble": 0.0}),
    ("gl_retro_raye", "retro", "retro", T("Film abîmé", "Damaged film", "Beschädigter Film", "Película dañada", "Pellicola rovinata"), {"rayures": 1.0, "grain": 0.6, "tremble": 0.7}),
    ("gl_vhs", "retro", "vhs", T("VHS", "VHS", "VHS", "VHS", "VHS"), {}),
    ("gl_vhs_abime", "retro", "vhs", T("VHS abîmée", "Worn VHS", "Abgenutzte VHS", "VHS gastada", "VHS rovinata"), {"force": 1.2, "bande": 1.0, "bavure": 1.0}),
    ("gl_camescope", "retro", "vhs", T("Caméscope (DV)", "Camcorder (DV)", "Camcorder (DV)", "Videocámara (DV)", "Videocamera (DV)"), {"force": 0.3, "bande": 0.0, "lignes": 0.3, "bavure": 0.3}),
    ("gl_rvb", "glitch", "rvb", T("Séparation RVB", "RGB split", "RGB-Trennung", "Separación RGB", "Separazione RGB"), {}),
    ("gl_rvb_pulse", "glitch", "rvb", T("RVB pulsé", "Pulsing RGB", "Pulsierendes RGB", "RGB pulsado", "RGB pulsante"), {"force": 1.2, "rythme": 2.0}),
    ("gl_rvb_vertical", "glitch", "rvb", T("RVB vertical", "Vertical RGB", "Vertikales RGB", "RGB vertical", "RGB verticale"), {"angle": 90.0}),
    ("gl_glitch_bandes", "glitch", "glitch", T("Glitch bandes", "Glitch bands", "Glitch-Streifen", "Glitch de bandas", "Glitch a bande"), {"blocs": 0.0}),
    ("gl_glitch_blocs", "glitch", "glitch", T("Glitch blocs", "Glitch blocks", "Glitch-Blöcke", "Glitch de bloques", "Glitch a blocchi"), {"blocs": 1.0, "force": 0.4}),
    ("gl_glitch_fort", "glitch", "glitch", T("Glitch fort", "Heavy glitch", "Starker Glitch", "Glitch fuerte", "Glitch forte"), {"force": 1.3, "frequence": 0.9, "blocs": 0.8}),
    ("gl_vignette", "lentille", "lentille", T("Vignettage doux", "Soft vignette", "Weiche Vignette", "Viñeta suave", "Vignettatura morbida"), {"mode": 0, "mouvement": 0.0}),
    ("gl_lampe", "lentille", "lentille", T("Lampe de poche", "Flashlight", "Taschenlampe", "Linterna", "Torcia"), {"mode": 1, "mouvement": 0.5}),
    ("gl_flou_bord", "lentille", "lentille", T("Flou de bord (maquette)", "Edge blur (miniature)", "Randunschärfe (Miniatur)", "Desenfoque de bordes (maqueta)", "Sfocatura ai bordi (miniatura)"), {"mode": 2, "taille": 0.5}),
    ("gl_flou_granuleux", "lentille", "lentille", T("Flou granuleux", "Grainy blur", "Körnige Unschärfe", "Desenfoque granulado", "Sfocatura granulosa"), {"mode": 3}),
    ("gl_fisheye", "lentille", "lentille", T("Grand angle (fish-eye)", "Fish-eye", "Fischauge", "Ojo de pez", "Fish-eye"), {"mode": 4, "force": 0.8}),
    ("gl_ouvrir_cercle", "ouverture", "ouverture", T("Cercle qui s'ouvre", "Circle open", "Kreis öffnet", "Círculo que se abre", "Cerchio che si apre"), {"forme": 0, "sens": 0}),
    ("gl_fermer_cercle", "ouverture", "ouverture", T("Cercle qui se ferme", "Circle close", "Kreis schließt", "Círculo que se cierra", "Cerchio che si chiude"), {"forme": 0, "sens": 1}),
    ("gl_ouvrir_vertical", "ouverture", "ouverture", T("Ouverture verticale", "Vertical open", "Vertikal öffnen", "Apertura vertical", "Apertura verticale"), {"forme": 1, "sens": 0}),
    ("gl_ouvrir_horizontal", "ouverture", "ouverture", T("Ouverture horizontale", "Horizontal open", "Horizontal öffnen", "Apertura horizontal", "Apertura orizzontale"), {"forme": 2, "sens": 0}),
    ("gl_ouvrir_losange", "ouverture", "ouverture", T("Losange", "Diamond", "Raute", "Rombo", "Rombo"), {"forme": 3, "sens": 2}),
    ("gl_ouvrir_coeur", "ouverture", "ouverture", T("Cœur qui s'ouvre", "Heart open", "Herz öffnet", "Corazón que se abre", "Cuore che si apre"), {"forme": 4, "sens": 0, "duree": 1.2}),
    ("gl_rideau", "ouverture", "ouverture", T("Rideau", "Curtain", "Vorhang", "Telón", "Sipario"), {"forme": 5, "sens": 0, "adouci": 0.05}),
    ("gl_bandes_cinema", "cinematique", "cinema", T("Bandes cinéma qui entrent", "Sliding cinema bars", "Einfahrende Kinobalken", "Bandas de cine que entran", "Bande cinema che entrano"), {"mode": 0}),
    ("gl_teal_orange", "cinematique", "cinema", T("Bleu et orange (blockbuster)", "Teal & orange (blockbuster)", "Blau-Orange (Blockbuster)", "Azul y naranja (taquillazo)", "Blu e arancio (blockbuster)"), {"mode": 1, "bandes": 0.0}),
    ("gl_film_nb", "cinematique", "cinema", T("Film noir et blanc", "Black & white film", "Schwarzweißfilm", "Película en blanco y negro", "Film in bianco e nero"), {"mode": 2, "bandes": 0.1}),
    ("gl_projecteur", "cinematique", "cinema", T("Projecteur", "Projector", "Projektor", "Proyector", "Proiettore"), {"mode": 3, "bandes": 0.0}),
    ("gl_flash_noir", "motion", "flash", T("Flash noir au rythme", "Black flash on the beat", "Schwarzer Blitz im Takt", "Destello negro al ritmo", "Flash nero a ritmo"), {"mode": 0}),
    ("gl_flash_blanc", "motion", "flash", T("Flash blanc au rythme", "White flash on the beat", "Weißer Blitz im Takt", "Destello blanco al ritmo", "Flash bianco a ritmo"), {"mode": 1}),
    ("gl_zoom_pulse", "motion", "flash", T("Zoom pulsé (beat)", "Zoom pulse (beat)", "Zoom-Puls (Beat)", "Zoom pulsado (ritmo)", "Zoom pulsante (ritmo)"), {"mode": 2}),
    ("gl_strobe", "motion", "flash", T("Stroboscope", "Strobe", "Stroboskop", "Estroboscopio", "Stroboscopio"), {"mode": 3, "rythme": 4.0, "force": 0.5}),
    ("gl_secousse", "motion", "flash", T("Secousse au rythme", "Shake on the beat", "Wackeln im Takt", "Sacudida al ritmo", "Scossa a ritmo"), {"mode": 4}),
    ("gl_zoom_avant", "motion", "zoom", T("Zoom avant progressif", "Slow zoom in", "Langsamer Zoom hinein", "Zoom de acercamiento", "Zoom in progressivo"), {"mode": 0}),
    ("gl_zoom_arriere", "motion", "zoom", T("Zoom arrière progressif", "Slow zoom out", "Langsamer Zoom heraus", "Zoom de alejamiento", "Zoom out progressivo"), {"mode": 1}),
    ("gl_tourbillon", "motion", "zoom", T("Tourbillon d'entrée", "Swirl in", "Wirbel hinein", "Remolino de entrada", "Vortice d'ingresso"), {"mode": 2}),
    ("gl_flou_zoom", "motion", "zoom", T("Flou de zoom", "Zoom blur", "Zoom-Unschärfe", "Desenfoque de zoom", "Sfocatura zoom"), {"mode": 3}),
    ("gl_neon_rose", "glitch", "neon", T("Néon rose", "Pink neon", "Rosa Neon", "Neón rosa", "Neon rosa"), {"couleur": 0}),
    ("gl_neon_bleu", "glitch", "neon", T("Néon bleu", "Blue neon", "Blaues Neon", "Neón azul", "Neon blu"), {"couleur": 1}),
    ("gl_contours", "glitch", "neon", T("Contours lumineux", "Glowing edges", "Leuchtende Kanten", "Contornos luminosos", "Contorni luminosi"), {"couleur": 4, "garder": 0.0}),
    ("gl_pixels", "glitch", "pixels", T("Pixels", "Pixels", "Pixel", "Píxeles", "Pixel"), {}),
    ("gl_trame", "glitch", "pixels", T("Trame de points (BD)", "Halftone (comic)", "Rasterpunkte (Comic)", "Trama (cómic)", "Retino (fumetto)"), {"mode": 1, "taille": 12.0}),
    ("gl_etoiles", "lumieres", "particules", T("Étoiles scintillantes", "Twinkling stars", "Funkelnde Sterne", "Estrellas centelleantes", "Stelle scintillanti"), {"genre": 0}),
    ("gl_lucioles", "lumieres", "particules", T("Lucioles", "Fireflies", "Glühwürmchen", "Luciérnagas", "Lucciole"), {"genre": 1}),
    ("gl_poussiere", "lumieres", "particules", T("Poussière dorée", "Golden dust", "Goldstaub", "Polvo dorado", "Polvere dorata"), {"genre": 2, "taille": 0.7}),
    ("gl_neige", "lumieres", "particules", T("Neige", "Snow", "Schnee", "Nieve", "Neve"), {"genre": 3}),
    ("gl_confettis", "lumieres", "particules", T("Confettis", "Confetti", "Konfetti", "Confeti", "Coriandoli"), {"genre": 4, "quantite": 0.6}),
    ("gl_fuite_chaude", "lumieres", "fuite", T("Fuite de lumière chaude", "Warm light leak", "Warmes Lichtleck", "Fuga de luz cálida", "Fuga di luce calda"), {"couleur": 0}),
    ("gl_fuite_rose", "lumieres", "fuite", T("Fuite de lumière rose", "Pink light leak", "Rosa Lichtleck", "Fuga de luz rosa", "Fuga di luce rosa"), {"couleur": 1}),
]


def main():
    effets = [{"id": i, "famille": f, "shader": s, "nom": n, "reglages": r} for i, f, s, n, r in VARIANTES]
    for s in SHADERS.values():
        for p in s["parametres"]:
            p.setdefault("type", "float")
    d = {"version": 1, "note": "Shaders GLSL communs PC (OpenGL 3.3) et Android (OpenGL ES 3.0) ; voir app/moteur_gl.py",
         "familles": FAMILLES, "shaders": SHADERS, "effets": effets}
    chemin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue", "effets_gl.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(chemin, len(effets), "effets,", len(SHADERS), "shaders")


if __name__ == "__main__":
    main()
