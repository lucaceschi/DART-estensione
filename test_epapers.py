import sys;
from DART import *
from pprint import pprint

# ----------------------------------------------------- 

if len(sys.argv) < 6:
    print("Usage: DART_build_artifact_path endpoint_URI network_id N_eligibles N_universities [load / test]")
    sys.exit(-1)

buildArtifactPath = sys.argv[1]
endpointURI = sys.argv[2]
networkID = sys.argv[3]
nEligibles = int(sys.argv[4])
nUniversities = int(sys.argv[5])

loadOnly = False
testOnly = False
if len(sys.argv) > 6:
    if sys.argv[6] == 'load':
        loadOnly = True
    elif sys.argv[6] == 'test':
        testOnly = True

# Inizializza web3 connettendolo al provider locale ganache
w3 = Web3(Web3.HTTPProvider(endpointURI))
accounts = w3.eth.accounts;
w3.eth.defaultAccount = accounts[0]

if len(accounts) < (3+nEligibles+nUniversities):
    print("Not enough available Ethereum accounts! At least (N_eligibles + N_universities + 3) accounts are needed in order to run this test")
    sys.exit(-1)

addressesOfEligibles = accounts[3:3+nEligibles]
addressesOfUniversities = accounts[3+nEligibles:3+nEligibles+nUniversities]

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
    'StateA': accounts[2]
}
for idx, addr in enumerate(addressesOfEligibles):
    PR['Principal[' + str(idx+1) + ']'] = addr
for idx, addr in enumerate(addressesOfUniversities):
    PR['Uni[' + str(idx+1) + ']'] = addr
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
    for uniAddr in addressesOfUniversities:
        d.newRole(RN['student'], {'from': uniAddr})

    for idx, principalAddr in enumerate(addressesOfEligibles):
        # Registra il principal a EOrg.member
        d.addSimpleMember(RN['member'], SMExpression(principalAddr), 100, {'from': PR['EOrg']})
        # Registra il principal come studente di una delle università
        d.addSimpleMember(RN['student'], SMExpression(principalAddr), 100, {'from': addressesOfUniversities[idx % len(addressesOfUniversities)]})
    for uniAddr in addressesOfUniversities:
        # StateA.university ←− Uni_X
        d.addSimpleMember(RN['university'], SMExpression(uniAddr), 100, {'from': PR['StateA']})
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
    print("\nSearching... ", end='')
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
        print('On-chain verification proof:')
        pprint(proofStrs)

        verifGas = d.contract.functions.verifyProof(proof, currSol.reqStackSize).estimateGas()
        verifRes = d.verifyProof(proof, currSol.reqStackSize)
        if verifRes['principal'] != PR['EPapers'] or verifRes['rolename'] != RN['canAccess'] or verifRes['member'] != currSol.member:
            print("ERROR: invalid proof for current solution!")
        else:
            verifRes['principal'] = INV_PR[verifRes['principal']]
            verifRes['rolename'] = INV_RN[verifRes['rolename']]
            verifRes['member'] = INV_PR[verifRes['member']]
        print(f'On-chain verification gas: {verifGas}')
        print(f'On-chain verification result: {verifRes}')
