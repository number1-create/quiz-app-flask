# app.py (Versione Finale - Integrata con nuovo Frontend)

import os
import glob 
import re
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chiave_vittoria_modificata')

import logging
logger = logging.getLogger(__name__)

# ### MODIFICA 2: Il filtro 'superscript' è stato rimosso. ###
# La formattazione avanzata è ora gestita da MathJax nel frontend.


# --- CONFIGURAZIONE DEGLI ESAMI ---
EXAMS = {
    'fe-mechanical': {
        'display_name': 'FE Mechanical Exam',            
        'filenames': ['quiz_ROBUSTO_FINALE_v6.txt'],     #nome file 
        'num_questions': 2                           #numero domande per ogni test
    },
    'ged': {
        'display_name': 'GED Practice Test',
        'filenames': ['ged_test_output.txt'],            #nome file 
        'num_questions': 2                            #numero domande per ogni test
    },
    'asvab' : {
        'display_name': 'ASVAB Exam Prep',            
        'filenames': ['PRACTICE TEST - ASVAB EXAM PREP.txt'],
        'num_questions': 2                          #numero domande per ogni test
    },
}

# Nuova costante: il quiz “unico” o di default
DEFAULT_EXAM_KEY = 'fe-mechanical'

# --- BANCA DATI GLOBALE IN MEMORIA (ORGANIZZATA PER ESAME) ---
ALL_QUESTIONS_BANK = {} # Sarà popolata come {'exam_key': {question_id: question_data}}

# Sostituisci questo...
# --- BANCA DATI GLOBALE IN MEMORIA ---
# ALL_QUESTIONS_BANK = {}

# ...con questo
# --- BANCA DATI GLOBALE IN MEMORIA (ORGANIZZATA PER ESAME) ---
ALL_QUESTIONS_BANK = {} # Sarà popolata come {'exam_key': {question_id: question_data}}

# ==============================================================================
# === LA FUNZIONE DI PARSING DEL FILE TXT (INVARIATA)                        ===
# ==============================================================================
# <-- Lasciamo questo import qui perché è usato da parse_quiz_file

import logging
SECTION_HEADER_RE = re.compile(r'^PRACTICE TEST - .+? - (?P<area>.+)$', re.MULTILINE)
QUESTION_LINE_RE = re.compile(r'^\s*(?P<num>\d+)\.\s*(?P<text>.*)$')
OPTION_RE = re.compile(r'^\s*(?P<letter>[A-Da-d])\)\s*(?P<opt>.*)$')
ANSWER_HEADER = '--- CORRECT ANSWERS AND EXPLANATIONS ---'
ANSWER_LINE_RE = re.compile(r'^\s*(?P<num>\d+)\.\s*Correct Answer:\s*(?P<ans>[A-Da-d])', re.IGNORECASE)
EXPLANATION_RE = re.compile(r'^\s*Explanation:\s*(?P<exp>.*)$', re.IGNORECASE)

def parse_quiz_file_v2(file_content, filename="<unknown>"):
    logger = logging.getLogger(__name__)
    questions = []
    parts = SECTION_HEADER_RE.split(file_content)
    it = iter(parts)
    next(it, None)  # skip preamble
    sections = []
    for area in it:
        content = next(it, '')
        sections.append((area.strip(), content))

    for area, content in sections:
        if ANSWER_HEADER not in content:
            logger.warning(f"Missing answer section in area '{area}' of {filename}")
            continue
        qpart, apart = content.split(ANSWER_HEADER, 1)

        # parse questions
        q_blocks, current, last_opt = [], None, None
        for line in qpart.splitlines():
            m = QUESTION_LINE_RE.match(line)
            if m:
                if current: q_blocks.append(current)
                current = {'num': int(m.group('num')),
                           'text_lines': [m.group('text').strip()],
                           'options': {}}
                last_opt = None
                continue
            if not line.strip() or current is None:
                continue
            mopt = OPTION_RE.match(line)
            if mopt:
                letter = mopt.group('letter').upper()
                current['options'][letter] = [mopt.group('opt').strip()]
                last_opt = letter
            else:
                if last_opt and last_opt in current['options']:
                    current['options'][last_opt].append(line.strip())
                else:
                    current['text_lines'].append(line.strip())
        if current: q_blocks.append(current)

        # parse answers
        a_map, exp_map, lines, idx = {}, {}, apart.splitlines(), 0
        while idx < len(lines):
            m = ANSWER_LINE_RE.match(lines[idx])
            if m:
                num = int(m.group('num')); ans = m.group('ans').upper(); idx += 1
                exp_lines = []
                while idx < len(lines):
                    me = EXPLANATION_RE.match(lines[idx])
                    if me:
                        exp_lines.append(me.group('exp').strip()); idx += 1
                        while idx < len(lines) and lines[idx].strip():
                            exp_lines.append(lines[idx].strip()); idx += 1
                        break
                    idx += 1
                a_map[num] = ans
                exp_map[num] = ' '.join(exp_lines)
            else:
                idx += 1

        # combine question + answer
        for qb in q_blocks:
            n = qb['num']
            if n not in a_map or not exp_map.get(n):
                logger.warning(f"Q{n} in '{area}' missing answer/expl in {filename}")
                continue
            questions.append({
                'id': n,
                'area': area,
                'area': area,
                'topic': area,
                'text': ' '.join(qb['text_lines']),
                'options': {l: ' '.join(txt) for l, txt in qb['options'].items()},
                'correct_answer': a_map[n],
                'explanation': exp_map[n]
            })
    return questions

