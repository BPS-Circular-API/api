from unittest import result
import requests
import itertools
import functools
from rake_nltk import Rake


class SearchCorpus():
    def __init__(self) -> None:
        self.corpus = []
        self.r = Rake()

    # sentence class
    class Sentence():
        def __init__(self, sentence: str, model: Rake) -> None:
            self.raw = sentence
            self.sentence = sentence.lower()
            self.keywords = model.extract_keywords_from_text(sentence)
            self.ranked_phrases = model.get_ranked_phrases_with_scores()

        def __str__(self) -> str:
            return f"""Sentence: {self.sentence}
Keywords: {self.keywords}
Ranked Phrases: {self.ranked_phrases}"""

        def __repr__(self) -> str:
            return f"""Sentence: {self.sentence}
Keywords: {self.keywords}
Ranked Phrases: {self.ranked_phrases}"""

    # function to adds

    def add_(self, sentence: str) -> None:
        self.corpus.append(self.Sentence(sentence, self.r))

    # function to search
    def search(self, q: str, prnt: bool = False) -> list:
        q = q.lower()

        # CRITERION AND CUSTOM FILTERING
        # Replace "class" with "grade"
        q = q.replace("class", "grade")

        # Replace periodic test with pt
        q = q.replace("periodic test", "pt")

        # Replace numbers with ronam munerals
        list_of_roman = ["i", "ii", "iii", "iv", "v",
                         "vi", "vii", "viii", "ix", "x", "xi", "xii"]
        for i in range(len(q.split(" "))):
            # if the previous word is not 'pt'
            print(q.split(" ")[i-1] == "pt")
            if (q.split(" ")[i-1] == "pt") is False and (q.split(" ")[i].isdigit()) is True:
                # replace other words, with their roman numeral
                q = q.replace(
                    str(q.split(" ")[i]), list_of_roman[int(q.split(" ")[i])-1])
        print(q)
        # rake the keyword
        self.r.extract_keywords_from_text(q)
        keyword = self.r.get_ranked_phrases_with_scores()
        print(keyword)

        results = []
        for corp in self.corpus:
            # print([c[1] for c in corp.ranked_phrases])
            for keyword_ in keyword:
                # if result directly in ranked phrases
                if keyword_[1] in [c[1] for c in corp.ranked_phrases]:
                    # WEIGHTAGE: 10
                    if corp in [c[1] for c in results]:
                        results[[c[1] for c in results].index(corp)][0] += 8
                    else:
                        results.append([8, corp])
                else:
                    for keyword__ in keyword_[1].split(" "):
                        # if words in keyword's ranked phrases in the corpus ranked phrases
                        if keyword__ in "".join([c[1] for c in corp.ranked_phrases]):
                            if corp in [c[1] for c in results]:
                                results[[c[1]
                                         for c in results].index(corp)][0] += 1
                            else:
                                results.append([1, corp])

                        if keyword__ in [c[1] for c in corp.ranked_phrases]:
                            # WEIGHTAGE: 2
                            if corp in [c[1] for c in results]:
                                results[[c[1]
                                         for c in results].index(corp)][0] += 2
                            else:
                                results.append([2, corp])

            # print([" ".join(string) for string in list(
            #     itertools.combinations(keyword_[1].split(" "), 2))])
            for keyword___ in [" ".join(string) for string in list(itertools.combinations(keyword_[1].split(" "), 2))]:
                # if any of the possible pair of words in keyword's ranked phrases in the corpus ranked phrases
                # print(keyword___, [c[1] for c in corp.ranked_phrases])
                if keyword___ in [c[1] for c in corp.ranked_phrases]:
                    # WEIGHTAGE: 2
                    if corp in [c[1] for c in results]:
                        results[[c[1] for c in results].index(corp)][0] += 2
                    else:
                        results.append([2, corp])

        # sort results based on weightage
        results = sorted(results, key=lambda x: x[0], reverse=True)

        if prnt is True:
            string__ = ""
            for a__ in [a__ for a__ in results]:
                string__ += f"{a__}\n"
                string__ += "\n"
            print(string__)

        print(results[0])
        return results[0][1].raw

    def __repr__(self) -> str:
        string = ""
        for a in [a for a in self.corpus]:
            string += f"{a}\n"
        string += "\n"
        return string

    def __str__(self) -> str:
        string = ""
        for a in [a for a in self.corpus]:
            string += f"{a}\n"
        string += "\n"
        return string
