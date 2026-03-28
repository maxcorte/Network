#!/bin/bash
# =====================================================
# TEST BLACKBOX DES PERFORMANCES GLOBALES
# =====================================================

GREEN='\033[0;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fichiers de test et d'export
ORIGINAL="tests/www/test_blackbox.bin"
DOWNLOADED="reçu_blackbox.bin"
CSV_FILE="tests/resultats_performances.csv"

# Fonction appelée en cas de Ctrl+C (anti-zombies)
cleanup_on_interrupt() {
    echo -e "\n${RED}Arrêt forcé ! Nettoyage des processus...${NC}"
    kill $SERVER_PID $SIM_PID 2>/dev/null
    wait $SERVER_PID $SIM_PID 2>/dev/null
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
    python3 src/server.py localhost 8080 --root ./tests/www > /dev/null 2>&1 &
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
    kill $SERVER_PID $SIM_PID 2>/dev/null
    wait $SERVER_PID $SIM_PID 2>/dev/null
    rm -f "$DOWNLOADED" time_out.txt client_err.log
    sleep 1
    echo ""
}


echo -e "${YELLOW}🧪 Tests blackbox Latence${NC}"

# Valeurs de tests
LATENCE=(10 50 100 200 300 350 400 450 500 600 700 800 900 1000 1100 1200 1300 1400 1500 1600 1700 1800 1900 2000)

for d in "${LATENCE[@]}"; do
    run_test "Latence ${d} ms" "-d $d -R"
done



echo -e "${GREEN}🧪 Tests blackbox réseau parfait${NC}"
run_test "Réseau Parfait" "-l 0"



echo -e "${YELLOW}🧪 Tests blackbox pertes${NC}"
# Valeurs de tests
PERTES=(10 20 30 40 50 60 70 80 85 90)

for l in "${PERTES[@]}"; do
    run_test "Pertes extrêmes ${l} %" "-l $l -R"
done



echo -e "${YELLOW}🧪 Tests blackbox Latence et jitter${NC}"

#Valeurs de tests:

latence_jitter=("10 5" "20 10" "30 15" "40 30" "50 25" "60 50" "70 40" "80 70" "90 45" "100 90" "110 55")

for dj in "${latence_jitter[@]}"; do
    read -r d j <<< "$dj"
    run_test "Latence et Jitter (Délai ${d}, Jitter ${j})" "-d $d -j $j -R"
done


rm -f $ORIGINAL
echo "Tests terminés !"