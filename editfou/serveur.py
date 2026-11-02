"""Interface web locale d'EditFou : coller un lien, suivre l'analyse, valider les clips puis les storyboards,
lancer le montage et regarder le résultat. Les étapes longues tournent en tâche de fond (`python -m editfou …`),
leur sortie va dans projets/<projet>/journal.txt.

  python -m editfou serveur        → http://localhost:5100
"""
import os, subprocess, sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from . import ia
from .config import PAQUET, RACINE
from .gabarits import INSERTS, SURIMPRESSIONS
from .projet import Projet
from .storyboard import verifier

app = FastAPI(title='EditFou')
TACHES = {}          # slug → Popen


def _p(slug):
    try:
        return Projet(slug)
    except FileNotFoundError:
        raise HTTPException(404, 'projet inconnu')


def _lancer(p, *args):
    t = TACHES.get(p.slug)
    if t and t.poll() is None:
        raise HTTPException(409, 'une tâche tourne déjà sur ce projet')
    journal = open(p.chemin('journal.txt'), 'a', encoding='utf-8')
    journal.write('\n$ editfou %s\n' % ' '.join(args)); journal.flush()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    TACHES[p.slug] = subprocess.Popen([sys.executable, '-m', 'editfou'] + list(args), cwd=RACINE, stdout=journal,
                                      stderr=subprocess.STDOUT, env=env,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


def _occupe(p):
    t = TACHES.get(p.slug)
    return bool(t and t.poll() is None)


def _resume(p):
    clips = p.clips()
    return {'slug': p.slug, 'info': p.info(), 'etat': p.etat(), 'occupe': _occupe(p),
            'clips': {'total': len(clips), 'valides': sum(c['statut'] == 'valide' for c in clips),
                      'montes': sum(bool(c.get('monte')) for c in clips)}}


@app.get('/', response_class=HTMLResponse)
def accueil():
    with open(os.path.join(PAQUET, 'web', 'index.html'), encoding='utf-8') as f:
        return f.read()


@app.get('/polices/{nom}')
def polices(nom: str):
    f = os.path.join(PAQUET, 'polices', os.path.basename(nom))
    if not f.endswith('.ttf') or not os.path.isfile(f):
        raise HTTPException(404)
    return FileResponse(f, media_type='font/ttf')


@app.get('/api/config')
def config():
    return {'ia': ia.disponible(), 'gabarits': {'inserts': {k: v[1] for k, v in INSERTS.items()},
                                                'surimpressions': {k: v[1] for k, v in SURIMPRESSIONS.items()}}}


@app.get('/api/projets')
def projets():
    return [_resume(p) for p in Projet.liste()]


class Nouveau(BaseModel):
    source: str
    nom: str = ''


@app.post('/api/projets')
def creer(n: Nouveau):
    src = n.source.strip().strip('"')
    if not (src.startswith('http://') or src.startswith('https://') or os.path.isfile(src)):
        raise HTTPException(400, 'ni un lien, ni un fichier vidéo existant')
    p = Projet.creer(src, n.nom.strip() or None)
    _lancer(p, 'analyser', p.slug)
    return _resume(p)


@app.get('/api/projets/{slug}')
def projet(slug: str):
    p = _p(slug)
    out = _resume(p)
    clips = p.clips()
    for c in clips:
        sb = p.storyboard(c['id'])
        c['storyboard'] = None if not sb else {'statut': sb.get('statut'), 'auteur': sb.get('auteur', ''),
                                               'problemes': verifier(sb, p)}
        c['rendu'] = bool(c.get('monte')) and os.path.isfile(p.rendu(c['id']))
        c['projet_filmcraft'] = p.chemin('clips', c['id'], 'montage.fcproj') if c.get('monte') else ''
    out['clips_detail'] = clips
    out['ia'] = ia.disponible()
    return out


@app.get('/api/projets/{slug}/journal')
def journal(slug: str):
    f = _p(slug).chemin('journal.txt')
    if not os.path.isfile(f):
        return {'texte': ''}
    with open(f, encoding='utf-8', errors='replace') as fh:
        return {'texte': fh.read()[-6000:]}


@app.get('/api/projets/{slug}/video')
def video(slug: str):
    p = _p(slug)
    try:
        return FileResponse(p.video(), media_type='video/mp4')
    except FileNotFoundError:
        raise HTTPException(404, 'vidéo pas encore disponible')


@app.post('/api/projets/{slug}/proposer')
def proposer(slug: str):
    p = _p(slug)
    if not ia.disponible():
        raise HTTPException(409, 'pas d’IA intégrée : demande à ton agent de proposer les clips')
    _lancer(p, 'proposer', slug)
    return {'ok': True}


class MajClip(BaseModel):
    statut: str | None = None
    debut: float | None = None
    fin: float | None = None
    titre: str | None = None


@app.post('/api/projets/{slug}/clips/{cid}')
def maj_clip(slug: str, cid: str, m: MajClip):
    p = _p(slug)
    kw = {k: v for k, v in m.model_dump().items() if v is not None}
    if 'statut' in kw and kw['statut'] not in ('propose', 'valide', 'rejete'):
        raise HTTPException(400, 'statut invalide')
    c = p.maj_clip(cid, **kw)
    if kw.get('statut') == 'valide':
        p.etat('storyboards', 'attente_ia', "Clips validés : l'IA peut écrire les storyboards")
    return c


@app.get('/api/projets/{slug}/clips/{cid}/storyboard')
def lire_storyboard(slug: str, cid: str):
    p = _p(slug)
    sb = p.storyboard(cid)
    if not sb:
        raise HTTPException(404, 'pas encore de storyboard')
    return {'storyboard': sb, 'problemes': verifier(sb, p), 'mots': p.mots(sb['debut'], sb['fin'])}


class Storyboard(BaseModel):
    storyboard: dict


@app.post('/api/projets/{slug}/clips/{cid}/storyboard')
def ecrire_storyboard(slug: str, cid: str, s: Storyboard):
    p = _p(slug)
    sb = s.storyboard
    sb['clip'] = cid
    err = verifier(sb, p)
    if sb.get('statut') == 'valide' and err:
        raise HTTPException(400, 'storyboard invalide : ' + ' ; '.join(err))
    p.ecrire_storyboard(cid, sb)
    return {'problemes': err}


@app.post('/api/projets/{slug}/clips/{cid}/storyboard/auto')
def storyboard_auto(slug: str, cid: str):
    p = _p(slug)
    if ia.disponible():
        _lancer(p, 'storyboard', slug, cid, '--ia', ia.disponible())
        return {'tache': True}
    from .storyboard import brouillon_auto, ecrire
    return {'problemes': ecrire(p, cid, brouillon_auto(p, p.clip(cid)))}


@app.post('/api/projets/{slug}/clips/{cid}/monter')
def monter(slug: str, cid: str):
    p = _p(slug)
    sb = p.storyboard(cid)
    if not sb or sb.get('statut') != 'valide':
        raise HTTPException(409, 'valide d’abord le storyboard')
    if not p.info().get('video'):
        raise HTTPException(409, 'la vidéo se télécharge encore : relance le montage quand elle est prête')
    _lancer(p, 'monter', slug, cid)
    return {'ok': True}


@app.get('/api/projets/{slug}/clips/{cid}/rendu')
def rendu(slug: str, cid: str):
    f = _p(slug).rendu(cid)
    if not os.path.isfile(f):
        raise HTTPException(404, 'pas encore monté')
    return FileResponse(f, media_type='video/mp4', filename=os.path.basename(f))
