import sys;
from DART import *
from pprint import pprint

# EPapers.canAccess ←− EOrg.member ∩ EOrg.student
# EOrg.student ←− EOrg.university.student
# EOrg.university ←− StateA.university
# StateA.university ←− UniA
# UniA.student <- Alice
# EOrg.member <- Alice

# ----------------------------------------------------- 

if len(sys.argv) < 4:
    print("Usage: DART_build_artifact_path endpoint_URI network_id [load / test]")
    sys.exit(-1)

buildArtifactPath = sys.argv[1]
endpointURI = sys.argv[2]
networkID = sys.argv[3]

loadOnly = False
testOnly = False
if len(sys.argv) > 4:
    if sys.argv[4] == 'load':
        loadOnly = True
    elif sys.argv[4] == 'test':
        testOnly = True

# Inizializza web3 connettendolo al provider locale ganache
w3 = Web3(Web3.HTTPProvider(endpointURI))
accounts = w3.eth.accounts;
w3.eth.defaultAccount = accounts[0]

if len(accounts) < 5:
    print("Not enough available Ethereum accounts! At least 5 accounts are needed in order to run this test")

# Inizializza l'interfaccia per interagire con lo smart contract DART
DARTArtifact = json.load(open(buildArtifactPath))
d = DART(DARTArtifact['abi'], DARTArtifact['networks'][networkID]['address'], w3)

# ----------------------------------------------------- 

# Per facilitare la stesura dei test e la lettura dei risultati
# realizza due coppie di dizionari per legare:

# ... principals ad address e viceversa
PR = {
    'EPapers': accounts[0],
    'EOrg': accounts[1],
    'StateA': accounts[2],
    'UniA': accounts[3],
    'Alice': accounts[4]
}
INV_PR = {v: k for k, v in PR.items()}
print("\nPRINCIPALS:")
pprint(PR)

# ... rolenames esadecimali a rolenames stringhe e viceversa
RN = {
    'canAccess': '0x000a',
    'student': '0x000b',
    'member': '0x000c',
    'university': '0x000d',
    'student': '0x000e'
}
INV_RN = {v: k for k, v in RN.items()}
print("\nROLENAMES:")
pprint(RN)

# Funzione di utilità per convertire una Expression in una stringa human-readable
def expr2str(expr):
    if isinstance(expr, SMExpression):
        return INV_PR[expr.member]
    elif isinstance(expr, SIExpression):
        return INV_PR[expr.principal] + "." + INV_RN[expr.roleName]
    elif isinstance(expr, LIExpression):
        return INV_PR[expr.principal] + "." + INV_RN[expr.roleNameA] + "." + INV_RN[expr.roleNameB]
    elif isinstance(expr, IIExpression):
        return INV_PR[expr.principalA] + "." + INV_RN[expr.roleNameA] + " ∩ " + INV_PR[expr.principalB] + "." + INV_RN[expr.roleNameB]


# ----------------------------------------------------- 

if loadOnly or (not loadOnly and not testOnly):
    # Registra ruoli e credenziali per istanziare la policy di test EPapers
    print("Loading policy... ", end='')

    d.newRole(RN['canAccess'], {'from': PR['EPapers']})
    d.newRole(RN['student'], {'from': PR['EOrg']})
    d.newRole(RN['member'], {'from': PR['EOrg']})
    d.newRole(RN['university'], {'from': PR['EOrg']})
    d.newRole(RN['university'], {'from': PR['StateA']})
    d.newRole(RN['student'], {'from': PR['UniA']})

    # EOrg.member <- Alice
    d.addSimpleMember(RN['member'], SMExpression(PR['Alice']), 100, {'from': PR['EOrg']})
    # UniA.student <- Alice
    d.addSimpleMember(RN['student'], SMExpression(PR['Alice']), 100, {'from': PR['UniA']})
    # StateA.university ←− UniA
    d.addSimpleMember(RN['university'], SMExpression(PR['UniA']), 100, {'from': PR['StateA']})
    # EOrg.university ←− StateA.university
    d.addSimpleInclusion(RN['university'], SIExpression(PR['StateA'], RN['university']), 100, {'from': PR['EOrg']})
    # EOrg.student ←− EOrg.university.student
    d.addLinkedInclusion(RN['student'], LIExpression(PR['EOrg'], RN['university'], RN['student']), 100, {'from': PR['EOrg']})
    # EPapers.canAccess ←− EOrg.member ∩ EOrg.student
    d.addIntersectionInclusion(RN['canAccess'], IIExpression(PR['EOrg'], RN['student'], PR['EOrg'], RN['member']), 50, {'from': PR['EPapers']})

    print("Done")

# ----------------------------------------------------- 

if testOnly or (not loadOnly and not testOnly):
    # Effettua una ricerca locale di tutti i membri a cui risulta assegnato il ruolo EPapers.canAccess
    print('\nExecuting off-line credential chain discovery on EPapers.canAccess ... ', end='')
    solutions = d.search(SIExpression(PR['EPapers'], RN['canAccess']))
    print(f"Found solutions: {len(solutions)}")

    # Per ciascun membro trovato, costruiscine la dimostrazione per il metodo di verifica on-chain sulla base dei paths nelle soluzioni
    for idx, currSol in enumerate(solutions.values()):
        print(f'\nSolution #{idx+1}: member={INV_PR[currSol.member]}, weight={currSol.weight}')
        proofStrs = []
        proof = []
        for currEdge in currSol.path:
            if not isinstance(currEdge.toNode.expr, LIExpression):
                proofStrs.append(expr2str(currEdge.toNode.expr) + ' ←- ' + expr2str(currEdge.fromNode.expr))
                proof.append(currEdge.toNode.expr.id)
                proof.append(currEdge.fromNode.expr.id)

        # Verifica la dimostrazione on-chain
        print('Constructed verification proof:')
        pprint(proofStrs)
        print(f'Required stack size: {currSol.reqStackSize}')
        verifGas = d.contract.functions.verifyProof(proof, currSol.reqStackSize).estimateGas()
        verifRes = d.verifyProof(proof, currSol.reqStackSize)
        if verifRes['principal'] != accounts[i] or verifRes['rolename'] != RN['trust'] or verifRes['member'] != currSol.member or verifRes['weight'] != int(currSol.weight):
            print("ERROR: invalid proof for current solution!")
        else:
            verifRes['principal'] = INV_PR[verifRes['principal']]
            verifRes['rolename'] = INV_RN[verifRes['rolename']]
            verifRes['member'] = INV_PR[verifRes['member']]
        
        print(f'On-chain verification gas: {verifGas}')
        print(f'On-chain verification result: {verifRes}')
