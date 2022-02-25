#%%
from fileinput import filename
import numpy as np
from pathlib import Path
import re
import textract
import itertools
import random
from collections import Counter

MAX_ITER = 200


class MaxIterError(Exception):
    pass


#%%


class Constraint:
    def counter_from_clones_list(clones_list):
        """Fonction qui prend en argument une liste de clones
        et qui renvoie deux compteurs c_T, c_F où c_T (resp. c_F) compte
        les occurences des réponses vraies (resp. fausses)"""
        true_answer_with_repetition = []
        false_answer_with_repetition = []
        for clone in clones_list:
            true_answer_with_repetition.extend(clone.true_answers)
            false_answer_with_repetition.extend(clone.false_answers)
        return Counter(true_answer_with_repetition), Counter(
            false_answer_with_repetition
        )

    def __init__(self, minapp_T=0, maxapp_T=100, minapp_F=0, maxapp_F=100):
        """création de l'object contrainte avec lest attribu de
        max et min appartition des réponse vraies et fausses"""
        self.minapp_T = minapp_T
        self.maxapp_T = maxapp_T
        self.minapp_F = minapp_F
        self.maxapp_F = maxapp_F

    def do_satisfy(self, question_native, clones_list):
        """
        Retourne True si la contrainte sur la liste des clones clones_list générés depuis question_native est vérifiée,
        False sinon.
        """
        c_T, c_F = Constraint.counter_from_clones_list(clones_list)
        for true_ans in question_native.true_answers:
            if c_T[true_ans] < self.minapp_T or c_T[true_ans] > self.maxapp_T:
                return False
        for false_ans in question_native.false_answers:
            if c_F[false_ans] < self.minapp_F or c_T[false_ans] > self.maxapp_F:
                return False
        return True


class Question:
    """
    Class Question :
    Une question possède :
    - self.code : Un code UE
    - self.question : Une question (str avec '?' à la fin)
    - self.true_answers : Une liste de réponse vraies (list of str)
    - self.false_answers : Une liste de réponse fausses (list of str)
    - self.nb_clones : on choisit de générer self.nb_clones à partir de la question
    """

    def __init__(self, code, question, nb_clones=6):
        self.code = code
        self.question = question
        self.true_answers = []
        self.false_answers = []
        self.nb_clones = nb_clones

    def rewards(self):
        """
        retourne les rewards (r1, r2) selon
        r1 = 100/nb_questions_justes
        r2 = -100/nb_questions_fausses
        """
        r1 = 0 if not self.true_answers else 100 / len(self.true_answers)
        r2 = 0 if not self.false_answers else -100 / len(self.false_answers)
        r1 = (
            int(r1) if np.abs(r1 - int(r1)) < 0.1 else r1
        )  # on arrondi à l'entier pour moodle notamment dans le cas 100%
        r2 = int(r2) if np.abs(r2 - int(r2)) < 0.1 else r2
        return (r1, r2)

    def get_clones(self):
        """
        Retourne la liste de tous les clones à partir de l'objet question.
        Il y en a précisément
        (nb_clones parmis nb_total_de questions).
        """
        cloned_questions = []
        n_true = len(self.true_answers)
        n_false = len(self.false_answers)
        T_A = set(zip(self.true_answers, n_true * [True]))
        F_A = set(zip(self.false_answers, n_false * [False]))
        sets_of_cloned_answers = list(
            map(set, itertools.combinations(T_A.union(F_A), 4))
        )
        for idx, cloned_answers in enumerate(sets_of_cloned_answers):
            prefix = self.code[:-2]
            suffix = f"0{idx + 1}" if idx + 1 < 10 else f"{idx + 1}"
            clone = Question(prefix + suffix, question=self.question)
            for answer, b in cloned_answers:
                if b:
                    clone.true_answers.append(answer)
                else:
                    clone.false_answers.append(answer)
            cloned_questions.append(clone)
        return cloned_questions

    def get_random_clones(self, constraint):
        """
        constraint : object contrainte
        retourne un ensemble aléatoire de clones qui satisfont la contrainte.
        """
        cloned_questions = self.get_clones()
        if len(cloned_questions) <= self.nb_clones:
            print(
                f"warning : question {self.code} has only {len(cloned_questions)} possible clones"
            )
            return cloned_questions
        else:
            for _ in range(MAX_ITER):
                random_clones = random.sample(cloned_questions, self.nb_clones)
                if constraint.do_satisfy(self, random_clones):
                    return random_clones
            raise MaxIterError

    def __repr__(self):
        return self.code


