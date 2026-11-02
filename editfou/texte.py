"""Mise en page du texte « mot par mot » : un bloc compact à hauteur de poitrine, trois tailles (petits mots de
liaison / MOT-CLÉ en majuscules / suite en petit), lignes alignées à gauche sur un même bord.
Tailles en px de corps de police sur un canevas 1080×1920 (petite 50 px, grande 100 px : tailles 10 et 20 de
CapCut, recette Edgar). Inter Black : capitales = 0,727 corps.
"""
from PIL import ImageFont

from .config import police

W, H = 1080, 1920
CAPITALE = 0.727         # hauteur des capitales d'Inter, en corps
_polices = {}


def largeur(nom, texte, corps):
    """Largeur (px) d'un texte dans la police incluse `nom` (inter, bebas, play) à ce corps."""
    if nom not in _polices:
        _polices[nom] = ImageFont.truetype(police(nom), 100)
    return _polices[nom].getlength(texte) / 100 * corps


def composer(mots, i_cle, petite=50.0, grande=100.0, largeur_max=860, espace=0.24, nom='inter'):
    """mots : textes du bloc ; i_cle : indice du mot-clé (ou None). Renvoie les lignes
    [(corps, [(index_mot, texte_affiché, largeur_px)], est_cle)]."""
    def petites(idx):
        lignes, cur, l = [], [], 0.0
        for i in idx:
            w = largeur(nom, mots[i], petite)
            e = espace * petite if cur else 0
            if cur and l + e + w > largeur_max:
                lignes.append((petite, cur, False)); cur, l, e = [], 0.0, 0
            cur.append((i, mots[i], w)); l += e + w
        if cur:
            lignes.append((petite, cur, False))
        return lignes
    if i_cle is None:
        return petites(range(len(mots)))
    cle = mots[i_cle].upper()
    t = min(grande, grande * largeur_max / max(1.0, largeur(nom, cle, grande)))
    return petites(range(i_cle)) + [(t, [(i_cle, cle, largeur(nom, cle, t))], True)] + \
        petites(range(i_cle + 1, len(mots)))


def placer(lignes, haut, centre_x=W / 2, espace=0.24):
    """[(index_mot, texte, corps, x_centre, y_ligne_de_base, est_cle)] + boîte du bloc (px).
    Bloc centré sur centre_x, empilement serré à partir de `haut`."""
    def lg(l):
        t, ws, _ = l
        return sum(w for _, _, w in ws) + espace * t * (len(ws) - 1)
    larg = max(lg(l) for l in lignes)
    gauche = min(max(centre_x - larg / 2, 50), W - 50 - larg)
    out, y = [], haut
    for t, ws, cle in lignes:
        base = y + CAPITALE * t
        x = gauche
        for i, txt, w in ws:
            out.append((i, txt, t, x + w / 2, base, cle))
            x += w + espace * t
        # petits mots en minuscules : on garde la place des jambages avant la ligne suivante
        y += CAPITALE * t + (0.16 if cle else 0.30) * t
    return out, (gauche, haut, gauche + larg, y)
