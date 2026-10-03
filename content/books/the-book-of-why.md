---
title: "The Book of Why"
author: "Judea Pearl and Dana Mackenzie"
category: decisions
year: 2018
one_line: "A pioneer of artificial intelligence explains how scientists learned to reason about cause and effect with diagrams and simple rules, after a century in which statistics would only talk about correlation."
sources:
  - https://en.wikipedia.org/wiki/The_Book_of_Why
  - https://www.ams.org/journals/notices/201907/rnoti-p1093.pdf
  - https://booksummaryclub.com/summary-of-the-book-of-why-by-judea-pearl-and-dana-mackenzie/
review: "check"
---

## In short

For most of the twentieth century, statisticians taught that data can show correlation but can't prove causation, and many stopped asking causal questions at all. Judea Pearl, a computer scientist and Turing Award winner, writing with the science writer Dana Mackenzie, tells the story of the "causal revolution" that changed this. With causal diagrams and a small set of rules, he argues, we can often answer questions like "Does smoking cause cancer?" or "What would have happened if...?" from data, and machines will need the same tools to think like people.

## Summary

The book's central image is the Ladder of Causation, introduced in Chapter 1. On the bottom rung is association: seeing that two things go together, which is what most statistics and most current machine learning do. On the second rung is intervention: asking what happens if I do something, such as take an aspirin or raise a price. On the top rung are counterfactuals: imagining what would have happened if things had been different, as in "Would my headache have gone without the aspirin?" Pearl argues that humans climbed this ladder early, and points to a carved lion-headed figure about 40,000 years old as a sign of our ability to imagine things that don't exist. Data alone, he insists, can't get you off the bottom rung. You also need a model of how the world works.

Chapter 2 explains how statistics lost its interest in causes. Francis Galton discovered regression to the mean while studying the heights of parents and children, and his follower Karl Pearson went further, treating correlation as the real science and causation as a primitive idea. A lone exception was the geneticist Sewall Wright, who around 1920 drew arrow diagrams of what causes what to study the coat colours and birth weights of guinea pigs. His path diagrams were attacked and largely ignored for decades; Pearl sees them as the ancestor of his own methods.

Chapter 3 tells Pearl's own story. In the 1980s he developed Bayesian networks, which let computers update beliefs as evidence comes in, combining the 18th-century rule of Thomas Bayes with diagrams. He then realised that such networks describe associations and that causal reasoning needed something more.

Chapter 4 deals with confounding, a hidden factor that affects both the supposed cause and the effect. Ronald Fisher's randomised experiments solve this by assigning treatments by chance, but experiments are often impossible or unethical. Pearl's "do-operator" formalises the difference between seeing someone take a drug and making someone take it, and his "back-door criterion" tells you, from a diagram, which variables you need to adjust for.

Chapter 5 is the smoking debate of the 1950s and 60s. Fisher, himself a smoker, argued that a gene might cause both the urge to smoke and lung cancer. Jerome Cornfield showed that such a gene would have to be implausibly powerful, since heavy smokers had many times the cancer risk of non-smokers. The 1964 US Surgeon General's report finally declared smoking a cause of lung cancer, but without formal tools the argument took years longer than it needed to.

Chapter 6 uses causal diagrams to explain famous puzzles. In the Monty Hall problem, the host's choice of door carries information. In Simpson's paradox, a drug can seem to help both men and women separately yet harm the population as a whole, or the reverse; which answer is right depends on the causal story, not the numbers.

Chapter 7 shows how to estimate effects without experiments, including the "front-door" method and natural experiments. John Snow's 1854 investigation of cholera in London is the classic case. Snow compared households supplied by two water companies, one drawing from sewage-polluted parts of the Thames, and so separated the cause from everything else about people's lives.

Chapter 8 climbs to counterfactuals. Courts use "but-for" causation, and climate scientists now estimate how much more likely a heat wave was because of global warming. Pearl shows how to calculate the probability that one thing was necessary or sufficient for another.

Chapter 9 is about mediation: working out the mechanism by which a cause works. The story of scurvy shows why this matters. The British navy learned that citrus prevented it, but didn't know why, so it switched to limes with less vitamin C and, much later, polar expeditions suffered from the disease again.

Chapter 10 turns to artificial intelligence. Pearl argues that today's data-hungry systems are stuck on the bottom rung and that truly intelligent machines will need causal models, the ability to imagine and perhaps even something like free will.

## Key ideas

**The Ladder of Causation.** There are three levels of causal reasoning: seeing associations, predicting the effects of interventions, and imagining counterfactuals. Each needs more than the level below it.

**Data are not enough.** Raw data can't tell you what causes what. You need assumptions about how the world works, stated openly in a model.

**Causal diagrams.** Drawing arrows from causes to effects makes your assumptions visible and lets you work out what can be learned from the data.

**Confounders.** A hidden factor that influences both cause and effect can create a false link. Diagrams show which variables to control for, and which to leave alone.

**The do-operator.** Observing that people who take a drug recover is different from making people take it. The do-operator expresses that difference in mathematics.

**Counterfactuals.** Asking "what if things had been different?" is the highest form of causal reasoning, used in law, science and everyday regret.

**Mediation.** Knowing how a cause produces its effect, not just that it does, protects you from mistakes like the navy's switch to limes.

## If you read one chapter

Chapter 5, "The Smoke-Filled Debate," because the fight over smoking and cancer shows what was at stake when science had no language for causes.