# ==============================================================================
# === LE FUNZIONI DI CARICAMENTO E LE ROTTE DELL'APP                         ===
# ==============================================================================

def load_all_questions_into_bank():
    print("--- Inizio caricamento di tutte le domande dai file TXT ---")
    # Ciclo esterno: uno per ogni esame ('fe-mechanical', 'ged', ecc.)
    # Livello 1 di indentazione (4 spazi)
    for exam_key, config in EXAMS.items():
        # Crea lo "scaffale" vuoto per questo specifico esame
        ALL_QUESTIONS_BANK[exam_key] = {}
        print(f"  -> Preparazione per l'esame: '{config['display_name']}'")

        # Livello 2 di indentazione (8 spazi)
        # Ciclo interno: uno per ogni file associato a QUESTO esame
        # (indentato correttamente dentro al primo ciclo)
        # NUOVA VERSIONE CON DEBUG
# (dentro load_all_questions_into_bank)
        for filename in config['filenames']:
            print(f"--- [DEBUG RENDER] Analizzo l'esame '{exam_key}', file '{filename}' ---")

            # Tentativo 1: nella cartella 'quizzes'
            path_in_quizzes = os.path.join(os.path.dirname(__file__), 'quizzes', filename)
            print(f"[DEBUG RENDER] Tento di trovare il file qui: {path_in_quizzes}")
            if os.path.exists(path_in_quizzes):
                print(f"[DEBUG RENDER] SUCCESSO: File trovato in 'quizzes'.")
                filepath = path_in_quizzes
            else:
                # Tentativo 2: nella cartella principale (root)
                print(f"[DEBUG RENDER] FALLITO: File non trovato. Provo nella cartella principale.")
                path_in_root = os.path.join(os.path.dirname(__file__), filename)
                print(f"[DEBUG RENDER] Tento di trovare il file qui: {path_in_root}")
                if os.path.exists(path_in_root):
                    print(f"[DEBUG RENDER] SUCCESSO: File trovato nella root.")
                    filepath = path_in_root
                else:
                    print(f"[DEBUG RENDER] FALLITO: File non trovato neanche nella root. Salto questo file.")
                    print(f"  -> ATTENZIONE: File non trovato '{filename}' per l'esame '{exam_key}'")
                    continue

            print(f"[DEBUG RENDER] Procedo con l'apertura e la lettura del file: {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            questions_from_file = parse_quiz_file_v2(content, filename)
            
            # Livello 3 di indentazione (12 spazi)
            # Aggiunge le domande allo SCAFFALE GIUSTO (exam_key)
            for q in questions_from_file:
                 # Livello 4 di indentazione (16 spazi)
                 # Creiamo un ID univoco combinando l'area e il numero originale.
                 # Esempio: "TERMODINAMICA-15"
                unique_id = f"{q['area'].upper()}-{q['id']}"

                # Controlliamo la presenza dell'ID univoco

                if unique_id not in ALL_QUESTIONS_BANK[exam_key]:
                # Salviamo l'ID univoco DENTRO l'oggetto domanda. È fondamentale!
                # Livello 5 di indentazione (20 spazi)
                    q['id'] = unique_id 
                    ALL_QUESTIONS_BANK[exam_key][unique_id] = q
                else:
                 # Livello 5 di indentazione (20 spazi)
                 # L'avviso ora usa l'ID originale per chiarezza
                     print(f"  -> ATTENZIONE: Combinazione area/ID duplicata '{q['area']}/{q['id']}' nel file '{filename}' per l'esame '{exam_key}'. La domanda verrà ignorata.")
        
            # Stampa il messaggio NUOVO E CORRETTO, specifico per questo esame
            print(f"  -> Caricato '{filename}'. Banca dati per '{exam_key}' ora ha: {len(ALL_QUESTIONS_BANK[exam_key])} domande.")
            
    print("--- Caricamento completato. ---")

@app.route('/start/<exam_key>')
def start_quiz(exam_key):
    # 1. Validazione dell'esame richiesto
    if exam_key not in EXAMS:
        abort(404, description="The requested exam does not exist.")

    # 2. Pulizia sessione e impostazione del contesto dell'esame
    session.clear()
    session['exam_key'] = exam_key

    # 3. Selezione delle domande specifiche per l'esame
    config = EXAMS[exam_key]
    question_bank_for_exam = ALL_QUESTIONS_BANK.get(exam_key, {})
    all_available_ids = list(question_bank_for_exam.keys())

    if not all_available_ids:
        # Se non ci sono domande, non si può procedere.
        # È un errore di configurazione, non dell'utente.
        return "<h1>Critical Error<p>No questions found for this exam. Please contact the administrator.</p>", 500

    num_to_select = min(config['num_questions'], len(all_available_ids))
    
    if num_to_select <= 0:
        return "<h1>Configuration Error</h1><p>The number of questions to select is zero.</p>", 500

    selected_ids = random.sample(all_available_ids, num_to_select)
    session['question_ids'] = selected_ids
    
    # 4. Reindirizza l'utente alla pagina del quiz
    return redirect(url_for('quiz'))

@app.route('/')
def index():
    # Non mostra una lista, ma dà un'istruzione.
        return "<h1>Quiz Platform</h1><p>To start an exam, please use the link you were provided.</p>"

@app.route('/quiz')
def quiz():
    if 'question_ids' not in session:
        flash("Invalid or expired session. Please start a new exam.", "error")
        # Reindirizza alla pagina di cortesia
        return redirect(url_for('index')) 
        
    # 1. Recupera lo "scaffale" (l'esame) dalla sessione
    exam_key = session.get('exam_key') 
    
    # Controllo di sicurezza: se per qualche motivo exam_key non c'è, non possiamo continuare.
    if not exam_key or exam_key not in ALL_QUESTIONS_BANK:
        flash("Sessione non valida. Scegli un esame.", "error")
        return redirect(url_for('index'))

    question_ids = session['question_ids']
    
    # 2. QUI LA MODIFICA CHIAVE:
    # Per ogni ID, cerca prima nello "scaffale" giusto (exam_key) e poi prendi la domanda (qid)
    questions_for_quiz = [
        ALL_QUESTIONS_BANK[exam_key][qid] for qid in question_ids
        if qid in ALL_QUESTIONS_BANK[exam_key]
    ]
    exam_title = EXAMS.get(exam_key, {}).get('display_name', 'Quiz')
    return render_template('quiz.html', questions=questions_for_quiz, exam_title=exam_title)

@app.route('/submit', methods=['POST'])
def submit():
    if 'question_ids' not in session:
        # Reindirizza se la sessione è scaduta prima dell'invio
        return redirect(url_for('index'))

    # 1. Recupera lo "scaffale" (l'esame) dalla sessione
    exam_key = session.get('exam_key')
    if not exam_key or exam_key not in ALL_QUESTIONS_BANK:
        return redirect(url_for('index'))

    question_ids = session.get('question_ids', [])
    
    # 2. QUI LA MODIFICA CHIAVE (IDENTICA A /quiz):
    # Cerca prima nello "scaffale" giusto (exam_key) e poi prendi la domanda (qid)
    questions_in_quiz = [
        ALL_QUESTIONS_BANK[exam_key][qid] for qid in question_ids
        if qid in ALL_QUESTIONS_BANK.get(exam_key, {})
    ]

    user_answers = request.form
    results = []
    score = 0
    questions_with_answers = 0
    
    ### MODIFICA 3: Logica per 'advice' ###
    # Inizializziamo una lista per gli argomenti sbagliati
    incorrect_topics = set() 

    for q in questions_in_quiz:
        user_answer = user_answers.get(f'q{q["id"]}')
        is_correct = None
        if q.get('correct_answer'):
            questions_with_answers += 1
            is_correct = (user_answer == q['correct_answer'])
            if is_correct:
                score += 1
            else:
                # Se la risposta è sbagliata, aggiungiamo l'argomento alla lista
                incorrect_topics.add(q['topic'])
        
        results.append({
            'question': q,
            'user_answer': user_answer,
            'is_correct': is_correct
        })

        # Create the advice message
    if not incorrect_topics:
        advice = "Congratulations, you answered all questions correctly! Great job."
    else:
        advice = f"To improve, we recommend you review the following topics: {', '.join(sorted(list(incorrect_topics)))}."

    session.clear()

    ### MODIFICA 4: Passaggio di 'advice' e 'EXAMS' al template ###

    exam_title = EXAMS.get(exam_key, {}).get('display_name', 'Quiz')

    return render_template (
        'results.html',
        score=score,
        total=questions_with_answers,
        results=results,
        advice=advice,          # <-- La nuova variabile per i consigli
        exam_title=exam_title,
        exam_key=exam_key  # <-- Il dizionario globale per i nomi degli esami
        )


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, '
        'post-check=0, pre-check=0, max-age=0'
    )
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ==============================================================================

if __name__ == '__main__':
    load_all_questions_into_bank()
    app.run(debug=True, port=5002)
