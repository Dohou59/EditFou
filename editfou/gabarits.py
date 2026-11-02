"""Bibliothèque de motions natifs FilmCraft, choisis et réglés par le storyboard.

Deux familles :
- INSERTS plein écran (fond noir à grille, charte Edgar) : ils cachent l'A-roll pendant une phrase, la voix continue ;
- SURIMPRESSIONS posées sur l'A-roll, petites, hors du visage (pastille de chapitre, compteur ×1 → ×2).

Chaque gabarit reçoit la scène, son début et sa fin (temps du montage), ses paramètres et ses déclencheurs
(instants des mots, temps du montage). Chaque événement graphique a son bruitage, pic calé sur l'image.
`python -m editfou gabarits` imprime ce catalogue pour l'IA qui écrit le storyboard.
"""
import math

from .motion import BLANC, ROUGE, GRIS, FPS
from .texte import largeur

f = 1 / FPS
CX, CY = 540, 960


def ajuste(texte, police, taille, largeur_max=940):
    """Corps qui fait tenir `texte` dans largeur_max px."""
    return round(min(taille, taille * largeur_max / max(1.0, largeur(police, texte, taille))), 1)


def nombre(v):
    if abs(v - round(v)) < 1e-6:
        return '{:,}'.format(int(round(v))).replace(',', ' ')
    return ('%.1f' % v).replace('.', ',')


def _phrase(s, a, b, bg, p, y=560):
    if p.get('phrase'):
        s.texte(a, b, p['phrase'], CX, y, 'play', ajuste(p['phrase'], 'play', 92), GRIS, entree='fondu',
                t=a + 0.03, dessus=bg)


def _borne(t, a, b):
    return max(a, min(t, b - 3 * f))


# ------------------------------------------------------------------ inserts plein écran
def mot_choc(s, a, b, p, d):
    impact = _borne(d['impact'], a, b)
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 720)
    rouge = p.get('couleur', 'rouge') != 'blanc'
    taille = ajuste(p['texte'], 'inter', 190)
    c = s.texte(a, b, p['texte'], CX, CY, 'inter', taille, ROUGE if rouge else BLANC, entree='tampon', t=impact,
                dessus=bg)
    s.secousse(c, impact + 5 * f, CX, CY, 14, 6)
    w = largeur('inter', p['texte'], taille)
    tb = impact + 0.18
    if tb < b - 0.2:
        s.barre(a, b, CX - w / 2, CY + 0.42 * taille + 40, w, 14, BLANC if rouge else ROUGE, t=tb, duree=6, dessus=bg)
        s.son('clic', tb, -12)
    if p.get('sous_texte') and impact + 0.3 < b - 0.2:
        s.texte(a, b, p['sous_texte'], CX, 1260, 'play', ajuste(p['sous_texte'], 'play', 84), BLANC, entree='monte',
                t=impact + 0.3, dessus=bg)
    s.son('woosh', a, -9)
    s.son('punch', impact, -6)


def chiffre(s, a, b, p, d):
    fin = _borne(d['fin_compte'], a + 0.3, b)
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p)
    v = float(p['valeur'])
    fmt = lambda x: '%s%s%s' % (p.get('prefixe', ''), nombre(x), p.get('suffixe', ''))
    taille = ajuste(fmt(v), 'bebas', 430, 900)
    c = s.texte(a, b, fmt(0), CX, 920, 'bebas', taille, BLANC, dessus=bg)
    t0 = a + 0.05
    n = max(2, int((fin - t0) * FPS))
    cles, vus = [], None
    for k in range(0, n + 1, 2):
        u = k / n
        x = v * (1 - (1 - u) ** 3)
        x = round(x) if abs(v - round(v)) < 1e-6 else round(x, 1)
        if x != vus:
            cles.append((t0 + k * f, {'text': fmt(x)}))
            vus = x
    if vus != v:
        cles.append((fin, {'text': fmt(v)}))
    s.cles(c, cles, maintien=True)
    s.cles(c, [(fin - f, {'fill_color': BLANC}), (fin, {'fill_color': ROUGE})], maintien=True)
    s.cles(c, [(fin, {'scale': 100}), (fin + 4 * f, {'scale': 116}), (fin + 9 * f, {'scale': 100})])
    for k, (t, _) in enumerate(cles[1:-1]):
        if k % 3 == 0:
            s.son('clic', t, -16)
    if p.get('texte') and fin - 0.1 < b - 0.2:
        s.texte(a, b, p['texte'], CX, 1260, 'inter', ajuste(p['texte'], 'inter', 110), BLANC, entree='monte',
                t=fin - 0.1, dessus=bg)
    s.son('ding', fin, -9)
    s.son('boom', fin, -8)


