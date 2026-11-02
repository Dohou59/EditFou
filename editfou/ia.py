"""IA intégrée, facultative : un appel texte → texte vers Anthropic, OpenAI, Gemini ou Ollama (local).

EditFou est d'abord fait pour être piloté par un agent (Claude Code ou autre) qui lit AGENTS.md et écrit lui-même
clips.json et storyboard.json. Ce module sert quand on veut cliquer « Proposer » dans l'interface sans agent.
Les clés se lisent dans l'environnement uniquement (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).
"""
import json, os, re, urllib.request

from .config import C

MODELES = {'anthropic': 'claude-sonnet-5-5', 'openai': 'gpt-4o', 'gemini': 'gemini-2.0-flash', 'ollama': 'llama3.1'}
CLES = {'anthropic': 'ANTHROPIC_API_KEY', 'openai': 'OPENAI_API_KEY', 'gemini': 'GEMINI_API_KEY'}


class Erreur(Exception):
    pass


def disponible(fournisseur=None):
    """Nom du fournisseur utilisable, ou '' (pas de fournisseur configuré, ou clé absente)."""
    f = fournisseur or (C.get('ia') or {}).get('fournisseur') or ''
    if not f:
        return ''
    if f in CLES and not os.environ.get(CLES[f]):
        return ''
    return f


def _post(url, corps, entetes, delai=300):
    req = urllib.request.Request(url, json.dumps(corps).encode(), dict(entetes, **{'content-type': 'application/json'}))
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise Erreur('%s : HTTP %d %s' % (url.split('/')[2], e.code, e.read().decode('utf-8', 'replace')[:300]))


def demander(prompt, fournisseur=None, modele=None, max_jetons=8000):
    f = disponible(fournisseur)
    if not f:
        raise Erreur("aucune IA intégrée configurée : renseigner ia.fournisseur dans editfou.local.json et la clé "
                     "dans l'environnement, ou demander à l'agent (Claude Code…) de faire l'étape")
    m = modele or (C.get('ia') or {}).get('modele') or MODELES[f]
    if f == 'anthropic':
        r = _post('https://api.anthropic.com/v1/messages',
                  {'model': m, 'max_tokens': max_jetons, 'messages': [{'role': 'user', 'content': prompt}]},
                  {'x-api-key': os.environ[CLES[f]], 'anthropic-version': '2023-06-01'})
        return ''.join(b.get('text', '') for b in r.get('content', []))
    if f == 'openai':
        r = _post('https://api.openai.com/v1/chat/completions',
                  {'model': m, 'messages': [{'role': 'user', 'content': prompt}]},
                  {'authorization': 'Bearer ' + os.environ[CLES[f]]})
        return r['choices'][0]['message']['content']
    if f == 'gemini':
        r = _post('https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % m,
                  {'contents': [{'parts': [{'text': prompt}]}]}, {'x-goog-api-key': os.environ[CLES[f]]})
        return ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts'])
    if f == 'ollama':
        r = _post('http://localhost:11434/api/chat',
                  {'model': m, 'stream': False, 'messages': [{'role': 'user', 'content': prompt}]}, {})
        return r['message']['content']
    raise Erreur('fournisseur inconnu : %s' % f)


def json_de(texte):
    """Premier objet ou tableau JSON d'une réponse (tolère ```json … ``` autour)."""
    t = re.sub(r'^```(?:json)?|```$', '', texte.strip(), flags=re.M).strip()
    for o, c in (('{', '}'), ('[', ']')):
        i, j = t.find(o), t.rfind(c)
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                continue
    raise Erreur('réponse sans JSON lisible : %s' % texte[:200])
