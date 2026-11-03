"""Client du canal de contrôle FilmCraft (JSON par ligne sur 127.0.0.1) et export sans interface.

Le jeton est tiré au hasard à chaque lancement et gardé dans un fichier du profil utilisateur
(réglage `jeton_filmcraft`) : il n'apparaît ni en argument, ni dans les journaux, ni dans le dépôt.
On n'exporte jamais par le canal de contrôle (export.quick bloque et ferme le port) : `exporter`
passe par filmcraft-cli sur le projet enregistré.
"""
import json, os, secrets, socket, subprocess, time

from .config import C

T = 254016000000          # ticks FilmCraft par seconde
FPS = 30
F = T // FPS              # ticks par image
PRESET = 'Match Source – Adaptive High Bitrate'
# le mixeur FilmCraft somme les pistes sans limiteur : on normalise à l'export
REGLAGES_EXPORT = {'effects': {'loudness': {'enabled': True, 'target_lufs': -14.0, 'true_peak_dbtp': -1.0}}}


class Erreur(Exception):
    pass


def _exe(nom):
    d = C['filmcraft']
    if not d or not os.path.isfile(os.path.join(d, nom)):
        raise Erreur('FilmCraft introuvable : renseigner "filmcraft" (dossier de %s) dans editfou.local.json' % nom)
    return os.path.join(d, nom)


def _connexion(delai):
    # une connexion par commande : sur un long montage Windows peut manquer de ports locaux (WinError 10048),
    # le temps que les anciens se libèrent
    for essai in range(30):
        try:
            return socket.create_connection(('127.0.0.1', C['port_filmcraft']), timeout=delai)
        except OSError as e:
            if getattr(e, 'winerror', None) != 10048 or essai == 29:
                raise
            time.sleep(2)


def requete(methode, params=None, delai=120):
    with open(C['jeton_filmcraft']) as f:
        jeton = f.read().strip()
    with _connexion(delai) as s:
        msg = {'id': 1, 'token': jeton, 'method': methode}
        if params is not None:
            msg['params'] = params
        s.sendall((json.dumps(msg) + '\n').encode())
        tampon = b''
        while not tampon.endswith(b'\n'):
            bloc = s.recv(1 << 20)
            if not bloc:
                break
            tampon += bloc
    return json.loads(tampon.decode('utf-8'))


def cmd(commande, params=None):
    r = requete('engine.execute', {'command': commande, 'params': params or {}})
    if not r.get('ok'):
        raise Erreur('%s %s → %s' % (commande, json.dumps(params, ensure_ascii=False)[:300], r.get('error')))
    return r.get('result') or {}


def connecte():
    try:
        return bool(requete('ui.inspect', delai=5))
    except (OSError, ValueError):
        return False


def lancer():
    """Ouvre FilmCraft avec un jeton neuf et attend que le canal réponde."""
    os.makedirs(os.path.dirname(C['jeton_filmcraft']), exist_ok=True)
    jeton = secrets.token_hex(32)
    with open(C['jeton_filmcraft'], 'w') as f:
        f.write(jeton)
    exe = _exe('filmcraft.exe')
    env = dict(os.environ, FILMCRAFT_CONTROL_TOKEN=jeton)
    drapeaux = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0
    subprocess.Popen([exe, '--control', str(C['port_filmcraft'])], env=env, cwd=os.path.dirname(exe),
                     creationflags=drapeaux)
    for _ in range(60):
        time.sleep(1)
        if connecte():
            return
    raise Erreur('FilmCraft ne répond pas sur le port %d' % C['port_filmcraft'])


def assurer():
    """FilmCraft ouvert et pilotable (lancé si besoin)."""
    if os.path.isfile(C['jeton_filmcraft']) and connecte():
        return
    lancer()


def exporter(projet, sortie, journal=None):
    """Export H.264 à la taille de la séquence, son à -14 LUFS / -1 dBTP, sans interface."""
    r = subprocess.run([_exe('filmcraft-cli.exe'), '--project', projet, '--compact', 'export', sortie,
                        '--preset', PRESET, '--settings', json.dumps(REGLAGES_EXPORT)],
                       stdout=journal, stderr=subprocess.STDOUT if journal else None)
    if r.returncode or not os.path.isfile(sortie):
        raise Erreur('export FilmCraft échoué (code %d)' % r.returncode)
    return sortie
