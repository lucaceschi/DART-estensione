import json
from web3 import Web3
from hexbytes import HexBytes
from collections import deque

NULL_PRINCIPAL = "0x0000000000000000000000000000000000000000"
NULL_ROLENAME = "0x0000"
MAX_WEIGHT = 100

"""
------------------------------------------------------------------------------------
ESPRESSIONI
------------------------------------------------------------------------------------
"""

class Expression:
    """
    Interfaccia per una generica espressione.
    
    Ogni espressione deve essere inizializzata con un identificativo,
    sulla cui base è definito l'operatore di uguaglianza tra espressioni.
    La generazione di tale identificativo varia a seconda del tipo di espressione
    e corrisponde allo stesso metodo utilizzato da parte del contratto on-chain
    """

    def __init__(self, id):
        self.id = id

    def __hash__(self):
        return Web3.toInt(self.id)

    def __eq__(self, other):
        return self.id == other.id


class SMExpression(Expression):
    """
    Record di dati rappresentante una role expression per una credenziale Simple Member
    """

    def __init__(self, member):
        b = bytes(HexBytes(member))
        # L'identificativo di una simple member è l'indirizzo del membro stesso
        # seguito da una sequenza di zeri
        super().__init__(HexBytes(b.ljust(32, b'\x00')))
        self.member = member

    def __iter__(self):
        yield from [self.member]


class SIExpression(Expression):
    """
    Record di dati rappresentante una role expression per una credenziale Simple Inclusion
    o un assigned role di una qualsiasi credenziale
    """
    
    def __init__(self, principal, roleName):
        # L'identificativo di una simple inclusion è generata applicando la funzione di hashing sui propri dati
        super().__init__(Web3.solidityKeccak(['address', 'bytes2', 'address', 'bytes2'], [principal, roleName, NULL_PRINCIPAL, NULL_ROLENAME]))
        self.principal = principal
        self.roleName = roleName

    def __iter__(self):
        yield from [self.principal, self.roleName]


class LIExpression(Expression):
    """
    Record di dati rappresentante una role expression per una credenziale Linked Inclusion
    """

    def __init__(self, principal, roleNameA, roleNameB):
        # L'identificativo di una linked inclusion è generato applicando la funzione di hashing sui propri dati
        super().__init__(Web3.solidityKeccak(['address', 'bytes2', 'address', 'bytes2'], [principal, roleNameA, NULL_PRINCIPAL, roleNameB]))
        self.principal = principal
        self.roleNameA = roleNameA
        self.roleNameB = roleNameB

    def __iter__(self):
        yield from [self.principal, self.roleNameA, self.roleNameB]


class IIExpression(Expression):
    """
    Record di dati rappresentante una role expression per una credenziale Intersection Inclusion
    """

    def __init__(self, principalA, roleNameA, principalB, roleNameB):
        # L'identificativo di una intersection inclusion è generato applicando la funzione di hashing sui propri dati
        # i quali sono anzitutto ordinati in modo da considerare equivalenti le espressioni P1.r1 ∩ P2.r2 e P2.r2 ∩ P1.r1
        if ((HexBytes(principalB) > HexBytes(principalA)) or (HexBytes(principalA) == HexBytes(principalB) and HexBytes(roleNameB) > HexBytes(roleNameA))):
            principalA, roleNameA, principalB, roleNameB = principalB, roleNameB, principalA, roleNameA
        super().__init__(Web3.solidityKeccak(['address', 'bytes2', 'address', 'bytes2'], [principalA, roleNameA, principalB, roleNameB]))
        self.principalA = principalA
        self.roleNameA = roleNameA
        self.principalB = principalB
        self.roleNameB = roleNameB

    def __iter__(self):
        yield from [self.principalA, self.roleNameA, self.principalB, self.roleNameB]


"""
------------------------------------------------------------------------------------
ADT DI SUPPORTO PER ALGORITMO DI RICERCA
------------------------------------------------------------------------------------
"""

