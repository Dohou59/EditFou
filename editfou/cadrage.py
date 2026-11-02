"""Recadrage 9:16 d'une source plus large, plan par plan, sur le visage (recette ClaudeCut « Edgar »).

Les échelles sont exprimées comme dans CapCut (relatives à l'image ajustée au canevas : 3,1605 remplit le 9:16
avec du 16:9), les positions en fractions du demi-canevas, y vers le haut ; `motion_filmcraft` les convertit
en Motion ▸ Échelle (%) et Position (px) FilmCraft — conversion validée au portage d'Edgar.
"""
from collections import namedtuple

W, H = 1080, 1920
Zone = namedtuple('Zone', 'debut fin fx fy s taille large')


class Cadreur:
    def __init__(self, analyse):
        self.sw, self.sh = analyse['largeur'], analyse['hauteur']
        self.plans = analyse['plans']
        self.plein = max(1.0, round(H / (W * self.sh / self.sw), 4))
        self.large = round(self.plein * 1.2656, 2)
        self.zones = []

    def auto(self, seuil=0.1, taille_large=0.075):
        """Une zone par plan : visage ≥ seuil (fraction de la largeur) → plan serré centré sur lui ;
        sinon plan large resserré."""
        for pl in self.plans:
            if pl['taille_visage'] < seuil:
                self.zone(pl['debut'], pl['fin'], pl['x_visage'], pl['y_visage'], large=True, taille=taille_large)
            else:
                self.zone(pl['debut'], pl['fin'], pl['x_visage'], pl['y_visage'], taille=pl['taille_visage'])
        return self

    def zone(self, debut, fin, fx, fy, large=False, s=None, taille=None):
        """Ajoute (ou remplace sur [debut, fin[) le cadrage centré sur (fx, fy), fractions de l'image source."""
        s = s or (self.large if large else self.plein)
        taille = taille if taille is not None else (0.075 if large else 0.2)
        gardees = []
        for z in self.zones:
            if z.fin <= debut or z.debut >= fin:
                gardees.append(z)
                continue
            if z.debut < debut:
                gardees.append(z._replace(fin=debut))
            if z.fin > fin:
                gardees.append(z._replace(debut=fin))
        self.zones = sorted(gardees + [Zone(debut, fin, fx, fy, s, taille, large)])
        return self

    def cadrage(self, fx, fy, s):
        """Position X/Y (fraction du demi-canevas) qui centre le visage, sans laisser voir de bord."""
        hv = W * self.sh / self.sw * s
        tx = max(-(s - 1), min(s - 1, -(fx - 0.5) * 2 * s))
        lim = max(0.0, (hv - H) / H)
        ty = max(-lim, min(lim, (0.5 - fy) * (H - hv) / (H / 2)))
        return round(tx, 4), round(ty, 4)

    def decouper(self, plages, zoom=1.0):
        """Morceaux (a, b, zone) : chaque plage coupée aux changements de plan."""
        out = []
        for a, b in plages:
            for z in self.zones:
                x0, x1 = max(a, z.debut), min(b, z.fin)
                if x1 - x0 >= 0.12:
                    out.append((x0, x1, z._replace(s=z.s * zoom) if zoom != 1 else z))
        return out

    def visage(self, ts):
        for z in self.zones:
            if z.debut <= ts < z.fin:
                return z.fx, z.fy, z.taille
        return 0.5, 0.33, 0.2

    def menton(self, ts, s, tx, ty):
        """Hauteur (px, canevas 1080×1920) du menton à l'écran pour ce cadrage."""
        fx, fy, tv = self.visage(ts)
        k = W / self.sw * s
        return H / 2 - ty * H / 2 + (fy * self.sh - self.sh / 2) * k + 0.6 * tv * self.sw * k

    def x_visage(self, ts, s, tx):
        return W / 2 + tx * W / 2 + (self.visage(ts)[0] - 0.5) * W * s

    def chronologie(self, morceaux, t=0.0, punch=(1.22, 1.12), punch_large=(1.12,), menton_max=1360):
        """[(début montage, début source, fin source, échelle, x, y)]. Deux cadrages en alternance à chaque coupe
        dans un même plan (×1,22 serré, ×1,12 large), moins si le menton descendait trop bas pour le texte."""
        prec, alt, tl = None, False, []
        for a, b, z in morceaux:
            cle = (z.fx, z.fy, z.s)
            alt = (not alt) if cle == prec else False
            prec = cle
            s2 = z.s
            if alt:
                for f in (punch_large if z.large else punch):
                    if self.menton(a, z.s * f, *self.cadrage(z.fx, z.fy, z.s * f)) <= menton_max:
                        s2 = z.s * f
                        break
            tx, ty = self.cadrage(z.fx, z.fy, s2)
            tl.append((round(t, 3), a, b, s2, tx, ty))
            t += b - a
        return tl, t

    def motion_filmcraft(self, s, tx, ty):
        """(échelle %, [x, y] px) FilmCraft pour un cadrage (s, tx, ty)."""
        fit = min(W / self.sw, H / self.sh)
        return round(fit * s * 100, 3), [round(W / 2 + tx * W / 2, 2), round(H / 2 - ty * H / 2, 2)]


def temps_montage(TL, decalage=0.0):
    """Fonction temps de la source → temps du montage (une coupe renvoie au morceau suivant)."""
    fin = decalage + TL[-1][0] + TL[-1][2] - TL[-1][1]

    def T(ts):
        for o, a, b, *_ in TL:
            if ts < a:
                return round(decalage + o, 3)
            if ts <= b:
                return round(decalage + o + ts - a, 3)
        return round(fin, 3)
    return T
