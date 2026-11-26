# The theological boundary: the Creed of 381, and why

Dust adds exactly one theological boundary to an open model: the Niceno-Constantinopolitan
Creed of AD 381. This document says precisely where that line falls, why it was chosen,
what it leaves open, and why choosing a minimum does not water down the gospel.

It builds on the position paper *Christian AI Alignment and the Nicene Creed of 381*
(Always Foundation, November 2026, CC BY 4.0) and on Always Foundation's published Creed
propositions. Dust's contribution is to make the boundary machine-checkable and to
measure it.

## 1. What is inside the boundary

The Creed confesses, and Dust encodes as 24 propositions (`src/dust/data/creed.json`):

| Article | Propositions | The line it draws |
|---|---|---|
| One God, the Father Almighty, Maker of all things | P01, P02 | One God; the material world is the good work of that God (against Gnostic dualism and Marcion) |
| One Lord Jesus Christ, only-begotten, before all ages | P04, P05 | The Son is eternal and not a creature (against Arius: "there was when he was not") |
| True God from true God, of one substance (*homoousios*) | P06, P07 | Full and equal deity (against Arian and semi-Arian subordination of being) |
| Through whom all things were made | P08 | The Son is Creator, not creature |
| For us and for our salvation ... incarnate ... of the Virgin Mary ... made man | P09, P10, P11 | Real incarnation, virgin birth, full humanity (against docetism and Apollinarius) |
| Crucified under Pontius Pilate, suffered, buried | P12 | A real, datable death |
| Rose on the third day according to the Scriptures; ascended; seated | P13, P14 | Bodily resurrection; ascension |
| Will come again to judge; kingdom without end | P15, P16 | Return and judgement (and against Marcellus of Ancyra) |
| The Holy Spirit, Lord and Giver of life, proceeding from the Father, worshipped and glorified with the Father and the Son, who spoke through the prophets | P17-P20, P03 | The Spirit is fully divine and personal; Father, Son and Spirit are distinct (against the Pneumatomachians and modalism) |
| One holy, catholic and apostolic Church; one baptism for the forgiveness of sins | P21, P22 | Treated as *ecclesial*: Dust annotates rather than blocks (see section 5) |
| Resurrection of the dead; life of the world to come | P23, P24 | Hope beyond death |

Each proposition carries its Greek anchor phrase, so that a reviewer can check the
encoding against the conciliar text rather than against an English paraphrase, and two
or three Scripture references (World English Bible, public domain).

## 2. What falls outside

Sixteen historic positions are encoded as excluded errors, each linked to the
propositions it contradicts and to where the Church rejected it (E01-E16 in
`creed.json`): Arianism; semi-Arian (homoiousian) subordinationism; modalism; adoptionism;
psilanthropism ("merely human" Christologies); pneumatomachianism; docetism;
Apollinarianism; Gnostic dualism and Marcionism; tritheism and polytheism;
Marcellianism; and denials of the virgin birth, of Christ's bodily resurrection, of his
return and judgement, of the resurrection of the dead, and of the Son's role in creation.

Several of these are named in the first canon of Constantinople itself (Eunomians or
Anomoeans, Arians or Eudoxians, Semi-Arians or Pneumatomachi, Sabellians, Marcellians,
Photinians and Apollinarians). The boundary is therefore not an invention of Dust; it is
the line the Council drew.

Movements today that do not confess the Trinity as the Creed does fall outside this line.
Always Foundation's position paper names several. Dust does not need to: its checker
looks at *statements*, not at communities. This describes a doctrinal line, not a
judgement of any person, and the code is free for anyone to read and use.

## 3. Why 381, and not something smaller or larger

**It predates the divisions.** The Creed was received before the Christological
divisions of the fifth century, before the East-West schism and before the Reformation.
No later tradition owns it.

**It is the most widely confessed Christian text.** The Roman Catholic, Eastern Orthodox,
Oriental Orthodox, Assyrian Church of the East, Anglican, Lutheran, Reformed and
Presbyterian churches confess it, and Methodist churches use it liturgically. Many Baptist,
Pentecostal, charismatic and evangelical churches do not formally adopt creeds but hold
its Trinitarian faith, usually in their own statements of faith.

**It is definite.** It says who God is in short, propositional clauses. That makes it
checkable by a machine and arguable by a person.

**It is short.** It fits in every prompt and breaks into two dozen propositions.

**Why not something smaller**, such as "Jesus is Lord"? Because nearly every movement in
section 2 would affirm a bare slogan. The fourth-century debates were precisely about what
such confessions mean. A smaller boundary would not be a boundary.

**Why not something larger**, such as Chalcedon (451), the Westminster Confession, the
Catechism of the Catholic Church or the Thirty-Nine Articles? Because each later
definition is confessed by a subset of the churches that confess 381. The most important
case is Chalcedon: the Oriental Orthodox churches (Coptic, Ethiopian, Eritrean, Syriac,
Armenian, Malankara) and the Assyrian Church of the East confess the Creed of 381 but not
the definition of 451, and joint declarations since the 1970s and 1990s have recognised
substantial Christological agreement. Setting the boundary at 381 keeps them inside on
purpose (latitude topic L02).

## 4. The Filioque

The Greek text of 381 confesses that the Spirit "proceeds from the Father" (τὸ ἐκ τοῦ
Πατρὸς ἐκπορευόμενον). The Latin West later added *Filioque*, "and the Son"; the addition
was first made in Spain (it is associated with the Third Council of Toledo, 589), spread
through the Frankish church and was adopted in Rome in the eleventh century. It became
one of the theological issues in the division between East and West.

