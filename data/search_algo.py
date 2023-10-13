import itertools
from rake_nltk import Rake
from backend import log


def _install_stopwords_punkt():
    import nltk

    nltk.download('stopwords')
    nltk.download('punkt')


class SearchCorpus:
    def __init__(self):
        self.corpus = []
        try:
            self.r = Rake()
        except LookupError:
            log.warning("Stopwords/punkt not found, downloading...")
            _install_stopwords_punkt()

            self.r = Rake()

    class Sentence:
        def __init__(self, sentence, model):

            self.raw = sentence
            self.sentence = sentence.lower()

            try:
                self.keywords = model.extract_keywords_from_text(sentence)
                self.ranked_phrases = set(model.get_ranked_phrases_with_scores())
            except LookupError:
                log.warning("Stopwords/punkt not found, downloading...")
                _install_stopwords_punkt()

                self.keywords = model.extract_keywords_from_text(sentence)
                self.ranked_phrases = set(model.get_ranked_phrases_with_scores())

        def __str__(self):
            return f"Sentence: {self.sentence}\nKeywords: {self.keywords}\nRanked Phrases: {self.ranked_phrases}"

        def __repr__(self):
            return f"Sentence: {self.sentence}\nKeywords: {self.keywords}\nRanked Phrases: {self.ranked_phrases}"

    def add_(self, sentence):
        self.corpus.append(self.Sentence(sentence, self.r))
        print(len(self.corpus))

    def search(self, query, amount=1) -> list or None:
        try:
            query = query.lower()

            # query = query.replace("class", "grade")
            # query = query.replace("periodic test", "pt")

            list_of_roman = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
            # for i in range(len(query.split(" "))):
            #     if query.split(" ")[i - 1] != "pt" and query.split(" ")[i].isdigit():
            #         query = query.replace(str(query.split(" ")[i]), list_of_roman[int(query.split(" ")[i]) - 1])

            self.r.extract_keywords_from_text(query)
            keyword = set(self.r.get_ranked_phrases_with_scores())

            results = []
            corpus_phrases = set(itertools.chain.from_iterable(corp.ranked_phrases for corp in self.corpus))

            for corp in self.corpus:
                if any(keyword_ in corp.ranked_phrases for keyword_ in keyword):
                    results.append([8, corp])
                else:
                    for keyword__ in keyword:
                        if keyword__ in corpus_phrases:
                            results.append([1, corp])
                        if keyword__ in corp.ranked_phrases:
                            results.append([2, corp])

                    for keyword___ in itertools.combinations(keyword, 2):
                        if keyword___ in corp.ranked_phrases:
                            results.append([2, corp])

            results = sorted(results, key=lambda x: x[0], reverse=True)


            return [a[1].raw for a in results[:amount]]

        except IndexError:
            return None
        except Exception as e:
            print(e)
            return None

    def __repr__(self):
        return "\n".join(str(a) for a in self.corpus) + "\n"

    def __str__(self):
        return "\n".join(str(a) for a in self.corpus) + "\n"
