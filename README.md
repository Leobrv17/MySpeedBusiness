# MySpeedBusiness

MySpeedBusiness est une application de planification de rendez-vous et d'export de comptes-rendus, pensée pour les sessions de type speed-meeting. L'interface graphique repose sur PySide6 et s'appuie sur SQLite pour stocker les événements, les participants et les plans de table générés par l'algorithme de rotation intégré.

## Installation

1. Assurez-vous de disposer de Python 3.11 ou plus récent.
2. (Optionnel) Créez un environnement virtuel :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows : .venv\\Scripts\\activate
   ```
3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

## Lancer l'application

L'application démarre une interface Qt. Depuis la racine du dépôt :
```bash
python -m msb.app
```
Un dossier `data/` est créé automatiquement pour stocker les journaux et les fichiers générés. Sous certains systèmes, l'affichage peut nécessiter les paquets supplémentaires propres à Qt (bibliothèques système ou variables d'environnement, par exemple `QT_QPA_PLATFORM=xcb` sous Linux minimal).

## Générer des exécutables Windows / macOS / Linux

La création de binaires autonomes s'appuie sur [PyInstaller](https://pyinstaller.org/). Les ressources nécessaires (icônes, feuilles de style) sont déjà référencées dans `packaging/msb.spec` et accessibles dans l'application grâce à la détection automatique du dossier de ressources.

1. Installez PyInstaller en plus des dépendances applicatives :
   ```bash
   pip install -r requirements.txt pyinstaller
   ```
2. Depuis la racine du dépôt, lancez la construction (commande identique sur Linux/macOS/WSL) :
   ```bash
   python -m PyInstaller --clean packaging/msb.spec
   ```
   Sous Windows natif, l'équivalent PowerShell est `py -m PyInstaller --clean packaging/msb.spec`.
3. Les exécutables sont générés dans `dist/bundle/MySpeedBusiness/` (le binaire
   intermédiaire `dist/MySpeedBusiness` créé par PyInstaller n'est pas utilisé) :
   - `MySpeedBusiness.exe` pour Windows,
   - `MySpeedBusiness` pour macOS et Linux.

Au premier lancement, un dossier `data/` est créé à côté de l'exécutable pour stocker les bases SQLite, journaux et exports générés.

## Exécuter les tests

La suite de tests utilise `pytest` et couvre notamment l'algorithme de planification des tables.
```bash
pytest
```

## Structure rapide

- `msb/app.py` : point d'entrée de l'application PySide6.
- `msb/services/planner.py` : algorithme de génération des plans de table en évitant les répétitions.
- `msb/services/persistence.py` : gestion des événements et des participants en base SQLite via SQLAlchemy.
- `tests/` : tests unitaires (planification, propriétés générales du projet).
