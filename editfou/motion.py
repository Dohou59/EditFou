"""Scène FilmCraft : séquence 1080×1920 où l'on pose l'A-roll, des graphiques natifs (formes, tracés, textes,
images clés) et des sons, par le canal de contrôle. Tout reste modifiable dans FilmCraft.

Pistes vidéo : 0 = A-roll (V1) ; chaque graphique prend la première piste libre au-dessus (ou au-dessus d'un
autre graphique avec `dessus`). Pistes audio : A1 = voix, A2 = musique, A3… = bruitages (allouées pareil).
Les temps sont en secondes du montage, arrondis à l'image (30 i/s). Les animations partent vif et arrivent en
douceur (easeIn, influence 0,9 sur l'image clé d'arrivée).
"""
import math

from . import filmcraft as fc
from .filmcraft import cmd, T, F, FPS
from .sons import catalogue

CALQUE = 3                # index d'effet du calque 0 d'un graphique (après motion, opacity, time_remap)
BLANC, ROUGE, GRIS, FOND = '#F2F2F2', '#E0202A', '#8A8A8A', '#0B0B0B'
# famille, style FilmCraft, hauteur du centre optique au-dessus de la ligne de base (en corps)
POLICES = {'inter': ('Inter 24pt', 'Black', 0.364), 'bebas': ('Bebas Neue', 'Regular', 0.35),
           'play': ('Playfair Display', 'Italic', 0.30)}


class Erreur(Exception):
    pass


def im(t):
    """Temps (s) → numéro d'image."""
    return int(round(t * FPS))


def db(v):
    return round(20 * math.log10(v), 2) if v > 1e-4 else -60.0


