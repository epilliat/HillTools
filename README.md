# HillTools

Ce répertoire s'adresse à l'équipe du projet Hill et est constitué de quelques outils pour formater des documents word. 

## Comment le télécharger ?

Utiliser le protocole git, ou autrement cliquer sur "Code" puis "Download Zip" en vert sur cette page.

## Comment l'utiliser sous windows

### Installation des outils nécessaires :

- Télécharger une version de python pour windows avec par exemple [miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Vérifier son installation sous windows : 
  - Ouvrir le powershell (touche Commande + taper "powershell"). dans la suite, toutes les ``commandes`` sont à copier dans le powershell
  - ``python --version``
- Installer pip : ``python -m ensurepip --upgrade``
- Vérifier que pip est bien installé : ``pip --version`` (pas d'erreur en sortie)
- Mettre pip à jour : ``python -m pip install --upgrade pip``
- Installer les modules numpy et textract (pour lire les fichiers word) : ``python -m pip install numpy textract``

### Utilisation rapide :

- Copier le fichier clonage_questions.py dans un répertoire contenant un fichier de questions .docx à formater
- Depuis le répertoire contenant le .docx, ouvrir un powershell :
  - raccourci : Alt, F, S, R
- ``python ./clonage_questions.py``
- Le script s'execute et les répertoires se remplissent.


### Répertoires créés :

- ./native : contient 1 fichier avec toutes les questions natives formatées
- ./tous_clones : contient 1 fichier par question native qui contient toutes les questions clonées possibles
- ./clones_sans_contrainte : contient 1 fichier avec N clones par question, où N est défini dans le script (défaut : 6)
- ./clones_contraintes_min_ab_max_cd : contient 1 fichier N clones par question. On impose que chaque question vraie (resp. fausse) apparaisse un minimum de a (resp. b) fois et un maximum de c (resp. d) fois.