# IA-PRESENCE

Système desktop de gestion des présences par reconnaissance faciale (EMSI).

Le [rapport du projet](rapport_IA_PRESENCE.docx) est inclus dans ce dépôt. Les photos, empreintes faciales, données de présence et exports restent locaux et ne sont pas publiés.

## Installation

```bash
cd projetfacial
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Sur Windows, `tf-keras` est requis avec TensorFlow 2.20+ (inclus dans `requirements.txt`).

Avant d'enregistrer de vrais visages, définissez la variable d'environnement `IA_PRESENCE_ENCRYPTION_KEY` avec une clé privée. Sans elle, la clé de démonstration est utilisée. Conservez la clé privée hors du dépôt : la changer empêche de déchiffrer les empreintes déjà enregistrées.

## Lancement

```bash
python main.py
```

## Fonctionnalités

- **Upload photos** : bouton « Ajouter photos » — nom + images → embedding pour la reconnaissance.
- **Webcam** : détection et identification en temps réel (démarrage automatique).
- **Présences** : enregistrement automatique (nom, date/heure, statut IN TIME/LATE, numéro de classe).
- **Export Excel** : rapport quotidien dans `exports/`.

## Numéro de classe

Saisissez le numéro dans la barre supérieure (« Classe »). Tous les pointages webcam utilisent cette valeur.

## Tests

```bash
python -m pytest tests/ -v
```

## Structure

- `core/` : reconnaissance faciale, enrôlement et authentification.
- `database/` : stockage des présences.
- `security/` : chiffrement des empreintes faciales.
- `ui/` : interface desktop et caméra.
- `export/` : export Excel.
- `tests/` : tests automatisés.
