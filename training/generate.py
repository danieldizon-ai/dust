"""Generate the synthetic training set for the neural guard.

    python training/generate.py            # writes data/train.jsonl

Every row is {"text", "label", "group", "lang", "frame"} where label is one of
"contradicts" (the speaker asserts something the Creed of 381 excludes), "consistent"
(the speaker asserts something inside the boundary, including positions on which
orthodox traditions differ) and "neutral" (reported views, questions, history,
off-topic text).

The set is built compositionally from clause templates x subjects x frames, with a
fixed seed. It is deliberately separate from the hand-written evaluation set in
data/eval/, which uses different wording; bench/run.py checks for overlap.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "train.jsonl"
SEED = 381

SON = ["Jesus", "Christ", "Jesus Christ", "the Son", "the Son of God", "the Lord Jesus", "Jesus of Nazareth"]
SPIRIT = ["the Holy Spirit", "the Spirit", "the Holy Ghost"]

# (group, contradicting clauses, consistent clauses). {S} = Son, {H} = Spirit.
LOCI = [
    ("son-eternal",
     ["{S} was created by God", "{S} is a creature", "{S} is the first being God ever made",
      "there was a time when {S} did not exist", "{S} had a beginning", "{S} came into existence at a point in time",
      "{S} is an angel, the highest of the angels", "{S} was produced by the Father as the first creation",
      "God made {S} before he made the world", "{S} is Michael the archangel",
      "{S} became the Son of God when he was baptised", "God adopted {S} as his Son because he was so righteous",
      "{S} earned divine status by his obedience", "{S} was not begotten before all ages"],
     ["{S} is eternally begotten of the Father", "{S} was begotten, not made", "{S} has always existed with the Father",
      "{S} existed before all ages", "there was never a time when {S} was not", "{S} is not a created being",
      "{S} is the only-begotten Son of God"]),
    ("son-divine",
     ["{S} was only a man", "{S} was merely a wise teacher", "{S} was a prophet and nothing more",
      "{S} is not God", "{S} was a good moral example but not divine", "{S} is a lesser god than the Father",
      "{S} is a god, but not God Almighty", "{S} is of a similar but different substance from the Father",
      "{S} is inferior to the Father in his very being", "{S} was an ordinary human being",
      "{S} never was divine", "{S} is a demigod"],
     ["{S} is true God from true God", "{S} is fully divine", "{S} is of one substance with the Father",
      "{S} is equal to the Father in being", "{S} is God incarnate", "{S} is Lord and God",
      "{S} shares the same divine nature as the Father", "{S} is not merely a man"]),
    ("creation-through-son",
     ["{S} had no part in creation", "the world was made without {S}", "the universe was created before {S} existed"],
     ["all things were made through {S}", "{S} made all things with the Father", "through {S} the universe was created"]),
    ("incarnation",
     ["{S} only seemed to be human", "{S} only appeared to have a body", "{S} had no real human body",
      "{S} was a phantom and not a real man", "{S} had no human mind; the divine Word replaced it",
      "Joseph was the biological father of {S}", "{S} had a human father like everyone else",
      "the virgin birth is a myth", "Mary was not a virgin when she conceived {S}", "the virgin birth never happened",
      "{S} pretended to be a man"],
     ["{S} became truly human", "{S} took on human flesh", "{S} was born of the Virgin Mary",
      "{S} was conceived by the Holy Spirit", "{S} is fully human and fully divine", "the Word became flesh",
      "{S} had a real human body and a human soul", "{S} came down from heaven for our salvation"]),
    ("crucifixion",
     ["{S} did not really die on the cross", "{S} swooned on the cross and later revived", "{S} survived the crucifixion",
      "someone else was crucified in his place", "{S} never existed", "{S} is a myth invented by the church",
      "{S} only appeared to die", "{S} was never crucified"],
     ["{S} was crucified under Pontius Pilate", "{S} truly suffered and died", "{S} died and was buried",
      "{S} was crucified for us"]),
    ("resurrection",
     ["{S} did not rise from the dead", "the resurrection is only a metaphor", "the resurrection was a hallucination",
      "his body stayed in the tomb", "{S} rose only in the hearts of his followers", "the tomb was not empty",
      "the resurrection is just a symbol of hope", "{S} never rose again", "{S} is still dead"],
     ["{S} rose bodily from the dead", "{S} rose again on the third day", "the tomb was empty because {S} was raised",
      "{S} was raised from the dead according to the Scriptures", "{S} is risen"]),
    ("ascension",
     ["{S} never ascended to heaven"],
     ["{S} ascended into heaven", "{S} sits at the right hand of the Father"]),
    ("return-judgement",
     ["{S} will never come back", "there will be no second coming", "there will be no final judgement",
      "the second coming is a myth", "his kingdom will come to an end", "the reign of {S} is temporary",
      "{S} will not judge anyone"],
     ["{S} will come again in glory", "{S} will judge the living and the dead", "his kingdom will have no end",
      "{S} will return"]),
    ("holy-spirit",
     ["{H} is an impersonal force", "{H} is just God's active force", "{H} is only an energy", "{H} is not a person",
      "{H} is a created being", "{H} should not be worshipped", "{H} is just an influence", "{H} is not God",
      "{H} is a power God created", "{H} does not proceed from the Father"],
     ["{H} is the Lord and Giver of life", "{H} is fully God", "{H} is worshipped together with the Father and the Son",
      "{H} proceeds from the Father", "{H} proceeds from the Father and the Son", "{H} proceeds from the Father through the Son",
      "{H} spoke through the prophets", "{H} is a divine person"]),
    ("trinity",
     ["the Father, the Son and the Spirit are three modes of one person", "God is one person who plays three roles",
      "the Father became the Son and then the Spirit", "the Father died on the cross", "{S} is the Father in human form",
      "Father, Son and Spirit are just three names for one person", "there are three gods",
      "the Father, the Son and the Spirit are three separate gods"],
     ["Father, Son and Holy Spirit are three distinct persons", "there is one God in three persons",
      "the Son is not the Father", "God is one, and Father, Son and Spirit are distinct"]),
    ("one-god",
     ["the material world was created by an evil god", "matter is evil and was not made by the true God",
      "a lesser demiurge made the world", "the God of the Old Testament is not the Father of Jesus",
      "there are many gods"],
     ["there is one God", "God made heaven and earth", "God created all things, visible and invisible",
      "the God of Israel is the Father of Jesus"]),
    ("resurrection-dead",
     ["there is no resurrection of the dead", "death is the final end", "there is no life after death",
      "when we die we cease to exist forever", "the dead will never rise"],
     ["the dead will be raised", "we look for the resurrection of the dead", "there is a life of the world to come"]),
]

# Consistent statements that contain a negation word. Added in iteration 2 after the dev
# split showed the guard reads "not"/"never" as a sign of heresy. Wording deliberately
# differs from the evaluation set (bench/run.py reports any near duplicates).
NEGATED_OK = [
    ("son-eternal", "{S} never had a beginning"), ("son-eternal", "{S} was not made by anyone"),
    ("son-eternal", "{S} is no creature at all"), ("son-eternal", "{S} did not come into being at some moment"),
    ("son-divine", "{S} was never only a prophet"), ("son-divine", "{S} is not a lesser god"),
    ("son-divine", "{S} is not inferior to the Father in being"), ("trinity", "the persons of the Trinity are not modes"),
    ("trinity", "Christians do not worship three gods"), ("trinity", "the Father is not the Son"),
    ("holy-spirit", "{H} is not a thing or an energy"), ("holy-spirit", "{H} was never created"),
    ("incarnation", "{S} did not pretend to be human"), ("incarnation", "the humanity of {S} was not an illusion"),
    ("crucifixion", "the death of {S} was not faked"), ("crucifixion", "{S} did not escape death on the cross"),
    ("resurrection", "the body of {S} did not remain in the grave"), ("resurrection", "the resurrection was no hallucination"),
    ("resurrection", "the empty tomb is not a legend"), ("return-judgement", "the kingdom of {S} will not end"),
    ("resurrection-dead", "the grave is not the last word"), ("one-god", "matter is not evil"),
]

HISTORY_NEUTRAL = [
    "Eastern churches recite the Creed without the words 'and the Son'.", "The Latin West added the Filioque over several centuries.",
    "The Council of Toledo in 589 is often linked with the Filioque.", "In 1054 the churches of Rome and Constantinople divided.",
    "The Creed was expanded at Constantinople to say more about the Spirit.", "Catholic and Orthodox theologians still discuss the Filioque.",
    "Some Anglican provinces print the Creed without the Filioque.", "Luther kept the Nicene Creed in the German Mass.",
    "Calvin valued the early creeds.", "The Oriental Orthodox churches did not accept Chalcedon.",
]

LATITUDE = [
    "infants should be baptised", "only believers should be baptised", "baptism should be by full immersion",
    "baptism is a sign and not a means of grace", "baptism washes away sin",
    "the bread and wine become the body and blood of Christ", "the Lord's Supper is a memorial",
    "Christ is spiritually present in communion", "the Pope is the successor of Peter",
    "the papacy has no biblical basis", "the Spirit proceeds from the Father and the Son",
    "the filioque should not have been added to the Creed", "the Spirit proceeds from the Father alone",
    "the millennium is symbolic", "Christ will reign on earth for a thousand years before the end",
    "God created the world through evolution", "the earth is young", "the days of Genesis are long ages",
    "women can be ordained as pastors", "only men should be elders", "the gifts of tongues have ceased",
    "the gift of prophecy continues today", "Mary was immaculately conceived", "Mary had other children after Jesus",
    "we are justified by faith alone", "justification involves faith and works of love",
    "salvation is participation in the divine life", "purgatory exists", "there is no purgatory",
    "icons may be venerated", "icons should not be used in worship", "the deuterocanonical books are Scripture",
    "the Protestant canon has 66 books", "Scripture alone is the final authority",
    "Scripture and Tradition together carry authority", "hell is eternal conscious punishment",
    "the wicked will finally be destroyed rather than suffer forever", "predestination is unconditional",
    "God's grace can be resisted", "worship should follow a liturgy", "worship should be spontaneous",
    "Christ has two natures in one person", "Christ has one incarnate nature of God the Word",
]

ASSERT_FRAMES = ["{c}.", "I believe {c}.", "Honestly, {c}.", "The truth is that {c}.", "In reality, {c}.",
                 "Let me be clear: {c}.", "{C}, and that is the plain truth.", "Most people miss this, but {c}.",
                 "Scripture shows that {c}.", "My answer is simple: {c}.", "It is a fact that {c}.",
                 "We should accept that {c}.", "{C}.", "Yes, {c}.", "The correct view is that {c}."]
REPORTED_FRAMES = ["Arius taught that {c}.", "Some groups claim that {c}.", "Critics argue that {c}.",
                   "The heretical view was that {c}.", "Historically, some sects held that {c}.",
                   "According to the Gnostics, {c}.", "One ancient heresy taught that {c}.",
                   "Skeptical scholars say that {c}.", "The idea that {c} was condemned by the councils.",
                   "Certain writers have suggested that {c}."]
QUESTION_FRAMES = ["Is it true that {c}?", "Did the early church believe that {c}?", "Why do some people say that {c}?",
                   "Can a Christian say that {c}?", "What does the Creed say about whether {c}?"]
REJECT_FRAMES = ["It is false to say that {c}.", "The Creed rejects the idea that {c}.", "Christians deny that {c}.",
                 "No one should claim that {c}.", "The church has always rejected the claim that {c}.",
                 "It is not true that {c}."]

NEUTRAL = [
    "Paul wrote his first letter to the Corinthians around AD 55.", "The Council of Nicaea met in 325.",
    "Constantinople hosted the second ecumenical council in 381.", "Here is a summary of the Gospel of Mark.",
    "The weather in Sydney is warm today.", "Here is a Python function that sorts a list.",
    "Athanasius was bishop of Alexandria.", "The Septuagint is a Greek translation of the Hebrew Scriptures.",
    "Let us read Psalm 23 together.", "The book of Acts describes the early church in Jerusalem.",
    "Greek has several words for love.", "The Reformation began in 1517.", "Many churches recite the Creed on Sundays.",
    "This passage has three main sections.", "The word homoousios means of the same substance.",
    "Augustine wrote The City of God.", "I can help you outline a Bible study.", "The Dead Sea Scrolls were found in 1947.",
    "Here are three questions for small group discussion.", "The Creed was written in Greek.",
    "Our meeting starts at seven.", "Translation choices affect how a verse reads.", "The Gospel of John has 21 chapters.",
    "Let me know which passage you want to study.", "Gregory of Nazianzus preached five theological orations.",
]

# Spanish and Portuguese training clauses (other languages are left unseen for the zero-shot test).
ML = {
    "es": {
        "contradicts": [("son-eternal", "Jesús fue creado por Dios"), ("son-eternal", "hubo un tiempo en que el Hijo no existía"),
                        ("son-divine", "Jesús fue solo un hombre"), ("son-divine", "Cristo no es Dios"),
                        ("holy-spirit", "el Espíritu Santo es una fuerza impersonal"), ("resurrection", "Jesús no resucitó de entre los muertos"),
                        ("resurrection", "la resurrección es solo una metáfora"), ("trinity", "el Padre, el Hijo y el Espíritu son solo tres modos de una persona"),
                        ("incarnation", "Jesús solo parecía ser humano"), ("crucifixion", "Jesús no murió realmente en la cruz")],
        "consistent": ["Jesús es verdadero Dios de verdadero Dios", "el Hijo fue engendrado, no creado", "Jesús resucitó al tercer día",
                       "el Espíritu Santo es Señor y dador de vida", "hay un solo Dios en tres personas", "Cristo se hizo verdaderamente hombre",
                       "los niños deben ser bautizados", "solo los creyentes deben ser bautizados"],
        "frames": ["{c}.", "Creo que {c}.", "La verdad es que {c}."],
        "reported": ["Arrio enseñó que {c}.", "Algunos grupos afirman que {c}."],
    },
    "pt": {
        "contradicts": [("son-eternal", "Jesus foi criado por Deus"), ("son-divine", "Jesus foi apenas um homem"),
                        ("son-divine", "Cristo não é Deus"), ("holy-spirit", "o Espírito Santo é uma força impessoal"),
                        ("resurrection", "Jesus não ressuscitou dos mortos"), ("resurrection", "a ressurreição é apenas uma metáfora"),
                        ("trinity", "o Pai, o Filho e o Espírito são apenas três modos de uma pessoa"), ("incarnation", "Jesus apenas parecia ser humano")],
        "consistent": ["Jesus é Deus verdadeiro de Deus verdadeiro", "o Filho foi gerado, não criado", "Jesus ressuscitou ao terceiro dia",
                       "o Espírito Santo é Senhor e doador da vida", "há um só Deus em três pessoas", "as crianças devem ser batizadas"],
        "frames": ["{c}.", "Eu creio que {c}.", "A verdade é que {c}."],
        "reported": ["Ário ensinou que {c}.", "Alguns grupos afirmam que {c}."],
    },
}


def _fill(clause: str, rng: random.Random) -> str:
    return clause.replace("{S}", rng.choice(SON)).replace("{H}", rng.choice(SPIRIT))


def _frame(frame: str, clause: str) -> str:
    c = clause[0].lower() + clause[1:] if not clause.startswith(("I ", "Jesus", "Christ", "Mary", "God", "Joseph", "Father")) else clause
    return frame.replace("{c}", c).replace("{C}", clause[0].upper() + clause[1:])


def build(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []

    def add(text, label, group, frame, lang="en"):
        rows.append({"text": text, "label": label, "group": group, "lang": lang, "frame": frame})

    for group, contra, affirm in LOCI:
        for clause in contra:
            for _ in range(6):
                add(_frame(rng.choice(ASSERT_FRAMES), _fill(clause, rng)), "contradicts", group, "assert")
            for _ in range(2):
                add(_frame(rng.choice(REPORTED_FRAMES), _fill(clause, rng)), "neutral", group, "reported")
            add(_frame(rng.choice(QUESTION_FRAMES), _fill(clause, rng)), "neutral", group, "question")
            add(_frame(rng.choice(REJECT_FRAMES), _fill(clause, rng)), "consistent", group, "reject")
        for clause in affirm:
            for _ in range(5):
                add(_frame(rng.choice(ASSERT_FRAMES), _fill(clause, rng)), "consistent", group, "assert")
            add(_frame(rng.choice(QUESTION_FRAMES), _fill(clause, rng)), "neutral", group, "question")
            add(_frame(rng.choice(REJECT_FRAMES[2:3] + ["I deny that {c}.", "It is wrong to believe that {c}."]), _fill(clause, rng)),
                "contradicts", group, "reject")
    for group, clause in NEGATED_OK:
        for _ in range(4):
            add(_frame(rng.choice(ASSERT_FRAMES), _fill(clause, rng)), "consistent", group, "negated")
    for text in HISTORY_NEUTRAL:
        for _ in range(2):
            add(text, "neutral", "none", "history")
    for clause in LATITUDE:
        for _ in range(4):
            add(_frame(rng.choice(ASSERT_FRAMES), clause), "consistent", "latitude", "latitude")
        add(_frame(rng.choice(QUESTION_FRAMES), clause), "neutral", "latitude", "question")
    for text in NEUTRAL:
        for _ in range(3):
            add(text, "neutral", "none", "neutral")
    for lang, spec in ML.items():
        for group, clause in spec["contradicts"]:
            for f in spec["frames"]:
                add(_frame(f, clause), "contradicts", group, "assert", lang)
            add(_frame(rng.choice(spec["reported"]), clause), "neutral", group, "reported", lang)
        for clause in spec["consistent"]:
            for f in spec["frames"]:
                add(_frame(f, clause), "consistent", "latitude" if "bauti" in clause or "batiz" in clause else "affirm", "assert", lang)
    # de-duplicate exact repeats, then shuffle
    seen, uniq = set(), []
    for r in rows:
        if r["text"] not in seen:
            seen.add(r["text"])
            uniq.append(r)
    rng.shuffle(uniq)
    return uniq


def main() -> None:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print(f"wrote {len(rows)} rows to {OUT.relative_to(ROOT)}: {counts}")


if __name__ == "__main__":
    main()
