# Report

A seguito della implementazione on-chain dell'algoritmo *backward search* per il *credential chain discovery*, abbiamo osservato che il costo necessario alla sua esecuzione risulta eccessivamente elevato, rendendone difficile l'adozione nel contesto di blockchain pubbliche ove siano presenti limitazioni in termini di gas.

Il nuovo obiettivo è stato dunque quello di comprendere meglio le motivazioni e gli interessi alla base di tale implementazione, nonché la ricerca di una soluzione meno costosa.

È stato osservato anzitutto come la necessità di eseguire on-chain le procedure di credential chain discovery abbia origine dall'interesse di rendere verificabili e trasparenti i calcoli in questione, e che ciò occorra principalmente in tutti quei casi e scenari per cui al risultato di elaborazione delle credenziali memorizzate su blockchain conseguano degli obblighi/interessi collettivi piuttosto che individuali. D'altra parte, ricerche i cui esiti interessano e hanno conseguenze unicamente a livello individuale, potrebbero essere eseguite off-chain dall'individuo stesso senza necessariamente ricorrere al consenso distribuito per il calcolo. Siamo a conoscenza di 2 algoritmi per effettuare la procedura di chain discovery:

* la *backward search*, la quale permette di calcolare l'insieme di membri appartenenti ad un certo ruolo
* la *forward search*, la quale permette di calcolare l'insieme di ruoli assegnati ad un certo membro
* l'esecuzione di entrambi gli algoritmi contemporaneamente permette di verificare l'assegnamento di un certo ruolo ad un certo membro

Abbiamo notato come entrambi gli algoritmi assolvano anche a verificare i loro rispettivi obiettivi complementari, ovvero permettano di accertare l'assenza di determinati membri all'interno di determinati ruoli.

In tutti i casi trattati sin ora (backward/forward, on-chain/off-chain), l'alta complessità di esecuzione delle procedure di chain discovery è motivata dalla costruzione del *proof graph*, che prevede l'esplorazione e la valutazione di tutte le credenziali potenzialmente in grado di contribuire alla formazione del risultato finale; per quanto sia vero che alcune di queste credenziali non apporteranno concretamente alcuna soluzione finale nell'insieme risultante, è importante osservare che la loro verifica risulta essenziale al fine di assolvere ai suddetti obiettivi complementari (in altre parole, non è possibile verificare l'effettiva assenza di un membro in un ruolo senza valutare ogni possibile credenziale coinvolta, per quanto essa non risulti nell'inserimento di alcuna soluzione concreta al risultato finale). In definitiva, dal momento in cui siamo interessati ad accertare l'assenza di determinati membri in determinati ruoli, la valutazione di tutte le credenziali tra loro correlate diviene essenziale.

Osservando vari possibili scenari, è stato appurato come il ricorso al chain discovery abbia come tipico obiettivo quello di verificare l'assegnamento di uno o più ruoli ad uno o più membri, piuttosto che la verifica del complementare. In tal caso, considerando l'esecuzione on-chain della procedura di chain discovery, non vi sarebbe alcun interesse nel garantire l'auditability nella valutazione di quelle credenziali che sicuramente non concorrerebbero alla costruzione dei risultati effettivi a cui siamo interessati. L'idea base diviene dunque quella di disporre di procedure off-chain in grado di individuare i sottoinsiemi minimi di credenziali presenti su blockchain utili a verificare l'assegnamento di uno o più ruoli ad uno o più membri. Fornito tale sottoinsieme alla procedura di chain discovery on-chain, questa presenterebbe un costo di esecuzione minore in quanto l'espansione del proof graph sarebbe garantita limitarsi alle sole credenziali effettivamente utili all'ottenimento delle soluzioni che siamo interessati verificare garantendo il secure computing.

Tuttavia, per quanto operante su un insieme più ristretto di credenziali, la complessità della procedura di chain discovery si manterrebbe invariata in quanto sarebbe comunque prevista la costruzione di un proof graph. Da qui l'idea di ricorrere piuttosto ad un algoritmo di verifica on-chain [...]



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

