# Déploiement GitHub Pages — SunuDoctor

Ce dossier est déployé automatiquement sur la branche `gh-pages`.

- `index.html` : application (base `/sunudoctor/`, routage par hash)
- `404.html` : page de secours pour les liens profonds (SPA)
- `assets/` : bundle JS/CSS
- `.nojekyll` : empêche Jekyll d'ignorer les fichiers commençant par `_`

URL publique : https://aydiarra-star.github.io/sunudoctor/

Le backend n'est **pas** hébergé ici (Pages ne sert que du statique).
L'application se connecte à l'API distante configurée via `VITE_API_BASE`.
Sans backend joignable, l'interface affiche honnêtement « Backend non connecté ».
