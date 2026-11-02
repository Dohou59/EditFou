"""Réglages d'EditFou : valeurs par défaut, surchargées par `editfou.local.json` à la racine du dépôt
(jamais versionné) puis par les variables d'environnement EDITFOU_*.

Les clés d'API des fournisseurs d'IA ne passent jamais par ce fichier : elles se lisent dans l'environnement
(ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY), que chacun règle lui-même.
"""
import json, os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAQUET = os.path.join(RACINE, 'editfou')
POLICES = os.path.join(PAQUET, 'polices')
LOCAL = os.path.join(RACINE, 'editfou.local.json')

DEFAUTS = {
    # dossier de FilmCraft portable (filmcraft.exe + filmcraft-cli.exe)
    'filmcraft': os.environ.get('FILMCRAFT_DIR', ''),
    'port_filmcraft': 9876,
    # jeton du canal de contrôle : jamais en argument ni dans le dépôt
    'jeton_filmcraft': os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'FilmCraftClaude',
                                    'jeton.txt'),
    'projets': os.path.join(RACINE, 'projets'),
    'langue': 'fr',
    'modele_whisper': 'small',
    # rôle → fichier son (voir README, « Bruitages ») ; un rôle absent est simplement ignoré
    'sons': {},
    # IA intégrée (facultative) : fournisseur parmi anthropic, openai, gemini, ollama
    'ia': {'fournisseur': '', 'modele': ''},
    'port_serveur': 5100,
}


def charger():
    c = json.loads(json.dumps(DEFAUTS))
    if os.path.isfile(LOCAL):
        with open(LOCAL, encoding='utf-8') as f:
            for k, v in json.load(f).items():
                if isinstance(v, dict) and isinstance(c.get(k), dict):
                    c[k].update(v)
                else:
                    c[k] = v
    for k in ('filmcraft', 'projets', 'langue', 'modele_whisper'):
        v = os.environ.get('EDITFOU_' + k.upper())
        if v:
            c[k] = v
    return c


C = charger()


def police(nom):
    """Chemin du fichier de police inclus (mesure des textes)."""
    return os.path.join(POLICES, {'inter': 'Inter_24pt-Black.ttf', 'bebas': 'BebasNeue-Regular.ttf',
                                  'play': 'PlayfairDisplay-Italic.ttf'}[nom])