class Solution:
    """
    Record di dati rappresentante una soluzione posseduta da un ProofNode.

    member: l'indirizzo del principal oggetto della soluzione
    weight: il valore di fiducia associato alla soluzione
    path: sequenza di ProofEdge(s) attraversati dalla soluzione per giungere al ProofNode in possesso della soluzione stessa
    reqStackSize: dimensione della stack sufficiente affinché la soluzione possa essere verificata on-chain
    """

    def __init__(self, member, weight, path = [], reqStackSize = 1):
        self.member = member
        self.weight = weight
        self.path = path
        self.reqStackSize = reqStackSize


class Monitor:
    """
    Interfaccia per un generico monitor del backward search algorithm.

    Ogni monitor possiede:
    - destNode: il ProofNode a cui saranno inviate le soluzioni
    - proofGraph: il ProofGraph in cui inserire eventuali nuovi nodi o archi
    - dart: l'istanza di interfacciamento al contratto dart on-chain su cui è eseguita la ricerca
    - notify(): metodo per notificare al monitor una nuova soluzione
    """

    def __init__(self, destNode, proofGraph, dart):
        self.destNode = destNode
        self.proofGraph = proofGraph
        self.dart = dart

    def notify(self, solution, fromNode):
        pass


class LinkingMonitor(Monitor):
    """
    Monitor per gestire le inclusioni linkate.

    Un LinkingMonitor per gestire credenziali Linked Inclusion A.a <- P.r1.r2:
    - ha come nodo destinazione destNode il ProofNode rappresentante l'espressione A.a
    - viene notificato alla ricezione di nuove soluzioni da parte del ProofNode rappresentante l'espressione P.r1
    """

    def __init__(self, destNode, proofGraph, dart):
        super().__init__(destNode, proofGraph, dart)

    def notify(self, solution, fromNode=None):
        # Notifica di ricezione di una nuova soluzione solution da parte di P.r1
        # Aggiungi, se non presente, un nuovo nodo rappresentante l'espressione (solution.member).r2
        # ed un arco tra di esso e P.r1.r2 pesato con lo stesso valore di fiducia di solution

        linkedRole = SIExpression(solution.member, self.destNode.expr.roleNameB)
        if self.dart.exprExists(linkedRole):
            self.proofGraph.addNode(linkedRole)
            self.proofGraph.addEdge(linkedRole, self.destNode.expr, solution.weight, solution)


class IntersectionMonitor(Monitor):
    """
    Monitor per gestire le inclusioni intersecate.

    Una IntersectionMonitor per gestire credenziali Intersection Inclusion A.a <- P1.r1 ∩ P2.r2:
    - ha come nodo destinazione destNode il ProofNode rappresentante l'espressione A.a
    - viene notificato alla ricezione di nuove soluzioni da parte dei ProofNode rappresentanti le espressioni P1.r1 e P2.r2
    """

    def __init__(self, destNode, proofGraph, dart):
        super().__init__(destNode, proofGraph, dart)
        self.solutionsA = {}
        self.solutionsB = {}
        self.roleA = SIExpression(destNode.expr.principalA, destNode.expr.roleNameA)
        self.roleB = SIExpression(destNode.expr.principalB, destNode.expr.roleNameB)
    
    def notify(self, solution, fromNode):
        # Notifica di ricezione di una nuova soluzione solution da parte di uno dei due nodi P1.r1 o P2.r2.
        # Aggiungi la soluzione al relativo insieme di soluzioni da esse notificate se nuova o con valore di fiducia maggiore.
        # Se risultano presenti in entrambi gli insiemi due soluzioni con medesimo membro oggetto,
        # invia al destNode una nuova soluzione composta da:
        # - il membro in questione
        # - il valore di fiducia minimo tra le due soluzioni
        # - come path una concatenazione dei paths delle due soluzioni, ponendo prima la più corta
        # - una reqStackSize sufficiente a verificare on-chain la sequenza di credenziali rappresentata dalla suddetta concatenazione dei path

        if fromNode.expr == self.roleA:
            solutions = self.solutionsA
            otherSolutions = self.solutionsB
        elif fromNode.expr == self.roleB:
            solutions = self.solutionsB
            otherSolutions = self.solutionsA
        else:
            return

        if solution.member not in solutions or solutions[solution.member].weight < solution.weight:
            solutions[solution.member] = solution
            if solution.member in otherSolutions:
                
                otherSolution = otherSolutions[solution.member]
                outputWeight = min(solution.weight, otherSolution.weight)

                if solution.reqStackSize > otherSolution.reqStackSize:
                    outputPath = solution.path + otherSolution.path
                    outputReqStackSize = solution.reqStackSize
                elif solution.reqStackSize < otherSolution.reqStackSize:
                    outputPath = otherSolution.path + solution.path
                    outputReqStackSize = otherSolution.reqStackSize
                else:
                    outputPath = solution.path + otherSolution.path
                    outputReqStackSize = solution.reqStackSize + 1

                intersectedSolution = Solution(solution.member, outputWeight, outputPath, outputReqStackSize)
                self.destNode.addSolution(intersectedSolution)


