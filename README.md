# Report

Il [report completo](https://github.com/lucaceschi/DART-estensione/blob/main/report/README.md) della estensione DART è sotto la cartella "report"

# Utilizzo ed esecuzione dei test

Il repo è organizzato come progetto del framework [Truffle](https://github.com/trufflesuite/truffle), costituito da:
* il file di configurazione Truffle `truffle-config.js` 
* la cartella `contracts` contenente il codice Solidity dello smart contract DART
* la cartella `migrations` contenente il codice Solidity per il deployment on-chain dello smart contract DART

assieme ad alcuni script Python per i calcoli off-chain e l'esecuzione di test:
* `DART.py`: libreria per l'interazione con lo smart contract on-chain DART e l'esecuzione off-chain del backward search algorithm
* `test_epapers.py`: esegue il test scenario A del paper ICDCS
* `test_wot_passive.py`: esegue il test scenario B (passive behaviour) del paper ICDCS
* `test_wot_active.py`: esegue il test scenario B (active behaviour) del paper ICDCS

Per eseguire i test su una blockchain locale, è necessario possedere [Ganache](https://github.com/trufflesuite/ganache) o [ganache-cli](https://github.com/trufflesuite/ganache-cli). Quindi, dalla root del progetto:
1. avviare Ganache con un numero sufficiente di account di partenza, gas limit pari a `12000000` e network id `1`. Tramite ganache-cli ciò corrisponde ad eseguire `ganache-cli -l 12000000 -i 1`
2. avviare compilazione e deployment su blockchain locale dello smart contract tramite `truffle migrate --network ganache`
3. eseguire il test tramite `python3 nome_test.py [...]`

**NOTA**: a causa del caricamento delle rispettive policies, non è possibile eseguire più volte lo stesso test sulla stessa blockchain locale. Per eseguire nuovamente un test, è necessario riavviare tutta la procedura a partire dal punto 1