#%%
class Decoder:
    """Class qui pour décoder un fichier word .docx
    en une liste d'object Question (voir class Question)
    self.text contient le text extrait du docx
    """

    def __init__(self, path_file_docx):
        # On extrait les données avec le module textract dans la variable text_brut
        text_brut = (
            str(textract.process(str(path_file_docx)), "utf-8")
            .replace("\t", "")
            .split("\n\n")
        )
        # On nettoie ensuite un peu et on la met dans dans text_propre
        text_propre = []
        for line in text_brut:
            text_propre = text_propre + line.split("\n")
        self.text = text_propre

    def evaluate(self, answer):
        """
        answer : str
        on évalue answer en fonction du préfixe :
        par convention, si elle commence par
        '+', '$' 'OUI' ou 'OUI -'
        """
        if answer.strip()[0] in {"+", "$"}:
            return answer.strip()[1:].strip(), True
        elif answer.strip()[0:5] == "OUI -":
            return answer.strip()[5:].strip(), True
        elif answer.strip()[0:3] == "OUI":
            return answer.strip()[3:].strip(), True
        else:
            return answer.strip(), False

    def get_questions(self):
        """
        Retournes une liste de Question:
        la liste des objets Question est la liste des questions natives.
        """
        question_list = []
        # reg_exp : on cherche les endroits où il y a un code UE de la forme PX où X est un nombre
        reg_exp = re.compile("P\d\.")
        for index, line in enumerate(self.text):
            # Si on tombe sur un code UE, alors on rentre dans une sous boucle pour créer l'objet questino qui correspond.On accepte aussi si la ligne commence par *
            if line and (line[0] == "*" or reg_exp.match(line.strip())):
                name = line[1:].strip() if line[0].strip() == "*" else line.strip()

                # prefixe contient le code UE (hors *) avec un . à la fin. Il n'est pas ajouté si le '.' est déjà présent.
                prefix = name if name[-1] == "." else name + "."
                question = Question(
                    code=prefix + "00",
                    question=self.text[index + 1].strip(),
                )
                index_answer = index + 2
                while index_answer < len(self.text) and not (
                    self.text[index_answer].strip() == ""
                ):
                    answer, is_true = self.evaluate(self.text[index_answer])
                    if is_true:
                        question.true_answers.append(answer.strip())
                    else:
                        question.false_answers.append(answer.strip())
                    index_answer += 1
                question_list.append(question)
        return question_list


class Encoder:
    """
    Class pour encoder une liste de quesitons en text formatté.
    Ici on formatte en moodle mais on peut encoder différemment.
    en une liste d'object Question (voir class Question)
    self.text contient le text extrait du docx
    """

    def __init__(self):
        pass

    def encode_question(self, question):
        code_name = question.code
        r1, r2 = question.rewards()
        s = (
            f"// question name: {question.question}\n"
            f"//[id:{code_name}]\n"
            f"::{question.question}::\n"
            f"[html]{code_name} <strong>{question.question}</strong>"
            "{\n"
        )

        for answer in question.true_answers:
            s = s + f"~%{r1}%{answer}\n"
        for answer in question.false_answers:
            s = s + f"~%{r2}%{answer}\n"
        if question.true_answers:
            s = s + "~%-100%Aucune de ces propositions n'est juste\n"
        else:
            s = s + "~%100%Aucune de ces propositions n'est juste\n"
        return s + "}\n\n"

    def write_question_list(
        self, question_list, path_dir_output, filename_output="native.txt"
    ):
        with open(
            path_dir_output.joinpath(filename_output), "w", encoding="utf-8"
        ) as file:
            for question in question_list:
                file.write(self.encode_question(question))

    def write_all_clones(self, question_list, path_dir_output):
        for question in question_list:
            cloned_questions = question.get_clones()
            self.write_question_list(
                cloned_questions, path_dir_output, question.code + ".txt"
            )

    def write_random_clones(
        self,
        question_list,
        path_dir_output,
        filename_output=None,
        constraint=Constraint(),
    ):
        if filename_output is None:
            filename_output = str(path_dir_output) + ".txt"
        clones_list = []
        for question in question_list:
            clones_list.extend(question.get_random_clones(constraint))
        self.write_question_list(clones_list, path_dir_output, filename_output)


#%%
if __name__ == "__main__":
    list_dir = list(
        map(
            Path,
            [
                "./native",
                "./tous_clones",
                "./clones_sans_contrainte",
                "./clones_contrainte_min_11",
                "./clones_contrainte_min_22",
                "./clones_customisé_ex_min_22_max_33",
            ],
        )
    )
    for dir in list_dir:
        if not dir.is_dir():
            dir.mkdir()
    current_dir = Path(".")
    path_file_docx = next(current_dir.glob("*.docx"))

    decoder = Decoder(path_file_docx)
    encoder = Encoder()
    question_list = decoder.get_questions()

    constraint_random = Constraint()
    constraint_1 = Constraint(minapp_T=1, minapp_F=1)
    encoder.write_question_list(question_list, list_dir[0])
    encoder.write_all_clones(question_list, list_dir[1])
    encoder.write_random_clones(
        question_list, list_dir[2], constraint=constraint_random
    )
    encoder.write_random_clones(question_list, list_dir[3], constraint=constraint_1)
    try:
        constraint_2 = Constraint(minapp_T=2, minapp_F=2)
        constraint_custom = Constraint(minapp_T=2, maxapp_T=3, minapp_F=2, maxapp_F=3)
        encoder.write_random_clones(question_list, list_dir[4], constraint=constraint_2)
        encoder.write_random_clones(
            question_list, list_dir[5], constraint=constraint_custom
        )
    except MaxIterError:
        print("constraint_2 ou constraint_custom pas possible")
# %%
"""-------dev:ignorer cette partie----------------"""
do_test = False
if do_test:
    for question in question_list:
        clones = question.get_random_clones(constraint=constraint_custom)
        c_T, c_F = Constraint.counter_from_clones_list(clones)
        print(
            f"set : {len(set(clones))} count T : {min((c_T).values()), max((c_T).values())} --- count F : {min((c_T).values()), max((c_T).values())}"
        )

# %%
