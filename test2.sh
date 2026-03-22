#!/bin/bash
# =====================================================
# TEST BLACKBOX SRTP - VERSION ULTRA-SIMPLE macOS
# Un test à la fois, sans timeout magique, export CSV
# =====================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fichiers de test et d'export
ORIGINAL="www/test_blackbox.bin"
DOWNLOADED="reçu_blackbox.bin"
CSV_FILE="resultats_performances.csv"

# Fonction appelée en cas de Ctrl+C (anti-zombies)
cleanup_on_interrupt() {
    echo -e "\n${RED}Arrêt forcé ! Nettoyage des processus...${NC}"
    kill -9 $SERVER_PID $SIM_PID 2>/dev/null
    rm -f time_out.txt client_err.log
    exit 1
}
trap cleanup_on_interrupt SIGINT

# Initialisation du fichier CSV
echo "Nom du test,Statut,Temps Real (s),Temps User (s),Temps Sys (s)" > "$CSV_FILE"

# Génération d'un fichier de 50 Ko pour les tests
mkdir -p www
head -c 50000 /dev/urandom > "$ORIGINAL"

# Fonction de test générique
run_test() {
    TEST_NAME=$1
    SIM_ARGS=$2
    echo -e "========== Test: ${TEST_NAME} =========="
    
    # Serveur
    python3 src/server.py localhost 8080 --root ./www > /dev/null 2>&1 &
    SERVER_PID=$!
    
    # Link simulator
    ../../Linksimulator/Linksimulator-master/link_sim -p 8888 -P 8080 $SIM_ARGS > /dev/null 2>&1 &
    SIM_PID=$!
    
    sleep 1 
    
    # On définit le format de sortie de la commande 'time' (Real, User, Sys séparés par des virgules)
    export TIMEFORMAT="%R,%U,%S"
    
    # Client : On redirige les erreurs du client (2> client_err.log) pour que SEUL le temps aille dans time_out.txt
    { time python3 src/client.py "http://localhost:8888/test_blackbox.bin" -s "$DOWNLOADED" 2> client_err.log ; } 2> time_out.txt
    
    # Récupération des temps générés par TIMEFORMAT
    TIMES=$(cat time_out.txt)
    
    # Vérification Black-Box
    STATUS="ÉCHEC"
    if cmp -s "$ORIGINAL" "$DOWNLOADED" 2>/dev/null; then
        echo -e "${GREEN}[SUCCÈS] Le fichier reçu est parfaitement identique !${NC}"
        STATUS="SUCCÈS"
    else
        echo -e "${RED}[ÉCHEC] Le fichier reçu est corrompu ou incomplet.${NC}"
    fi
    
    # Écriture dans le fichier CSV
    echo "\"$TEST_NAME\",\"$STATUS\",$TIMES" >> "$CSV_FILE"
    
    # Nettoyage de fin de test
    kill -9 $SERVER_PID $SIM_PID 2>/dev/null
    rm -f "$DOWNLOADED" time_out.txt client_err.log
    sleep 1
    echo ""
}


echo -e "${YELLOW}🧪 Tests blackbox Latence${NC}"

run_test "Latence 10 ms" "-d 10 -R"
run_test "Latence 20 ms" "-d 20 -R"
run_test "Latence 30 ms" "-d 30 -R"
run_test "Latence 40 ms" "-d 40 -R"
run_test "Latence 50 ms" "-d 50 -R"
run_test "Latence 60 ms" "-d 60 -R"
run_test "Latence 70 ms" "-d 70 -R"
run_test "Latence 80 ms" "-d 80 -R"
run_test "Latence 90 ms" "-d 90 -R"
run_test "Latence 100 ms" "-d 100 -R"


echo -e "${GREEN}🧪 Tests blackbox réseau parfait${NC}"
run_test "Réseau Parfait" "-l 0"

echo -e "${YELLOW}🧪 Tests blackbox pertes${NC}"
run_test "Pertes extrêmes (10% Data + ACKs)" "-l 10 -R"
run_test "Pertes extrêmes (20% Data + ACKs)" "-l 20 -R"
run_test "Pertes extrêmes (40% Data + ACKs)" "-l 40 -R"
run_test "Pertes extrêmes (60% Data + ACKs)" "-l 60 -R"
run_test "Pertes extrêmes (70% Data + ACKs)" "-l 70 -R"


echo -e "${YELLOW}🧪 Tests blackbox Latence et jitter${NC}"
run_test "Latence et Jitter (Délai 10ms, Jitter 5ms)" "-d 10 -j 5 -R"
run_test "Latence et Jitter (Délai 20ms, Jitter 10ms)" "-d 20 -j 10 -R"
run_test "Latence et Jitter (Délai 40ms, Jitter 30ms)" "-d 40 -j 30 -R"
run_test "Latence et Jitter (Délai 60ms, Jitter 50ms)" "-d 60 -j 50 -R"
run_test "Latence et Jitter (Délai 80ms, Jitter 70ms)" "-d 80 -j 70 -R"
run_test "Latence et Jitter (Délai 100ms, Jitter 90ms)" "-d 100 -j 90 -R"


rm -f $ORIGINAL
echo "Tests terminés !"