Dust's position (P18, L01):

* The proposition it checks is the one every tradition affirms: **the Spirit proceeds from
  the Father**, and is fully divine (P19).
* "From the Father and the Son", "from the Father alone" and "from the Father through the
  Son" are all inside the boundary. The checker blocks only a denial that the Spirit
  proceeds from the Father, which no tradition holds.
* The English text Dust carries follows 381 (no Filioque); the Latin liturgical text is
  bundled too and is labelled as containing the addition.

Why this is fair rather than evasive: the dispute is real and concerns the eternal
relations of origin, whether a local church may amend a conciliar creed, and authority in
the Church. But it is a dispute between Trinitarians about the Trinity. Both sides confess
one God in three persons, the full deity of the Spirit and the same Creed apart from one
phrase. A boundary that excluded either side would exclude roughly half of historic
Christianity over a question both sides frame inside Trinitarian faith.

## 5. What Dust deliberately does not decide

Latitude topics L01-L11 in `creed.json` list the questions on which the Creed is silent or
on which traditions that confess it read it differently: baptism (subjects, mode,
sacramental meaning), the Lord's Supper, the identity and government of the Church, Mary
beyond the virgin birth, justification and salvation, Scripture and Tradition and the
canon, creation and science, the last things, spiritual gifts, ministry and worship.

On these the constitution tells the model to set out the main Catholic, Orthodox and
Protestant positions fairly and not to choose. The evaluation set checks this: 42
latitude statements, from both sides of each question, must *not* be blocked. The final
false-positive rate on them is 4.8% (2 of 42; see `results/benchmark.md`).

The ecclesial articles (Church and baptism, P21-P22) are confessed by all, but each
tradition identifies the one Church differently, and some Christian bodies (for example
the Quakers and the Salvation Army) do not practise water baptism. Dust therefore annotates
rather than blocks on these articles, and it has no denial patterns for baptism at all.

Two further cases are worth naming because a careless checker would get them wrong:

* **Functional subordination.** Some evangelicals hold that the Son eternally submits to
  the Father in role while being equal in being. Whatever one thinks of it, it does not
  deny *homoousios*. Dust blocks inequality *in being, essence, nature or divinity*, not
  talk of roles; the evaluation includes a case for this.
* **Final destiny.** Conditional immortality and hope for universal reconciliation are
  debated, but neither denies return, judgement or resurrection. Dust flags only outright
  denials of those (L10).

## 6. Why a minimum does not compromise the gospel

A fair worry is that a lowest-common-denominator boundary trades truth for unity. Five
reasons it does not:

1. **The Creed is gospel-shaped.** Its second article follows the outline of the gospel
   Paul says he received and handed on: that Christ died for our sins according to the
   Scriptures, that he was buried, that he was raised on the third day according to the
   Scriptures (1 Corinthians 15:3-4). "For us and for our salvation ... crucified for us
   ... rose again on the third day according to the Scriptures" is not a reduction of the
   gospel; it is its spine.
2. **It is not neutral about God.** The boundary is narrow in scope and firm in content:
   neutral between denominations, not neutral about who Christ is. The model is told to
   affirm the Creed plainly, not to present it as one opinion among many.
3. **It is a floor, not a ceiling.** Dust does not claim that the Creed says everything a
   church must confess. Every tradition holds more than the Creed, and many would say the
   gospel itself includes truths the Creed does not spell out (for Protestants, for
   example, justification by faith; for Catholics and Orthodox, the sacramental life of
   the Church). Dust does not deny those truths; it declines to decide between traditions
   that confess the same Creed. A church, denomination or ministry may fork Dust and add
   its own confession as a further layer under its own name. That is how the layer stack
   is meant to work: model maker's specification, then Nicaea, then local confession.
4. **It describes rather than adjudicates salvation.** The checker tests statements
   against propositions. It makes no claim about who is saved, and it is not a test of
   anyone's faith.
5. **Unity around the Creed is itself a gospel concern.** Jesus prayed that his followers
   would be one (John 17:21). The Creed is the text that Catholic, Orthodox and Protestant
   Christians can still say together. Building shared infrastructure on that text, rather
   than on any one tradition's distinctives, is an act of that unity, not a retreat from
   conviction.

## 7. Limits

* The encoding is a model of the Creed, made by people, and can be wrong. Propositions,
  Greek anchors, errors and latitude topics are published so that theologians from
  different traditions can correct them. No formal review by such a panel has happened
  yet; that is the most important next step.
* Pattern-based checking reads sentences, not intentions. Sarcasm, irony and long
  arguments can defeat it, and the benchmark lists every case it gets wrong.
* Pastoral wisdom cannot be reduced to propositions. Dust is a layer for study tools, not
  a substitute for a pastor, priest or church.

## References

* Always Foundation, *Christian AI Alignment and the Nicene Creed of 381* (position paper,
  November 2026) and `ai/creed/nicene-381.json`, alwaysfoundation/always-platform, CC BY 4.0.
* Council of Constantinople (381), Creed and Canon 1, in N. P. Tanner (ed.), *Decrees of the
  Ecumenical Councils*, vol. 1 (1990).
* P. Schaff, *The Creeds of Christendom*, vol. 1 (1877) and vol. 2 (Greek and Latin texts).
* J. N. D. Kelly, *Early Christian Creeds*, 3rd ed. (1972).
* Common Christological Declaration between the Catholic Church and the Assyrian Church of
  the East (1994); joint statements of the Orthodox and Oriental Orthodox churches
  (Chambésy, 1990).
* Lutheran World Federation and Catholic Church, *Joint Declaration on the Doctrine of
  Justification* (1999).