def comparaison(s, a, b, p, d):
    t1 = _borne(d['avant'], a, b)
    t3 = _borne(d['apres'], t1 + 0.3, b)
    t2 = _borne(d.get('rature') or (t3 - 0.3), t1 + 0.15, t3)
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 480)
    avant, apres = p.get('avant', '×1'), p.get('apres', '×2')
    ta = ajuste(avant, 'inter', 280, 800)
    un = s.texte(a, b, avant, CX, 800, 'inter', ta, BLANC, entree='pop', t=t1, dessus=bg)
    w = largeur('inter', avant, ta) + 60
    s.barre(a, b, CX - w / 2, 800, w, 22, ROUGE, t=t2, duree=5, rot=-12, dessus=un)
    s.texte(a, b, apres, CX, 1210, 'inter', ajuste(apres, 'inter', 330, 900), ROUGE, entree='tampon', t=t3, dessus=bg)
    if p.get('texte'):
        s.texte(a, b, p['texte'], CX, 1500, 'play', ajuste(p['texte'], 'play', 90), GRIS, entree='fondu', t=t3,
                dessus=bg)
    s.son('clic', t1, -6)
    s.son('declencheur', t2, -4)
    s.son('punch', t3, -8)


def progression(s, a, b, p, d):
    t0 = _borne(d.get('depart') or a + 0.15, a, b)
    fin = _borne(d['fin'], t0 + 0.3, b)
    v = max(0.0, min(100.0, float(p.get('valeur', 100))))
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 640)
    s.rect(a, b, CX, 1000, 820, 80, None, contour=BLANC, epaisseur=6, rayon=40, dessus=bg)
    n = max(2, int((fin - t0) * FPS))
    s.barre(a, b, 140, 1000, 800 * v / 100, 60, ROUGE, t=t0, duree=n, dessus=bg)
    compteur = s.texte(a, b, '0 %', CX, 860, 'bebas', 130, BLANC, dessus=bg)
    cles = []
    for k in range(0, n + 1, 2):
        u = k / n
        cles.append((t0 + k * f, {'text': '%d %%' % round(v * (1 - (1 - u) ** 3))}))
    cles.append((fin, {'text': '%d %%' % round(v)}))
    s.cles(compteur, cles, maintien=True)
    if p.get('texte'):
        s.texte(a, b, p['texte'], CX, 1180, 'inter', ajuste(p['texte'], 'inter', 110), BLANC, entree='monte',
                t=min(t0 + 0.3, fin), dessus=bg)
    s.son('riser', fin, -12, avant=fin - t0, duree=fin - t0 + 0.05)
    s.son('ding', fin, -10)


def horloge(s, a, b, p, d):
    t0 = _borne(d.get('depart') or a + 0.1, a, b)
    arret = _borne(d['arret'], t0 + 0.4, b)
    cx, cy, r = CX, 860, 270
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 400)
    s.ellipse(a, b, cx, cy, 2 * r, 2 * r, None, contour=BLANC, epaisseur=14, entree='pop', t=a + 0.03, dessus=bg)
    for k in range(12):
        ang = k * 30
        x = cx + (r - 40) * math.sin(math.radians(ang))
        y = cy - (r - 40) * math.cos(math.radians(ang))
        s.rect(a, b, x, y, 10 if k % 3 else 14, 30 if k % 3 else 46, BLANC, rot=ang, entree='fondu',
               t=a + 0.08 + k * 0.01, dessus=bg)
    aiguille = s.rect(a, b, cx, cy, 14, 230, ROUGE, dessus=bg)
    s.regle(aiguille, anchor=[0, 115], position=[cx, cy])
    s.cles(aiguille, [(t0, {'rotation': 0}), (arret, {'rotation': 360 * float(p.get('tours', 1))})])
    s.ellipse(a, b, cx, cy, 40, 40, ROUGE, dessus=aiguille)
    if p.get('texte'):
        s.texte(a, b, p['texte'], CX, 1420, 'bebas', ajuste(p['texte'], 'bebas', 200), ROUGE, entree='tampon',
                t=arret, dessus=bg)
    s.son('tictac', arret, -9, avant=arret - t0, duree=arret - t0 + 0.05)
    s.son('declencheur', arret, -3)


def chapitre(s, a, b, p, d):
    t = _borne(d['impact'], a, b)
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 520)
    s.ellipse(a, b, CX, 900, 300, 300, None, contour=ROUGE, epaisseur=16, entree='pop', t=t, dessus=bg)
    s.texte(a, b, str(p.get('numero', '01')), CX, 900, 'bebas', 170, BLANC, entree='tampon', t=t + 3 * f, dessus=bg)
    s.son('pop', t, -6)
    if p.get('texte'):
        tt = _borne(t + 0.35, a, b)
        s.texte(a, b, p['texte'], CX, 1260, 'inter', ajuste(p['texte'], 'inter', 100), BLANC, entree='monte', t=tt,
                dessus=bg)
        s.son('clic', tt, -8)


