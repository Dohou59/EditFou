"""EditFou en ligne de commande — chaque étape est une commande, tout est lisible dans projets/<projet>/.

  python -m editfou nouveau <lien YouTube | fichier> [--nom N]   crée le projet, affiche son nom
  python -m editfou analyser <projet> [--modele small]            téléchargement + transcription mot à mot
  python -m editfou phrases <projet>                              transcription en phrases (pour choisir les clips)
  python -m editfou consignes-clips <projet>                      consignes de sélection des clips (pour l'IA)
  python -m editfou proposer <projet> [--ia anthropic] [--fichier clips.json]
                                                                  enregistre les clips proposés (IA intégrée ou fichier)
  python -m editfou clips <projet>                                liste des clips et statuts
  python -m editfou valider <projet> c01 c03 …  /  rejeter <projet> c02 …
  python -m editfou mots <projet> <clip>                          mots horodatés du clip (pour le storyboard)
  python -m editfou gabarits                                      catalogue des motions disponibles
  python -m editfou consignes-storyboard <projet> <clip>          consignes complètes du storyboard (pour l'IA)
  python -m editfou storyboard <projet> <clip> [--auto | --ia anthropic | --fichier sb.json]
  python -m editfou verifier <projet> <clip>                      contrôle le storyboard
  python -m editfou valider-storyboard <projet> <clip>
  python -m editfou monter <projet> <clip> [--sans-export] [--force]
  python -m editfou exporter <projet> <clip>
  python -m editfou etat [<projet>]                               état d'un projet (ou liste des projets)
  python -m editfou sons                                          mesure la bibliothèque de bruitages
  python -m editfou diagnostic                                    vérifie l'installation
  python -m editfou serveur [--port 5100]                         interface web de validation
"""
import argparse, json, os, shutil, subprocess, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from .config import C, LOCAL
from .projet import Projet


def _projet(nom):
    try:
        return Projet(nom)
    except FileNotFoundError as e:
        sys.exit(str(e))


def _lire_json(f):
    with open(f, encoding='utf-8') as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='editfou', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='commande', required=True)
    x = sp.add_parser('nouveau'); x.add_argument('source'); x.add_argument('--nom'); x.add_argument('--analyser', action='store_true')
    x = sp.add_parser('analyser'); x.add_argument('projet'); x.add_argument('--modele'); x.add_argument('--langue')
    for n in ('phrases', 'consignes-clips', 'clips'):
        sp.add_parser(n).add_argument('projet')
    x = sp.add_parser('proposer'); x.add_argument('projet'); x.add_argument('--ia'); x.add_argument('--fichier')
    for n in ('valider', 'rejeter'):
        x = sp.add_parser(n); x.add_argument('projet'); x.add_argument('clips', nargs='+')
    for n in ('mots', 'consignes-storyboard', 'verifier', 'valider-storyboard', 'exporter'):
        x = sp.add_parser(n); x.add_argument('projet'); x.add_argument('clip')
    x = sp.add_parser('storyboard'); x.add_argument('projet'); x.add_argument('clip')
    x.add_argument('--auto', action='store_true'); x.add_argument('--ia'); x.add_argument('--fichier')
    x = sp.add_parser('monter'); x.add_argument('projet'); x.add_argument('clip')
    x.add_argument('--sans-export', action='store_true'); x.add_argument('--force', action='store_true')
    x = sp.add_parser('etat'); x.add_argument('projet', nargs='?')
    sp.add_parser('gabarits'); sp.add_parser('sons'); sp.add_parser('diagnostic')
    x = sp.add_parser('serveur'); x.add_argument('--port', type=int, default=C['port_serveur'])
    a = ap.parse_args(argv)
    c = a.commande

    if c == 'nouveau':
        p = Projet.creer(a.source, a.nom)
        print(p.slug)
        if a.analyser:
            from .analyse import analyser
            analyser(p)
    elif c == 'analyser':
        from .analyse import analyser
        p = _projet(a.projet)
        try:
            analyser(p, a.modele, a.langue)
        except Exception as e:
            if not os.path.isfile(p.chemin('phrases.txt')):  # après : seule la vidéo manque, l'erreur est dans info.json
                p.etat(p.etat().get('etape', 'telechargement'), 'erreur', str(e)[:500])
            raise
        print('Transcription prête : %s' % p.chemin('phrases.txt'))
    elif c == 'phrases':
        with open(_projet(a.projet).chemin('phrases.txt'), encoding='utf-8') as fh:
            print(fh.read())
    elif c == 'consignes-clips':
        from .clips import prompt
        print(prompt(_projet(a.projet)))
    elif c == 'proposer':
        from . import clips
        p = _projet(a.projet)
        try:
            r = clips.enregistrer(p, _lire_json(a.fichier)['clips']) if a.fichier else clips.proposer_ia(p, a.ia)
        except Exception as e:
            p.etat('clips', 'erreur', str(e)[:500])
            raise
        for x in r:
            print('%s  %7.2f–%7.2f  (%4.0f s)  %s' % (x['id'], x['debut'], x['fin'], x['fin'] - x['debut'], x['titre']))
    elif c == 'clips':
        for x in _projet(a.projet).clips():
            print('%s  %-8s %7.2f–%7.2f  (%3.0f s)  score %s  %s' % (x['id'], x['statut'], x['debut'], x['fin'],
                                                                   x['fin'] - x['debut'], x.get('score'), x['titre']))
    elif c in ('valider', 'rejeter'):
        p = _projet(a.projet)
        for cid in a.clips:
            p.maj_clip(cid, statut='valide' if c == 'valider' else 'rejete')
        if c == 'valider':
            p.etat('storyboards', 'attente_ia', "Clips validés : l'IA peut écrire les storyboards")
        print('ok')
    elif c == 'mots':
        from .storyboard import mots_horodates
        p = _projet(a.projet)
        print(mots_horodates(p, p.clip(a.clip)))
    elif c == 'gabarits':
        from .gabarits import doc
        print(doc())
    elif c == 'consignes-storyboard':
        from .storyboard import prompt
        p = _projet(a.projet)
        print(prompt(p, p.clip(a.clip)))
    elif c == 'storyboard':
        from . import storyboard as S
        p = _projet(a.projet)
        if a.fichier:
            err = S.ecrire(p, a.clip, _lire_json(a.fichier))
        elif a.ia:
            err = S.proposer_ia(p, a.clip, a.ia)
        elif a.auto:
            err = S.ecrire(p, a.clip, S.brouillon_auto(p, p.clip(a.clip)))
        else:
            print(json.dumps(p.storyboard(a.clip), ensure_ascii=False, indent=1))
            return
        print('storyboard écrit : %s' % p.chemin('clips', a.clip, 'storyboard.json'))
        print('\n'.join('⚠ ' + e for e in err) or 'aucun problème détecté')
    elif c == 'verifier':
        from .storyboard import verifier
        p = _projet(a.projet)
        sb = p.storyboard(a.clip)
        if not sb:
            sys.exit('pas de storyboard')
        err = verifier(sb, p)
        print('\n'.join('⚠ ' + e for e in err) or 'storyboard correct')
        sys.exit(1 if err else 0)
    elif c == 'valider-storyboard':
        from .storyboard import verifier
        p = _projet(a.projet)
        sb = p.storyboard(a.clip)
        err = verifier(sb, p) if sb else ['pas de storyboard']
        if err:
            sys.exit('\n'.join('⚠ ' + e for e in err))
        sb['statut'] = 'valide'
        p.ecrire_storyboard(a.clip, sb)
        print('ok')
    elif c == 'monter':
        from .montage import monter
        p = _projet(a.projet)
        try:
            monter(p, a.clip, exporter=not a.sans_export, force=a.force)
        except Exception as e:
            p.etat('montage', 'erreur', str(e)[:500])
            raise
    elif c == 'exporter':
        from .montage import exporter_clip
        exporter_clip(_projet(a.projet), a.clip)
    elif c == 'etat':
        if a.projet:
            p = _projet(a.projet)
            print(json.dumps({'info': p.info(), 'etat': p.etat(), 'clips': [
                {k: v for k, v in x.items() if k != 'texte'} for x in p.clips()]}, ensure_ascii=False, indent=1))
        else:
            for p in Projet.liste():
                e = p.etat()
                print('%-40s %-12s %-10s %s' % (p.slug, e.get('etape'), e.get('statut'), e.get('message', '')))
    elif c == 'sons':
        from .sons import catalogue, ROLES
        cat = catalogue(rafraichir=True)
        for r, desc in ROLES.items():
            s = cat.get(r)
            print('%-12s %s' % (r, ('%6.2f s, pic %5.2f s  %s' % (s['duree'], s['pic'], s['fichier'])) if s
                                else '— absent (%s)' % desc))
    elif c == 'diagnostic':
        diagnostic()
    elif c == 'serveur':
        import uvicorn
        print('EditFou : http://localhost:%d' % a.port)
        uvicorn.run('editfou.serveur:app', host='127.0.0.1', port=a.port, log_level='warning')