class Scene:
    def __init__(self, nom, duree, pistes=48, audio=8, W=1080, H=1920):
        cmd('file.newProject', {'name': nom})
        cmd('file.newSequence', {'name': nom, 'width': W, 'height': H, 'fps': FPS, 'video': pistes, 'audio': audio})
        self.W, self.H, self.duree = W, H, duree
        self.occupe = [[] for _ in range(pistes)]
        self.occupe_audio = [[] for _ in range(audio)]
        self.piste_de, self.debut, self.fin, self.items = {}, {}, {}, {}
        self.sons = catalogue()
        self.manquants = set()

    # ------------------------------------------------------------------ pistes
    def piste(self, i0, i1, mini=1):
        for k in range(mini, len(self.occupe)):
            if all(b <= i0 or a >= i1 for a, b in self.occupe[k]):
                self.occupe[k].append((i0, i1))
                return k
        raise Erreur('aucune piste vidéo libre entre les images %d et %d' % (i0, i1))

    def piste_audio(self, i0, i1, mini=2):
        for k in range(mini, len(self.occupe_audio)):
            if all(b <= i0 or a >= i1 for a, b in self.occupe_audio[k]):
                self.occupe_audio[k].append((i0, i1))
                return 'A%d' % (k + 1)
        return None

    def _graphique(self, commande, params, t0, t1, dessus=None, piste=None):
        i0, i1 = im(max(0.0, t0)), im(min(t1, self.duree))
        if i1 <= i0:
            i1 = i0 + 1
        if piste is not None:
            k = piste
            self.occupe[k].append((i0, i1))
        else:
            k = self.piste(i0, i1, self.piste_de[dessus] + 1 if dessus else 1)
        p = dict(params, seconds=(i1 - i0) / FPS, time=i0 * F, track=k)
        c = cmd(commande, p)['clip']
        self.piste_de[c], self.debut[c], self.fin[c] = k, i0, i1
        return c

    # ------------------------------------------------------------------ propriétés et images clés
    def regle(self, c, calque=0, **props):
        cmd('graphics.set', {'clip': c, 'layer': calque, 'props': props})

    def cles(self, c, cles, lisse=True, maintien=False):
        """cles : [(t, {propriété: valeur})]. `maintien` : valeurs tenues jusqu'à la clé suivante.
        Les clés hors du clip (insert plus court que son animation) sont ignorées : FilmCraft les refuse."""
        cles = [(t, props) for t, props in cles if self.debut[c] <= im(t) < self.fin[c]]
        for t, props in cles:
            cmd('graphics.set', {'clip': c, 'layer': 0, 'props': props, 'time': im(t) * F, 'keyframe': True})
        vus = set()
        for t, props in cles:
            mt = (im(t) - self.debut[c]) * F
            for p in props:
                base = {'clip': c, 'effect': CALQUE, 'param': p, 'mediaTime': mt}
                if maintien:
                    cmd('effects.setInterpolation', dict(base, interpolation='hold'))
                elif lisse and p in vus:
                    cmd('effects.setInterpolation', dict(base, interpolation='easeIn'))
                    cmd('effects.setKeyframe', dict(base, inInfluence=0.9))
                vus.add(p)

    def opacite(self, c, cles):
        """Images clés d'opacité du clip (effet Opacité, temps du montage)."""
        for t, v in cles:
            if c in self.fin and not self.debut[c] <= im(t) < self.fin[c]:
                continue
            cmd('effects.setParam', {'clip': c, 'effect': 'opacity', 'param': 'opacity', 'value': v,
                                     'keyframe': True, 'time': im(t) * F})

    def entree(self, c, t, x, y, style, duree=None, opacite=100):
        f = 1 / FPS
        if style == 'pop':
            self.cles(c, [(t, {'scale': 0, 'opacity': 0}), (t + 2 * f, {'opacity': opacite}),
                          (t + 5 * f, {'scale': 112}), (t + 9 * f, {'scale': 100})])
        elif style == 'tampon':
            self.cles(c, [(t, {'scale': 230, 'opacity': 0}), (t + 2 * f, {'opacity': opacite}),
                          (t + 5 * f, {'scale': 100})])
        elif style in ('monte', 'descend', 'gauche', 'droite'):
            dx, dy = {'monte': (0, 70), 'descend': (0, -70), 'gauche': (-260, 0), 'droite': (260, 0)}[style]
            self.cles(c, [(t, {'position': [x + dx, y + dy], 'opacity': 0}), (t + 5 * f, {'opacity': opacite}),
                          (t + (duree or 9) * f, {'position': [x, y]})])
        elif style == 'fondu':
            self.cles(c, [(t, {'opacity': 0}), (t + (duree or 8) * f, {'opacity': opacite})])
        elif style == 'tombe':
            self.cles(c, [(t, {'position': [x, -300]}), (t + (duree or 10) * f, {'position': [x, y]})])
        elif style == 'apparait':
            self.cles(c, [(t - f, {'opacity': 0}), (t, {'opacity': opacite})], lisse=False)
        elif style:
            raise Erreur('entrée inconnue : %s' % style)

    def secousse(self, c, t, x, y, amplitude=18, images=7):
        pas = [(1, -0.6), (-0.9, 0.7), (0.7, -0.4), (-0.5, 0.5), (0.3, -0.2), (-0.15, 0.1)]
        cles = [(t, {'position': [x, y]})]
        for i in range(1, images):
            ex, ey = pas[(i - 1) % len(pas)]
            cles.append((t + i / FPS, {'position': [x + ex * amplitude, y + ey * amplitude]}))
        cles.append((t + images / FPS, {'position': [x, y]}))
        self.cles(c, cles, lisse=False)

    # ------------------------------------------------------------------ éléments graphiques
    def texte(self, t0, t1, s, x, y, police='inter', taille=120, couleur=BLANC, entree=None, t=None, rot=0,
              tracking=0, dessus=None, piste=None):
        """Texte centré sur (x, y) : le point d'ancrage est le centre optique de la ligne."""
        famille, style, k = POLICES[police]
        c = self._graphique('graphics.newText', {'text': s, 'size': taille, 'position': [x, y]}, t0, t1, dessus, piste)
        self.regle(c, font=famille, font_style=style, size=taille, align='center', fill_color=couleur,
                   tracking=tracking, anchor=[0, -k * taille], position=[x, y], rotation=rot)
        if entree:
            self.entree(c, t0 if t is None else t, x, y, entree)
        return c

    def mot(self, t0, t1, s, x, base, taille, couleur, police='inter', piste=None):
        """Mot posé sur sa ligne de base (texte mot par mot)."""
        famille, style, _ = POLICES[police]
        c = self._graphique('graphics.newText', {'text': s, 'size': taille, 'position': [x, base]}, t0, t1, None, piste)
        self.regle(c, font=famille, font_style=style, size=round(taille, 2), align='center', fill_color=couleur,
                   position=[round(x, 2), round(base, 2)])
        return c

    def _forme(self, commande, params, t0, t1, x, y, couleur, contour, epaisseur, rot, opacite, entree, t,
               dessus, piste, **autres):
        c = self._graphique(commande, params, t0, t1, dessus, piste)
        props = dict(position=[x, y], rotation=rot, opacity=opacite, **autres)
        if couleur:
            props['fill_color'] = couleur
        else:
            props['fill'] = False
        if contour:
            props.update(stroke=True, stroke_color=contour, stroke_width=epaisseur, stroke_type=1)
        self.regle(c, **props)
        if entree:
            self.entree(c, t0 if t is None else t, x, y, entree, opacite=opacite)
        return c

    def rect(self, t0, t1, x, y, w, h, couleur=BLANC, rayon=0, contour=None, epaisseur=6, rot=0, opacite=100,
             entree=None, t=None, dessus=None, piste=None):
        return self._forme('graphics.newRectangle', {'position': [x, y], 'size': [w, h]}, t0, t1, x, y, couleur,
                           contour, epaisseur, rot, opacite, entree, t, dessus, piste, size=[w, h], corner_radius=rayon)

    def ellipse(self, t0, t1, x, y, w, h, couleur=BLANC, contour=None, epaisseur=6, rot=0, opacite=100,
                entree=None, t=None, dessus=None, piste=None):
        return self._forme('graphics.newEllipse', {'position': [x, y], 'size': [w, h]}, t0, t1, x, y, couleur,
                           contour, epaisseur, rot, opacite, entree, t, dessus, piste, size=[w, h])

    def trace(self, t0, t1, points, couleur=BLANC, epaisseur=8, opacite=100, dessus=None, piste=None):
        """Tracé ouvert de gauche à droite, prolongé jusqu'aux bords. FilmCraft ferme toujours ses tracés et les
        traits superposés s'annulent : le retour passe donc sous l'image, hors cadre."""
        ya, yb = points[0][1], points[-1][1]
        bas = self.H + 400
        points = [[-150, ya]] + points + [[self.W + 150, yb], [self.W + 150, bas], [-150, bas]]
        c = self._graphique('graphics.newShape', {'shape': 'path', 'points': points}, t0, t1, dessus, piste)
        self.regle(c, position=[0, 0], fill=False, stroke=True, stroke_color=couleur, stroke_width=epaisseur,
                   stroke_type=1, opacity=opacite)
        return c

    def barre(self, t0, t1, xg, y, w, h, couleur=ROUGE, t=None, duree=8, rot=0, dessus=None, piste=None):
        """Barre qui pousse depuis son bord gauche xg."""
        c = self.rect(t0, t1, xg + w / 2, y, w, h, couleur, rot=rot, dessus=dessus, piste=piste)
        t = t0 if t is None else t
        self.cles(c, [(t, {'size': [0.5, h], 'position': [xg, y]}),
                      (t + duree / FPS, {'size': [w, h], 'position': [xg + w / 2, y]})])
        return c

    def revele(self, c, cles, angle=270):
        """Balayage linéaire : cles [(t, % visible)] ; angle 270 = révèle de gauche à droite."""
        cmd('effects.apply', {'clips': [c], 'effect': 'linear_wipe_legacy'})
        cmd('effects.setParam', {'clip': c, 'effect': 'linear_wipe_legacy', 'param': 'angle', 'value': angle})
        for t, visible in cles:
            if c in self.fin and not self.debut[c] <= im(t) < self.fin[c]:
                continue
            cmd('effects.setParam', {'clip': c, 'effect': 'linear_wipe_legacy', 'param': 'completion',
                                     'value': 100 - visible, 'keyframe': True, 'time': im(t) * F})

    def fond(self, t0, t1, pas=90, couleur=FOND, ligne='#1A1A1A', grille=True):
        """Fond noir plein cadre (à grille : un seul graphique, une couche par trait) sur la première piste libre."""
        c = self._graphique('graphics.newRectangle', {'position': [self.W / 2, self.H / 2], 'size': [self.W, self.H]},
                            t0, t1)
        self.regle(c, size=[self.W, self.H], position=[self.W / 2, self.H / 2], fill_color=couleur)
        if grille:
            n = 1
            for x in range(pas // 2, self.W, pas):
                cmd('graphics.newRectangle', {'clip': c, 'position': [x, self.H / 2], 'size': [2, self.H]})
                self.regle(c, n, fill_color=ligne, size=[2, self.H], position=[x, self.H / 2])
                n += 1
            for y in range(pas // 2 + 30, self.H, pas):
                cmd('graphics.newRectangle', {'clip': c, 'position': [self.W / 2, y], 'size': [self.W, 2]})
                self.regle(c, n, fill_color=ligne, size=[self.W, 2], position=[self.W / 2, y])
                n += 1
        return c

    # ------------------------------------------------------------------ médias et sons
    def item(self, chemin):
        if chemin not in self.items:
            r = cmd('file.import', {'paths': [chemin]})
            if r.get('errors') or not r.get('items'):
                raise Erreur('import impossible : %s %s' % (chemin, r.get('errors')))
            self.items[chemin] = r['items'][0]
        return self.items[chemin]

    def place_audio(self, chemin, debut, source, duree, piste=None, niveau=0.0, fondus=None):
        debut = max(0.0, debut)
        duree = min(duree, self.duree - debut)
        if duree < 0.05:
            return None
        i0, i1 = im(debut), im(debut + duree)
        piste = piste or self.piste_audio(i0, i1)
        if piste is None:
            return None
        r = cmd('timeline.place', {'item': self.item(chemin), 'track': piste, 'time': i0 * F,
                                   'sourceIn': round(source * T), 'duration': (i1 - i0) * F, 'video': False})
        clip = (r.get('clips') or [None])[0]
        if clip is None:
            return None
        if fondus:
            for tt, v in fondus:
                cmd('effects.setParam', {'clip': clip, 'effect': 'volume', 'param': 'level', 'value': v,
                                         'keyframe': True, 'time': min(max(im(tt), i0), i1 - 1) * F})
        elif niveau:
            cmd('effects.setParam', {'clip': clip, 'effect': 'volume', 'param': 'level', 'value': niveau})
        return clip

    def son(self, role, t, niveau=-7.0, duree=None, avant=None):
        """Bruitage `role` posé pour que son pic tombe à t. `avant` : ne garder que ce qui précède le pic de
        `avant` secondes (tic-tac qui s'arrête net sur le mot, riser qui culmine sur le chiffre)."""
        s = self.sons.get(role)
        if not s:
            self.manquants.add(role)
            return None
        fin_son = s['duree'] - 0.03
        if avant is not None:
            src = max(0.0, s['pic'] - avant)
            debut = t - (s['pic'] - src)
        else:
            src, debut = 0.0, t - s['pic']
        if debut < 0:
            src, debut = src - debut, 0.0
        d = min(duree or fin_son - src, fin_son - src)
        return self.place_audio(s['fichier'], debut, src, d, niveau=niveau)

    def enregistrer(self, chemin):
        cmd('file.saveAs', {'path': chemin})
