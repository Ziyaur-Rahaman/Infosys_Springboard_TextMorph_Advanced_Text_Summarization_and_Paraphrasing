
import textstat

class ReadabilityAnalyzer:
    def __init__(self, text):
        self.text = text
        self.num_sentences = textstat.sentence_count(text)
        self.num_words = textstat.lexicon_count(text, removepunct=True)
        self.num_syllables = textstat.syllable_count(text)
        self.complex_words = textstat.difficult_words(text)
        self.char_count = textstat.char_count(text)

    def get_all_metrics(self):
        return {
            "Flesch Reading Ease": round(textstat.flesch_reading_ease(self.text), 1),
            "Flesch-Kincaid Grade": round(textstat.flesch_kincaid_grade(self.text), 1),
            "SMOG Index": round(textstat.smog_index(self.text), 1),
            "Gunning Fog": round(textstat.gunning_fog(self.text), 1),
            "Coleman-Liau": round(textstat.coleman_liau_index(self.text), 1),
        }