class ProofEdge:
    """
    ADT rappresentante un arco orientato del ProofGraph.

    fromNode: il nodo ProofNode sorgente
    toNode: il nodo ProofNode destinazione
    weight: il peso associato all'arco
    supportSolution: eventuale soluzione che ha giustificato la generazione dell'arco
    """

    def __init__(self, fromNode, toNode, weight, supportSolution = None):
        self.fromNode = fromNode
        self.toNode = toNode
        self.weight = weight
        self.supportSolution = supportSolution

    def sendSolution(self, solution):
        # Trasmetti una soluzione attraverso l'arco:
        # la soluzione viene anzitutto firmata con il metodo signSolution()
        # quindi aggiunta alle soluzioni del nodo destinazione
        self.toNode.addSolution(self.signSolution(solution))

    def signSolution(self, solution):
        # Firma una soluzione che attraversa l'arco. Una volta firmata, valgono le seguenti affermazioni:
        # - il valore di fiducia della soluzione è stato aggravato dal peso dell'arco
        # - al path della soluzione è stato accodato l'arco stesso
        # - se l'arco possiede una supportSolution, è stato accodato al path anche il path di supportSolution
        # - reqStackSize è stato aggiornato e reso sufficiente a verificare on-chain la sequenza di credenziali rappresentata dalla suddetta path
        newWeight = (solution.weight * self.weight) / MAX_WEIGHT
        if self.supportSolution == None:
            newPath = solution.path + [self]
            newReqStackSize = solution.reqStackSize
        else:
            newPath = solution.path + [self] + self.supportSolution.path
            if solution.reqStackSize > self.supportSolution.reqStackSize:
                newReqStackSize = solution.reqStackSize
            else:
                newReqStackSize = self.supportSolution.reqStackSize + 1
        
        return Solution(solution.member, newWeight, newPath, newReqStackSize)


