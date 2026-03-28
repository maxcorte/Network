#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
ORIGINAL="./www/test_blackbox.bin"
DOWNLOADED="reçu_blackbox.bin"

head -c 50000 /dev/urandom > $ORIGINAL

run_test() {
    TEST_NAME=$1
    SIM_ARGS=$2
    echo -e "========== Test: ${TEST_NAME} =========="
    #serveur
    python3 src/server.py localhost 8080 --root ./tests/www > /dev/null 2>&1 &
    SERVER_PID=$!
    
    #link simulator
    ../../Linksimulator/Linksimulator-master/link_sim -p 8888 -P 8080 $SIM_ARGS > /dev/null 2>&1 &
    SIM_PID=$!
    
    sleep 1 
    
    #client
    python3 src/client.py "http://localhost:8080/test_blackbox.bin" -s $DOWNLOADED
    
    if cmp -s "$ORIGINAL" "$DOWNLOADED"; then
        echo -e "${GREEN}[SUCCÈS] Le fichier reçu est parfaitement identique !${NC}"
    else
        echo -e "${RED}[ÉCHEC] Le fichier reçu est corrompu ou incomplet.${NC}"
    fi
    
    kill -9 $SERVER_PID $SIM_PID 2>/dev/null
    rm -f $DOWNLOADED
    sleep 1
    echo ""
}

run_test "Réseau Parfait" "-l 0"
run_test "Pertes extrêmes (60% Data + ACKs)" "-l 60 -R"
run_test "Latence et Jitter (Délai 100ms, Jitter 100ms)" "-d 100 -j 100 -R"
run_test "Corruption de paquets (50%)" "-e 50 -R"
run_test "Troncation de paquets (10%)" "-c 10 -R"
run_test "Tout en même temps" "-l 20 -d 30 -j 20 -e 5 -c 5 -R"
rm -f $ORIGINAL
echo "Tests terminés !"