def courbe(s, a, b, p, d):
    t0 = a + 0.05
    impact = _borne(d['impact'], t0 + 0.25, b)
    t1 = max(impact + 0.2, b - 0.12)
    chute = p.get('sens', 'chute') != 'hausse'
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 520)
    s.rect(a, b, CX, 1000, 960, 3, '#3A3A3A', dessus=bg)
    if chute:
        s.rect(a, b, CX, 1190, 1080, 220, ROUGE, opacite=28, entree='fondu', t=max(a, impact - 0.3), dessus=bg)
    y0 = 880 if chute else 1120
    y1 = 1220 if chute else 640

    def y_de(x):
        if x < 560:
            return y0 + 50 * math.sin(x / 70)
        u = min(1, (x - 560) / 120)
        return y0 + 50 * math.sin(560 / 70) + (y1 - y0 - 50 * math.sin(560 / 70)) * (3 * u * u - 2 * u ** 3)
    c = s.trace(a, b, [[x, round(y_de(x), 1)] for x in range(60, 1021, 8)], BLANC, 9, dessus=bg)
    tete = [(t0, 60), (impact, 600), (t1, 1020)]
    s.revele(c, [(t, x / 1080 * 100) for t, x in tete])
    point = s.ellipse(a, b, 60, y_de(60), 34, 34, ROUGE if not chute else BLANC, dessus=c)
    cles, k = [], 0
    while t0 + k * f <= t1:
        t = t0 + k * f
        x = 60 + (t - t0) / (impact - t0) * 540 if t <= impact else 600 + (t - impact) / (t1 - impact) * 420
        if k % 2 == 0:
            cles.append((t, {'position': [round(x, 1), round(y_de(x), 1)]}))
        k += 1
    cles.append((t1, {'position': [1020, round(y_de(1020), 1)]}))
    s.cles(point, cles, lisse=False)
    if p.get('texte'):
        s.texte(a, b, p['texte'], CX, 1440 if chute else 1340, 'bebas', ajuste(p['texte'], 'bebas', 180), ROUGE,
                entree='tampon', t=impact, dessus=bg)
    if chute:
        s.son('whoosh_bas', impact, -6)
        s.son('boom', impact, -7)
    else:
        s.son('riser', impact, -12, avant=impact - t0, duree=impact - t0 + 0.05)
        s.son('ding', impact, -9)


def question(s, a, b, p, d):
    t = _borne(d['impact'], a, b)
    bg = s.fond(a, b)
    _phrase(s, a, b, bg, p, 420)
    q = s.texte(a, b, '?', CX, 860, 'play', 640, ROUGE, entree='tampon', t=t, dessus=bg)
    s.secousse(q, t + 5 * f, CX, 860, 16, 6)
    if p.get('texte'):
        s.texte(a, b, p['texte'], CX, 1380, 'inter', ajuste(p['texte'], 'inter', 110), BLANC, entree='monte',
                t=_borne(t + 0.2, a, b), dessus=bg)
    s.son('woosh', a, -9)
    s.son('punch', t, -7)


# ------------------------------------------------------------------ surimpressions sur l'A-roll
def pastille(s, a, b, p, d):
    """Pastille de chapitre en haut à gauche (Bebas blanc sur rouge)."""
    t = _borne(d.get('impact') or a, a, b)
    r = s.rect(a, b, 150, 230, 130, 130, ROUGE, rayon=18, entree='pop', t=t)
    s.texte(a, b, str(p.get('texte', '1')), 150, 230, 'bebas', 100, BLANC, entree='pop', t=t + f, dessus=r)
    s.son('clic', t, -6)


def compteur(s, a, b, p, d):
    """×1 barré puis ×2 rouge, sous le bloc de texte (jamais sur le visage)."""
    y = 1730
    t1 = _borne(d.get('avant') or a, a, b)
    t3 = _borne(d['apres'], t1 + 0.3, b)
    t2 = _borne(d.get('rature') or t3 - 0.25, t1 + 0.1, t3)
    avant, apres = p.get('avant', '×1'), p.get('apres', '×2')
    un = s.texte(a, b, avant, 405, y, 'bebas', 170, BLANC, entree='fondu', t=t1)
    w = largeur('bebas', avant, 170) + 40
    s.barre(a, b, 405 - w / 2, y, w, 14, ROUGE, t=t2, duree=4, rot=-12, dessus=un)
    s.texte(a, b, apres, 675, y, 'bebas', 200, ROUGE, entree='tampon', t=t3)
    s.son('clic', t1, -8)
    s.son('declencheur', t2, -6)
    s.son('clic', t3, -4)