class ProofNode:
    """
    ADT rappresentante un nodo del ProofGraph.

    expr: l'espressione (SM/SI/LI/II)Expression rappresentata dal nodo
    outEdges: insieme degli archi uscenti
    solutions: insieme delle soluzioni possedute dal nodo
    solutionsState: valore corrispondente ad un determinato stato di solutions, incrementato ad ogni alterazione di solutions
    monitors: insieme dei monitor a cui notificare l'inserimento di una nuova soluzione in solutions
    """

    def __init__(self, expr):
        self.expr = expr
        self.outEdges = {}
        self.solutions = {}
        self.solutionsState = 0
        self.monitors = []

    def addSolution(self, solution):
        # Richiede l'inserimento di solution tra le soluzioni solutions del nodo.
        # La soluzione è accettata solamente se tratta di un nuovo membro o possiede un valore di fiducia maggiore.
        # Se accettata:
        # - viene aggiornato il contatore di stato solutionsState
        # - viene trasmessa la soluzione attraverso tutti gli archi uscenti
        # - vengono notificati tutti i monitor della nuova soluzione
        if solution.member not in self.solutions or self.solutions[solution.member].weight < solution.weight:
            self.solutions[solution.member] = solution
            self.solutionsState += 1
            for monitor in self.monitors:
                monitor.notify(solution, self)
            for edge in self.outEdges.values():
                edge.sendSolution(solution)

    def attachMonitor(self, monitor):
        # Associa un nuovo monitor al nodo.
        # Se il nodo possiede delle soluzioni, notificale tutte al nuovo monitor.
        # Quest'ultima operazione potrebbe comportare la ricezione di nuove soluzioni,
        # dunque è necessario operare su di una copia dell'insieme delle soluzioni
        self.monitors.append(monitor)
        if len(self.solutions) != 0:
            while True:
                currSolutionsState = self.solutionsState
                solutionsList = list(self.solutions.values())
                for solution in solutionsList:
                    monitor.notify(solution, self)
                if currSolutionsState == self.solutionsState:
                    break


class ProofGraph:
    """
    ADT rappresentante un grafo generato dal backward search algorithm.

    nodes: insieme dei nodi ProofGraph di cui il grafo è composto
    queue: coda di ProofNode(s) utilizzata da parte dal backward search algorithm per generare il grafo
    """

    def __init__(self):
        self.nodes = {}
        self.queue = deque()

    def addNode(self, expr):
        # Richiede l'inserimento di nuovo nodo nel grafo.
        # Il nodo è accettato solamente se rappresentante una nuova espressione.
        # A seguito dell'accettazione, è accodato nella coda di elaborazione del backward search algorithm
        if expr not in self.nodes:
            newNode = ProofNode(expr)
            self.nodes[expr] = newNode
            self.queue.append(newNode)
            return newNode
        else:
            return self.nodes[expr]

    def addEdge(self, fromExpr, toExpr, weight, supportSolution = None):
        # Richiede l'inserimento di un nuovo arco nel grafo.
        # L'arco è accettato solamente se non presente, o se presente con un valore di fiducia minore.
        # L'inserimento di un nuovo arco comporta il trasferimento di eventuali soluzioni
        # dal nodo sorgente al nodo destinazione.
        # Quest'ultima operazione potrebbe comportare la ricezione di nuove soluzioni da parte del nodo sorgente,
        # dunque è necessario operare su di una copia dell'insieme delle soluzioni
        if fromExpr in self.nodes and toExpr in self.nodes:
            fromNode = self.nodes[fromExpr]
            toNode = self.nodes[toExpr]
            newEdge = ProofEdge(fromNode, toNode, weight, supportSolution)
            if toNode not in fromNode.outEdges or fromNode.outEdges[toNode].weight < weight:
                fromNode.outEdges[toNode] = newEdge
                while True:
                    currSolutionsState = fromNode.solutionsState
                    solutionsList = list(fromNode.solutions.values())
                    for solution in solutionsList:
                        newEdge.sendSolution(solution)
                    if currSolutionsState == fromNode.solutionsState:
                        break

"""
------------------------------------------------------------------------------------
DART
------------------------------------------------------------------------------------
"""

