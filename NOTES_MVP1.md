## Premières observations
- La description dans le README est à harmoniser avec le contenu réel du projet -> Voir ## Structure du projet dans le README d'origine. 
- A aucun moment il n'est fait mention du data_loader. D'ailleurs à quoi sert-il exactement, étant donné qu'il existe le fichier indexer.py ?
- Je préconise uv comme gestionnaire de dépendance --> A adapter dans le README
- Le processus d'OCRisation des pdf est particulièrement long. Nous n'avons pas des pdf natifs, ceci explique peut être cela -> Envisager une autre façon de récolter les sources depuis Reddit ?
- D'ailleurs bien déterminer les rôles : quand, et quoi mettre dans les inputs, par qui ? A quelle fréquence ? Quels sont les indicateurs permettant de tracer la bonne alimentation du système. Veille à envisager ? Pas mal de questions sur le sujet

## Fait
- Test de run pour data_loader.py et indexer.py
- Un schéma rapide UML de l'existant
- Ce fichier

## A faire
- Insérer un timer au début de indexer pour calculer le temps exact, ce sera l'une des métriques