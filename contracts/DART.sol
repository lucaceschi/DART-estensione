pragma solidity >=0.8.1 <0.9;
pragma abicoder v2;

import "./dataStructures/WBytes32Set.sol";
import "./dataStructures/WAddressSet.sol";

contract DART {

    // Collega le librerie delle strutture dati ai relativi tipi
    using WBytes32Set for WBytes32Set.Set;
    using WAddressSet for WAddressSet.Set;

    // Definisci le costanti nulle per principals e rolenames
    address constant NULL_PRINCIPAL = address(0x0);
    bytes2 constant NULL_ROLENAME = 0x0000;

    // Definisci le costanti rappresentanti il valore di fiducia massimo
    uint constant MAX_WEIGHT = 100;
    uint8 constant MAX_WEIGHT_BYTE = 100;

    // Definisci le costanti identificative di ciascun tipo di role expression
    bytes1 constant EXPR_NC = 0x00;
    bytes1 constant EXPR_SI = 0x01;
    bytes1 constant EXPR_LI = 0x02;
    bytes1 constant EXPR_II = 0x03;

    // Definisci la struttura dati per rappresentare le role expressions
    struct Expression {
        bytes1 exprType;
        uint128 refCount;

        bytes2 roleA;
        bytes2 roleB;
        address addrA;
        address addrB;

        WBytes32Set.Set inclusions;
    }

    function packExpr(address addrA, bytes2 roleA, address addrB, bytes2 roleB) internal pure returns(bytes32) {
        return keccak256(abi.encodePacked(addrA, roleA, addrB, roleB));
    }

    function packExpr(address addrA, bytes2 roleA, bytes2 roleB) internal pure returns(bytes32) {
        return keccak256(abi.encodePacked(addrA, roleA, NULL_PRINCIPAL, roleB));
    }

    function packExpr(address addrA, bytes2 roleA) internal pure returns(bytes32) {
        return keccak256(abi.encodePacked(addrA, roleA, NULL_PRINCIPAL, NULL_ROLENAME));
    }

    // ----------------------------------------------------- //

    mapping(bytes32 => Expression) exprPool;
    mapping(bytes32 => WAddressSet.Set) members;

    modifier rolenameNotNull(bytes2 _rolename) {
        require(_rolename != 0x00, "invalid rolename");
        _;
    }

    function newRole(bytes2 _rolename)
            external rolenameNotNull(_rolename) {

        Expression storage expr = exprPool[packExpr(msg.sender, _rolename)];
        require(expr.exprType == EXPR_NC, "local role already exists");

        expr.exprType = EXPR_SI;
        expr.addrA = msg.sender;
        expr.roleA = _rolename;
    }

    function addSimpleMember(bytes2 _assignedRolename, address _member, uint8 _weight)
            external returns(bool) {

        bytes32 exprId = packExpr(msg.sender, _assignedRolename);
        require(exprPool[exprId].exprType == EXPR_SI, "local role does not exists");

        return members[exprId].insert(_member, _weight);
    }

    function removeSimpleMember(bytes2 _assignedRolename, address _member)
            external {

        bytes32 exprId = packExpr(msg.sender, _assignedRolename);
        require(exprPool[exprId].exprType == EXPR_SI, "local role does not exists");

        members[exprId].remove(_member);
    }

    function updateSimpleMember(bytes2 _assignedRolename, address _member, uint8 _newWeight)
            external {
        
        bytes32 exprId = packExpr(msg.sender, _assignedRolename);
        require(exprPool[exprId].exprType == EXPR_SI, "local role does not exists");

        members[exprId].update(_member, _newWeight);
    }

    function addSimpleInclusion(bytes2 _assignedRolename, address _principal, bytes2 _rolename, uint8 _weight)
            external returns(bool, bytes32) {

        Expression storage localRole = exprPool[packExpr(msg.sender, _assignedRolename)];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        bytes32 remoteRoleId = packExpr(_principal, _rolename);
        Expression storage remoteRole = exprPool[remoteRoleId];
        require(remoteRole.exprType == EXPR_SI, "remote role does not exists");

        return (localRole.inclusions.insert(remoteRoleId, _weight), remoteRoleId);
    }

    function removeSimpleInclusion(bytes2 _assignedRolename, bytes32 _exprId)
            external {

        bytes32 localRoleId = packExpr(msg.sender, _assignedRolename);
        Expression storage localRole = exprPool[localRoleId];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        require(exprPool[_exprId].exprType == EXPR_SI, "not a simple inclusion");
        localRole.inclusions.remove(_exprId);
    }

    function updateSimpleInclusion(bytes2 _assignedRolename, bytes32 _exprId, uint8 _newWeight)
            external {
        
        bytes32 localRoleId = packExpr(msg.sender, _assignedRolename);
        Expression storage localRole = exprPool[localRoleId];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        require(exprPool[_exprId].exprType == EXPR_SI, "not a simple inclusion");
        localRole.inclusions.update(_exprId, _newWeight);
    }

    function addLinkedInclusion(bytes2 _assignedRolename, address _principal, bytes2 _firstRolename, bytes2 _secondRolename, uint8 _weight)
            external returns(bool, bytes32) {

        Expression storage localRole = exprPool[packExpr(msg.sender, _assignedRolename)];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        require(exprPool[packExpr(_principal, _firstRolename)].exprType == EXPR_SI, "remote role does not exists");

        bytes32 linkedExprId = packExpr(_principal, _firstRolename, _secondRolename);
        Expression storage linkedExpr = exprPool[linkedExprId];
        if(linkedExpr.exprType == EXPR_NC) {
            linkedExpr.exprType = EXPR_LI;
            linkedExpr.addrA = _principal;
            linkedExpr.roleA = _firstRolename;
            linkedExpr.roleB = _secondRolename;
        }
        linkedExpr.refCount++;

        return (localRole.inclusions.insert(linkedExprId, _weight), linkedExprId);
    }

    function removeLinkedInclusion(bytes2 _assignedRolename, bytes32 _exprId)
            external {
    
        Expression storage localRole = exprPool[packExpr(msg.sender, _assignedRolename)];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        Expression storage expr = exprPool[_exprId];
        require(expr.exprType == EXPR_LI, "not a linked inclusion");
        localRole.inclusions.remove(_exprId);
        expr.refCount--;
        if(expr.refCount == 0) delete exprPool[_exprId];
    }

    function updateLinkedInclusion(bytes2 _assignedRolename, bytes32 _exprId, uint8 _newWeight)
            external {
    
        Expression storage localRole = exprPool[packExpr(msg.sender, _assignedRolename)];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        require(exprPool[_exprId].exprType == EXPR_LI, "not a linked inclusion");
        localRole.inclusions.update(_exprId, _newWeight);
    }
    
    function addIntersectionInclusion(bytes2 _assignedRolename, address _firstPrincipal, bytes2 _firstRolename,
            address _secondPrincipal, bytes2 _secondRolename, uint8 _weight) external
            returns (bool) {

        bytes32 localRoleId = packExpr(msg.sender, _assignedRolename);
        Expression storage localRole = exprPool[localRoleId];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        require(exprPool[packExpr(_firstPrincipal, _firstRolename)].exprType == EXPR_SI, "first remote role does not exists");

        require(exprPool[packExpr(_secondPrincipal, _secondRolename)].exprType == EXPR_SI, "second remote role does not exists");


        if((_secondPrincipal > _firstPrincipal) || (_firstPrincipal == _secondPrincipal && _secondRolename > _firstRolename))
            (_firstPrincipal, _firstRolename, _secondPrincipal, _secondRolename) = (_secondPrincipal, _secondRolename, _firstPrincipal, _firstRolename);

        bytes32 intersectionExprId = packExpr(_firstPrincipal, _firstRolename, _secondPrincipal, _secondRolename);
        Expression storage intersectionExpr = exprPool[intersectionExprId];
        if(intersectionExpr.exprType == EXPR_NC) {
            intersectionExpr.exprType = EXPR_II;
            intersectionExpr.addrA = _firstPrincipal;
            intersectionExpr.roleA = _firstRolename;
            intersectionExpr.addrB = _secondPrincipal;
            intersectionExpr.roleB = _secondRolename;
        }
        intersectionExpr.refCount++;

        return localRole.inclusions.insert(intersectionExprId, _weight);
    }

    function removeIntersectionInclusion(bytes2 _assignedRolename, bytes32 _exprId)
            external {

        Expression storage localRole = exprPool[packExpr(msg.sender, _assignedRolename)];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        Expression storage expr = exprPool[_exprId];
        require(expr.exprType == EXPR_II, "not an intersection inclusion");
        localRole.inclusions.remove(_exprId);
        expr.refCount--;
        if(expr.refCount == 0) delete exprPool[_exprId];
    }

    function updateIntersectionInclusion(bytes2 _assignedRolename, bytes32 _exprId, uint8 _newWeight)
            external {

        Expression storage localRole = exprPool[packExpr(msg.sender, _assignedRolename)];
        require(localRole.exprType == EXPR_SI, "local role does not exists");

        require(exprPool[_exprId].exprType == EXPR_II, "not an intersection inclusion");
        localRole.inclusions.update(_exprId, _newWeight);
    }

    // ----------------------------------------------------- //

    struct Solution {
        address principal;
        bytes2 rolename;
        address solution;
        uint8 weight;
    }

    function mulWeight(uint8 a, uint8 b) internal pure returns(uint8) {
        return uint8((uint(a) * uint(b)) / MAX_WEIGHT);
    }

    function verifyProof(bytes32[] calldata _proof, uint _stackSize) external view returns (Solution memory) {
        Solution[] memory solStack = new Solution[](_stackSize);
        uint i;
        uint j;

        Expression storage currAssignedRole;
        Expression storage currRoleExpr;
        address currMember;

        for(i = 0; i < _proof.length; i += 2) {
            // Ottieni il ruolo oggetto della credenziale attuale
            currAssignedRole = exprPool[_proof[i]];

            if(uint96(uint256(_proof[i+1])) == 0) {
                currMember = address(uint160(bytes20(_proof[i+1])));

                // La credenziale attuale è una simple member nella forma currAssignedRole <- currMember
                // Verifica l'esistenza su storage
                uint memberPointer = members[_proof[i]].getPointer(currMember);
                if(memberPointer == 0)
                    return Solution(NULL_PRINCIPAL, NULL_ROLENAME, NULL_PRINCIPAL, 1);

                // Accetta la simple member come soluzione inserendola nella coda di elaborazione
                if(i != 0) j++;
                solStack[j].principal = currAssignedRole.addrA;
                solStack[j].rolename = currAssignedRole.roleA;
                solStack[j].solution = currMember;
                solStack[j].weight = members[_proof[i]].getWeight(memberPointer - 1);
            }
            else {
                currRoleExpr = exprPool[_proof[i+1]];

                // La credenziale attuale è una inclusione nella forma currAssignedRole <- currRoleExpr
                // Verifica l'esistenza su storage
                uint inclusionPointer = currAssignedRole.inclusions.getPointer(_proof[i+1]);
                if(inclusionPointer == 0)
                    return Solution(NULL_PRINCIPAL, NULL_ROLENAME, NULL_PRINCIPAL, 2);

                if(currRoleExpr.exprType == EXPR_SI) {
                    // L'inclusione è di tipo semplice

                    // Accetta la simple inclusion solo se soddisfacibile dalle soluzioni nella stack di elaborazione
                    // credenziale: A.a <-w B.b
                    // solStack:
                    //              |               |   --->    |                   |
                    //       (j) -> | (m,w1) ∈ B.b  |   --->    | (m,w*w1) ∈ A.a    |
                    //              | ...           |   --->    | ...               |
                    //              -----------------   --->    ---------------------
                    //
                    if(currRoleExpr.addrA != solStack[j].principal || currRoleExpr.roleA != solStack[j].rolename)
                        return Solution(NULL_PRINCIPAL, NULL_ROLENAME, NULL_PRINCIPAL, 3);

                    // Aggiorna la stack di elaborazione
                    solStack[j].principal = currAssignedRole.addrA;
                    solStack[j].rolename = currAssignedRole.roleA;
                    solStack[j].weight = mulWeight(solStack[j].weight, currAssignedRole.inclusions.getWeight(inclusionPointer - 1));
                }
                else if(currRoleExpr.exprType == EXPR_LI) {
                    // L'inclusione è di tipo linkato

                    // Accetta la linked inclusion solo se soddisfacibile dalle soluzioni nella stack di elaborazione
                    // credenziale: A.a <-w B.b.c
                    // solStack:
                    //              |               |   --->    |                   |
                    //       (j) -> | (C,w2) ∈ B.b  |   --->    | [...]             |
                    //              | (m,w1) ∈ C.c  |   --->    | (m,w*w1*w2) ∈ A.a | <- (j)
                    //              | ...           |   --->    | ...               |
                    //              -----------------   --->    ---------------------
                    //
                    if(currRoleExpr.addrA != solStack[j].principal
                            || currRoleExpr.roleA != solStack[j].rolename
                            || currRoleExpr.roleB != solStack[j-1].rolename
                            || solStack[j].solution != solStack[j-1].principal)
                        return Solution(NULL_PRINCIPAL, NULL_ROLENAME, NULL_PRINCIPAL, 4);

                    // Aggiorna la stack di elaborazione
                    j--;
                    solStack[j].principal = currAssignedRole.addrA;
                    solStack[j].rolename = currAssignedRole.roleA;
                    solStack[j].weight = mulWeight(mulWeight(solStack[j].weight, solStack[j+1].weight), currAssignedRole.inclusions.getWeight(inclusionPointer - 1));
                }
                else if(currRoleExpr.exprType == EXPR_II) {
                    // L'inclusione è di tipo intersecato

                    // Accetta la intersection inclusion solo se soddisfacibile dalle soluzioni nella stack di elaborazione
                    // credenziale: A.a <-w B.b ∩ C.c
                    // solStack:
                    //              |               |       |               |    --->    |                           |
                    //       (j) -> | (m,w2) ∈ B.b  |       | (m,w2) ∈ C.c  |    --->    |                           |
                    //              | (m,w1) ∈ C.c  |  OR   | (m,w1) ∈ B.b  |    --->    | (m,w*min{w1*w2}) ∈ A.a    | <- (j)
                    //              | ...           |       | ...           |    --->    | ...                       |
                    //              -----------------       -----------------    --->    -----------------------------
                    //
                    if(solStack[j].solution != solStack[j-1].solution ||
                                (
                                    (
                                        currRoleExpr.addrA != solStack[j].principal ||
                                        currRoleExpr.roleA != solStack[j].rolename ||
                                        currRoleExpr.addrB != solStack[j-1].principal ||
                                        currRoleExpr.roleB != solStack[j-1].rolename
                                    )
                                    &&
                                    (
                                        currRoleExpr.addrA != solStack[j-1].principal ||
                                        currRoleExpr.roleA != solStack[j-1].rolename ||
                                        currRoleExpr.addrB != solStack[j].principal ||
                                        currRoleExpr.roleB != solStack[j].rolename
                                    )
                                )
                            )
                        return Solution(NULL_PRINCIPAL, NULL_ROLENAME, NULL_PRINCIPAL, 5);

                    // Aggiorna la stack di elaborazione
                    j--;
                    solStack[j].principal = currAssignedRole.addrA;
                    solStack[j].rolename = currAssignedRole.roleA;
                    if(solStack[j].weight <= solStack[j+1].weight)
                        solStack[j].weight = mulWeight(solStack[j].weight, currAssignedRole.inclusions.getWeight(inclusionPointer - 1));
                    else
                        solStack[j].weight = mulWeight(solStack[j+1].weight, currAssignedRole.inclusions.getWeight(inclusionPointer - 1));
                }
            }
        }

        return solStack[j];
    }


    // ----------------------------------------------------- //

    function exprExists(bytes32 _exprId) external view returns(bool) {
        return exprPool[_exprId].exprType != EXPR_NC;
    }

    function getMembersCount(bytes32 _roleId) external view returns(uint) {
        return members[_roleId].size();
    }

    function getMember(bytes32 _roleId, uint index) external view returns(address, uint8) {
        return members[_roleId].get(index);
    }

    function getInclusionsCount(bytes32 _roleId) external view returns(uint) {
        return exprPool[_roleId].inclusions.size();
    }

    function getInclusion(bytes32 _roleId, uint index) external view returns(address, address, bytes2, bytes2, uint8) {
        bytes32 exprId;
        uint8 weight;
        Expression storage expr;

        (exprId, weight) = exprPool[_roleId].inclusions.get(index);
        expr = exprPool[exprId];

        return (expr.addrA, expr.addrB, expr.roleA, expr.roleB, weight);
    }
 
}