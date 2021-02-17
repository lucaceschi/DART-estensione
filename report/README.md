A seguito della implementazione on-chain dell'algoritmo *backward search* per il *credential chain discovery*, abbiamo osservato che il costo necessario alla sua esecuzione risulta eccessivamente elevato, rendendone difficile l'adozione nel contesto di blockchain pubbliche ove siano presenti limitazioni in termini di gas.

Il nuovo obiettivo è stato dunque quello di comprendere meglio le motivazioni e gli interessi alla base di tale implementazione, nonché la ricerca di una soluzione meno costosa.

È stato osservato anzitutto come la necessità di eseguire on-chain le procedure di credential chain discovery abbia origine dall'interesse di rendere verificabili e trasparenti i calcoli in questione, e che ciò occorra principalmente in tutti quei casi e scenari per cui al risultato di elaborazione delle credenziali memorizzate su blockchain conseguano degli obblighi/interessi collettivi piuttosto che individuali. D'altra parte, ricerche i cui esiti interessano e hanno conseguenze unicamente a livello individuale, potrebbero essere eseguite off-chain dall'individuo stesso senza necessariamente ricorrere al consenso distribuito per il calcolo. Siamo a conoscenza di 2 algoritmi per effettuare la procedura di chain discovery:

* la *backward search*, la quale permette di calcolare l'insieme di membri appartenenti ad un certo ruolo
* la *forward search*, la quale permette di calcolare l'insieme di ruoli assegnati ad un certo membro
* l'esecuzione di entrambi gli algoritmi contemporaneamente permette di verificare l'assegnamento di un certo ruolo ad un certo membro

Abbiamo notato come entrambi gli algoritmi assolvano anche a verificare i loro rispettivi obiettivi complementari, ovvero permettano di accertare l'assenza di determinati membri all'interno di determinati ruoli.

In tutti i casi trattati sin ora (backward/forward, on-chain/off-chain), l'alta complessità di esecuzione delle procedure di chain discovery è motivata dalla costruzione del *proof graph*, che prevede l'esplorazione e la valutazione di tutte le credenziali potenzialmente in grado di contribuire alla formazione del risultato finale; per quanto sia vero che alcune di queste credenziali non apporteranno concretamente alcuna soluzione finale nell'insieme risultante, è importante osservare che la loro verifica risulta essenziale al fine di assolvere ai suddetti obiettivi complementari (in altre parole, non è possibile verificare l'effettiva assenza di un membro in un ruolo senza valutare ogni possibile credenziale coinvolta). In definitiva, dal momento in cui siamo interessati ad accertare l'assenza di determinati membri in determinati ruoli, la valutazione di tutte le credenziali tra loro correlate diviene essenziale.

Osservando vari possibili scenari, è stato appurato come il ricorso al chain discovery abbia come tipico obiettivo quello di verificare l'assegnamento di uno o più ruoli ad uno o più membri, piuttosto che la verifica del complementare. In tal caso, considerando l'esecuzione on-chain della procedura di chain discovery, non vi sarebbe alcun interesse nel garantire l'auditability nella valutazione di quelle credenziali che sicuramente non concorrerebbero alla costruzione dei risultati effettivi a cui siamo interessati. L'idea base diviene dunque quella di disporre di procedure off-chain in grado di individuare i sottoinsiemi minimi di credenziali presenti su blockchain utili a verificare un prestabilito assegnamento di uno o più ruoli ad uno o più membri.

Si consideri come esempio la seguente policy:

```
EPapers.canAccess ← EOrg.member ∩ EOrg.student
EOrg.student ← EOrg.university.student

EOrg.university ← StateA.university
EOrg.university ← StateB.university
[...]

StateA.university ← UniA1
StateA.university ← UniA2
StateA.university ← [...]
StateB.university ← UniB1
StateB.university ← UniB2
StateB.university ← [...]
[...]

UniA1.student ← Alice
UniA1.student ← Bob
[...]

UniB1.student ← Charlie
UniB1.student ← David
[...]

EOrg.member ← Alice
[...]
```

Siamo interessati a verificare che al principal *Alice* sia assegnato il ruolo *EPapers.canAccess*. In figura troviamo rappresentato:

* il grafo (a) delle credenziali che costituisce la policy
* il proof graph (b) generato dal backward search algorithm avente come ruolo oggetto della ricerca *EPapers.canAccess*. In blu sono evidenziati gli archi generati dall'algoritmo
* evidenziato in rosso (c) la porzione di proof graph che sarebbe stata sufficiente generare per provare ciò a cui siamo interessati

![](./img/epapers_proofgraph.svg)

Eseguendo tale processo off-chain, saremmo in grado di stabilire che il sottoinsieme minimale di credenziali utili a verificare che *Alice* abbia assegnato il ruolo è composto dalle sole seguenti credenziali:

```
EPapers.canAccess ← EOrg.member ∩ EOrg.student
EOrg.student ← EOrg.university.student
EOrg.university ← StateA.university
StateA.university ← UniA1
UniA1.student ← Alice
EOrg.member ← Alice
```



Una volta trovato tale sottoinsieme, esso verrà fornito alla procedura di chain discovery on-chain la quale presenterà un costo di esecuzione minore o uguale rispetto alla esecuzione della stessa chain discovery sull'intero insieme delle credenziali: ciò accade in quanto l'espansione del proof graph sarebbe garantita limitarsi alle sole credenziali effettivamente utili all'ottenimento delle soluzioni che siamo interessati a verificare tramite secure computing.

Tuttavia, per quanto operante su un insieme ristretto di credenziali, la complessità della procedura di chain discovery si manterrebbe dello stesso ordine, in quanto sarebbe comunque prevista la costruzione di un proof graph. Da qui l'idea piuttosto di ricorrere a:

* un algoritmo off-chain che includa:
  * l'esecuzione (locale) di un chain discovery esteso a tutte le credenziali attualmente presenti on-chain
  * l'individuazione del sottoinsieme minimo utile di credenziali
  * la costruzione di una dimostrazione sulla base di tale sottoinsieme
* un algoritmo on-chain in grado di verificare la dimostrazione garantendo secure computing

[...]