def diagnostic():
    ok = lambda b: 'ok ' if b else 'NON'
    print('%s réglages locaux        %s' % (ok(os.path.isfile(LOCAL)), LOCAL))
    for outil in ('ffmpeg', 'ffprobe'):
        print('%s %-21s %s' % (ok(shutil.which(outil)), outil, shutil.which(outil) or 'à installer'))
    for mod in ('yt_dlp', 'faster_whisper', 'cv2', 'PIL', 'fastapi', 'uvicorn', 'numpy'):
        try:
            __import__(mod); r = True
        except ImportError:
            r = False
        print('%s %-21s %s' % (ok(r), mod, '' if r else 'pip install -r requirements.txt'))
    from . import filmcraft as fc, ia
    d = C['filmcraft']
    print('%s FilmCraft             %s' % (ok(d and os.path.isfile(os.path.join(d, 'filmcraft-cli.exe'))), d or 'à renseigner'))
    print('%s FilmCraft ouvert      %s' % (ok(os.path.isfile(C['jeton_filmcraft']) and fc.connecte()),
                                         'pilotable' if os.path.isfile(C['jeton_filmcraft']) and fc.connecte()
                                         else 'sera lancé au premier montage'))
    from .sons import catalogue
    n = len(catalogue())
    print('%s bruitages             %d rôles configurés' % (ok(n), n))
    polices = subprocess.run(['powershell', '-NoProfile', '-Command',
                              '(New-Object System.Drawing.Text.InstalledFontCollection).Families.Name'],
                             capture_output=True, text=True).stdout if os.name == 'nt' else ''
    for fam in ('Inter 24pt', 'Bebas Neue', 'Playfair Display'):
        inst = fam in polices or not polices
        print('%s police %-14s %s' % (ok(inst), fam, '' if inst else 'installer editfou/polices/ (double-clic)'))
    f = ia.disponible()
    print('%s IA intégrée           %s' % (ok(f), f or 'aucune (l’agent fait les étapes IA)'))


if __name__ == '__main__':
    main()