class DART:
    """
    Classe per l'interfacciamento verso il contratto DART on-chain.
    """

    def __init__(self, contractABI, contractAddress, w3):
        """
        Crea una nuova istanza di interfacciamento verso un contratto DART on-chain.

        :param buildArtifactPath: path all'artefatto json prodotto dalla compilazione del contratto DART tramite suite truffle
        :param contractABI: array rappresentante l'ABI del contratto DART
        :param w3: istanza di Web3 connesso ad un nodo della blockchain su cui è istanziato il contratto DART all'indirizzo fornito
        """
        self.contract = w3.eth.contract(abi=contractABI, address=contractAddress)
        self.w3 = w3

    def newRole(self, roleName, tx={}):
        """
        Richiedi la creazione di un nuovo ruolo
        
        :param roleName: stringa rappresentante un valore esadecimale valido (es: 0xabcd) identificativo del nuovo ruolo
        :param tx: parametro opzionale contenente eventuali preferenze per la transazione
        """
        self.contract.functions.newRole(roleName).call(tx)
        txHash = self.contract.functions.newRole(roleName).transact(tx)
        self.w3.eth.waitForTransactionReceipt(txHash)

    def addSimpleMember(self, assignedRolename, expression, weight, tx={}):
        """
        Richiedi l'inserimento di una nuova credenziale Simple Member per un proprio ruolo
        
        :param assignedRolename: il rolename dell'assigned role della credenziale
        :param expression: la role expression SMExpression della credenziale
        :param weight: valore di fiducia associato alla credenziale
        :param tx: parametro opzionale contenente eventuali preferenze per la transazione
        """
        self.contract.functions.addSimpleMember(assignedRolename, *expression, weight).call(tx)
        txHash = self.contract.functions.addSimpleMember(assignedRolename, *expression, weight).transact(tx)
        self.w3.eth.waitForTransactionReceipt(txHash)

    def addSimpleInclusion(self, assignedRolename, expression, weight, tx={}):
        """
        Richiedi l'inserimento di una nuova credenziale Simple Inclusion per un proprio ruolo
        
        :param assignedRolename: il rolename dell'assigned role della credenziale
        :param expression: la role expression SIExpression della credenziale
        :param weight: valore di fiducia associato alla credenziale
        :param tx: parametro opzionale contenente eventuali preferenze per la transazione
        """
        self.contract.functions.addSimpleInclusion(assignedRolename, *expression, weight).call(tx)
        txHash = self.contract.functions.addSimpleInclusion(assignedRolename, *expression, weight).transact(tx)
        self.w3.eth.waitForTransactionReceipt(txHash)

    def addLinkedInclusion(self, assignedRolename, expression, weight, tx={}):
        """
        Richiedi l'inserimento di una nuova credenziale Linked Inclusion per un proprio ruolo
        
        :param assignedRolename: il rolename dell'assigned role della credenziale
        :param expression: la role expression LIExpression della credenziale
        :param weight: valore di fiducia associato alla credenziale
        :param tx: parametro opzionale contenente eventuali preferenze per la transazione
        """
        self.contract.functions.addLinkedInclusion(assignedRolename, *expression, weight).call(tx)
        txHash = self.contract.functions.addLinkedInclusion(assignedRolename, *expression, weight).transact(tx)
        self.w3.eth.waitForTransactionReceipt(txHash)

    def addIntersectionInclusion(self, assignedRolename, expression, weight, tx={}):
        """
        Richiedi l'inserimento di una nuova credenziale Intersection Inclusion per un proprio ruolo
        
        :param assignedRolename: il rolename dell'assigned role della credenziale
        :param expression: la role expression IIExpression della credenziale
        :param weight: valore di fiducia associato alla credenziale
        :param tx: parametro opzionale contenente eventuali preferenze per la transazione
        """
        self.contract.functions.addIntersectionInclusion(assignedRolename, *expression, weight).call(tx)
        txHash = self.contract.functions.addIntersectionInclusion(assignedRolename, *expression, weight).transact(tx)
        self.w3.eth.waitForTransactionReceipt(txHash)

    # --------------------------------------------------------------------------------
    # TODO: operazioni di rimozione di credenziali ed aggiornamento dei valori di fiducia
    # --------------------------------------------------------------------------------

    def exprExists(self, expr):
        """        
        Restituisce True se l'espressione expr:Expression fornita risulta parte di almeno una credenziale
        registrata sul contratto on-chain da parte di un qualsiasi principal
        """
        return self.contract.functions.exprExists(expr.id).call()

    def getMembersCount(self, role):
        """
        Restituisce il numero di credenziali Simple Member aventi role:SIExpression come assigned role
        """
        return self.contract.functions.getMembersCount(role.id).call()

    def getMember(self, role, memberIndex):
        """
        Restituisce il memberIndex-esimo membro associato tramite credenziale Simple Member al ruolo role:SIExpression
        """
        (address, weight) = self.contract.functions.getMember(role.id, memberIndex).call()
        return (SMExpression(address), weight)

    def getInclusionsCount(self, role):
        """
        Restituisce il numero di credenziali di inclusione (simple, linked, intersection)
        aventi role:SIExpression come assigned role
        """
        return self.contract.functions.getInclusionsCount(role.id).call()

    def getInclusion(self, role, inclusionIndex):
        """
        Restituisce la inclusionIndex-esima credenziale di inclusione avente role:SIExpression come assigned role
        """
        (addrA, addrB, roleA, roleB, weight) = self.contract.functions.getInclusion(role.id, inclusionIndex).call()
        roleA = Web3.toHex(roleA)
        roleB = Web3.toHex(roleB)
        if addrB != NULL_PRINCIPAL:
            return (IIExpression(addrA, roleA, addrB, roleB), weight)
        elif roleB != NULL_ROLENAME:
            return (LIExpression(addrA, roleA, roleB), weight)
        else:
            return (SIExpression(addrA, roleA), weight)

    def search(self, role):
        """
        Esegue il backward search algorithm a partire dal ruolo role:SMExpression fornito,
        restituendo infine l'insieme delle soluzioni trovate per tale ruolo
        """
        proofGraph = ProofGraph()
        startingNode = proofGraph.addNode(role)
        
        while len(proofGraph.queue) != 0:
            currNode = proofGraph.queue.popleft()

            if isinstance(currNode.expr, SMExpression):
                currNode.addSolution(Solution(currNode.expr.member, MAX_WEIGHT))

            elif isinstance(currNode.expr, SIExpression):
                nMembers = self.getMembersCount(currNode.expr)
                for i in range(0, nMembers):
                    (memberExpr, credWeight) = self.getMember(currNode.expr, i)
                    proofGraph.addNode(memberExpr)
                    proofGraph.addEdge(memberExpr, currNode.expr, credWeight)
                nInclusions = self.getInclusionsCount(currNode.expr)
                for i in range(0, nInclusions):
                    (inclExpr, credWeight) = self.getInclusion(currNode.expr, i)
                    proofGraph.addNode(inclExpr)
                    proofGraph.addEdge(inclExpr, currNode.expr, credWeight)
            
            elif isinstance(currNode.expr, LIExpression):
                linkingRole = SIExpression(currNode.expr.principal, currNode.expr.roleNameA)
                linkingRoleNode = proofGraph.addNode(linkingRole)
                linkingRoleNode.attachMonitor(LinkingMonitor(currNode, proofGraph, self))
            
            elif isinstance(currNode.expr, IIExpression):
                intersectedRoleA = SIExpression(currNode.expr.principalA, currNode.expr.roleNameA)
                intersectedRoleB = SIExpression(currNode.expr.principalB, currNode.expr.roleNameB)
                intersectedRoleNodeA = proofGraph.addNode(intersectedRoleA)
                intersectedRoleNodeB = proofGraph.addNode(intersectedRoleB)
                intersectionMonitor = IntersectionMonitor(currNode, proofGraph, self)
                intersectedRoleNodeA.attachMonitor(intersectionMonitor)
                intersectedRoleNodeB.attachMonitor(intersectionMonitor)

        return startingNode.solutions

    def verifyProof(self, proof, stackSize, tx={}):
        """
        Richiedi l'esecuzione dell'algoritmo di verifica on-chain

        :param proof: la sequenza di identificativi di espressioni che costituisce la dimostrazione
        :param stackSize: dimensione suggerita della stack di elaborazione
        :param tx: parametro opzionale contenente eventuali preferenze per la transazione
        """
        res = self.contract.functions.verifyProof(proof, stackSize).call(tx)
        return {'principal':res[0], 'rolename':Web3.toHex(res[1]), 'member':res[2], 'weight':res[3]}
