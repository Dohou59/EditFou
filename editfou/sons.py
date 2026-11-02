"""Bruitages et musique : chaque rôle (punch, whoosh, ding…) pointe vers un fichier de la bibliothèque de
l'utilisateur (`sons` dans editfou.local.json). On mesure une fois la durée et l'instant du pic de chaque son,
pour que le pic tombe pile sur l'événement graphique. Cache : sons/catalogue.json (non versionné).
"""
import json, os, subprocess

import numpy as np

from .config import C, RACINE

CACHE = os.path.join(RACINE, 'sons', 'catalogue.json')
ROLES = {
    'musique': 'nappe musicale sous la voix (≈ 13 dB plus bas), coupée sur le moment grave',
    'braam': 'ouverture du teaser noir et blanc',
    'whoosh': 'bascule teaser → récit, passage rapide',
    'whoosh_bas': 'chute, plongée',
    'woosh': 'entrée d’un insert plein écran (court)',
    'swoosh': 'mot qui glisse',
    'punch': 'impact d’un mot-clé tamponné',
    'hit': 'gros impact (moment fort)',
    'boom': 'grave qui tombe, chiffre géant',
    'pop': 'apparition d’une forme',
    'clic': 'compteur, pastille, barre qui se trace',
    'declencheur': 'tampon, rature',
    'ding': 'fin d’un compteur, aiguille qui s’arrête',
    'tictac': 'horloge',
    'riser': 'montée avant un chiffre',
    'verre': 'fissure, cassure',
}


def mesurer(f):
    brut = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                          capture_output=True).stdout
    x = np.abs(np.frombuffer(brut, dtype=np.int16).astype(np.float32))
    if not len(x):
        raise ValueError('son illisible : %s' % f)
    env = np.convolve(x, np.ones(80) / 80, mode='same')     # enveloppe 10 ms
    return {'fichier': f, 'duree': round(len(x) / 8000, 3), 'pic': round(float(np.argmax(env)) / 8000, 3),
            'taille': os.path.getsize(f)}


def catalogue(rafraichir=False):
    """{rôle: {fichier, duree, pic}} pour les rôles configurés et lisibles."""
    cache = {}
    if os.path.isfile(CACHE) and not rafraichir:
        with open(CACHE, encoding='utf-8') as fh:
            cache = json.load(fh)
    out, change = {}, False
    for role, f in (C.get('sons') or {}).items():
        if not f or not os.path.isfile(f):
            continue
        c = cache.get(role)
        if not c or c['fichier'] != f or c.get('taille') != os.path.getsize(f):
            try:
                c = mesurer(f)
            except ValueError:
                continue
            change = True
        out[role] = c
    if change or rafraichir:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
    return out