INSERTS = {
    'mot_choc': (mot_choc, 'Mot ou expression clé tamponné en grand, secousse, trait sous le mot. Le plus polyvalent.',
                 {'texte': 'MOT-CLÉ en majuscules (1 à 3 mots)', 'phrase': '(option) petite phrase en italique au-dessus',
                  'couleur': '(option) rouge (défaut) ou blanc', 'sous_texte': '(option) ligne en italique dessous'},
                 {'impact': 'syllabe du mot-clé'}),
    'chiffre': (chiffre, 'Compteur qui monte de 0 au nombre dit, vire au rouge et pulse. Pour tout chiffre marquant.',
                {'valeur': 'nombre (ex. 20, 1500, 2.5)', 'prefixe': '(option) ex. ×, +, $', 'suffixe': '(option) ex. %, €, k',
                 'texte': '(option) ce que compte le chiffre (DATES, ABONNÉS)', 'phrase': '(option) phrase au-dessus'},
                {'fin_compte': 'mot du chiffre : le compteur s’arrête dessus'}),
    'comparaison': (comparaison, 'Avant / après : la première valeur se fait barrer, la seconde claque en rouge.',
                    {'avant': 'ex. ×1, 10 k, AVANT', 'apres': 'ex. ×2, 100 k, APRÈS', 'texte': '(option) ligne dessous',
                     'phrase': '(option) phrase au-dessus'},
                    {'avant': 'mot de la première valeur', 'apres': 'mot de la seconde',
                     'rature': '(option) instant de la rature'}),
    'progression': (progression, 'Barre qui se remplit avec pourcentage. Apprentissage, progrès, étapes.',
                    {'valeur': '0 à 100 (défaut 100)', 'texte': '(option) mot en dessous', 'phrase': '(option)'},
                    {'fin': 'mot où la barre est pleine', 'depart': '(option) début du remplissage'}),
    'horloge': (horloge, 'Cadran dont l’aiguille tourne et s’arrête net (tic-tac). Durée, heure, temps qui passe.',
                {'texte': 'ex. 1 HEURE, 3 ANS', 'tours': '(option) nombre de tours (défaut 1)', 'phrase': '(option)'},
                {'arret': 'mot de la durée : l’aiguille s’y arrête', 'depart': '(option)'}),
    'chapitre': (chapitre, 'Numéro dans un anneau rouge + titre : annonce une partie (d’abord, ensuite, 3 raisons…).',
                 {'numero': 'ex. 01', 'texte': '(option) titre de la partie', 'phrase': '(option)'},
                 {'impact': 'mot qui annonce la partie'}),
    'courbe': (courbe, 'Courbe tracée en direct qui plonge (ou grimpe) sur le mot. Chute, crise, croissance.',
               {'sens': 'chute (défaut) ou hausse', 'texte': '(option) mot tamponné au moment clé', 'phrase': '(option)'},
               {'impact': 'mot de la chute / de la hausse'}),
    'question': (question, 'Point d’interrogation géant + question. Pour une vraie question au spectateur.',
                 {'texte': '(option) la question en majuscules courtes', 'phrase': '(option)'},
                 {'impact': 'mot clé de la question'}),
}

SURIMPRESSIONS = {
    'pastille': (pastille, 'Pastille de chapitre en haut à gauche, sur l’A-roll (1, 2, 3…).',
                 {'texte': 'ex. 1'}, {'impact': '(option) apparition'}),
    'compteur': (compteur, '×1 barré puis ×2 rouge sous le texte, sur l’A-roll.',
                 {'avant': 'ex. ×1', 'apres': 'ex. ×2'},
                 {'avant': '(option)', 'apres': 'mot de la seconde valeur', 'rature': '(option)'}),
    'souligne': (None, 'Barre rouge qui se trace sous le mot-clé d’un bloc de texte (le mot doit être mot-clé).',
                 {'mot': 'le mot souligné, en minuscules'}, {'mot': 'instant du mot (temps source)'}),
}


def doc():
    """Catalogue en Markdown (pour l'IA)."""
    out = ['# Gabarits EditFou', '',
           'Temps des `debut`, `fin` et déclencheurs : secondes de la VIDÉO SOURCE (comme mots.json).', '']
    for titre, cat in (('Inserts plein écran (`inserts`)', INSERTS), ('Surimpressions sur l’A-roll (`surimpressions`)',
                                                                     SURIMPRESSIONS)):
        out += ['## ' + titre, '']
        for nom, (_, desc, params, decl) in cat.items():
            out.append('### `%s` — %s' % (nom, desc))
            out += ['- param `%s` : %s' % kv for kv in params.items()]
            out += ['- déclencheur `%s` : %s' % kv for kv in decl.items()]
            out.append('')
    return '\n'.join(out)
