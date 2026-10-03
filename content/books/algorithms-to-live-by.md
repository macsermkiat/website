---
title: "Algorithms to Live By"
author: "Brian Christian and Tom Griffiths"
category: decisions
year: 2016
one_line: "A writer and a cognitive scientist show how problems computer scientists have solved, such as when to stop searching or how to schedule tasks, carry over to everyday human decisions."
sources:
  - https://algorithmstoliveby.com/
  - https://www.tosummarise.com/book-summary-algorithms-to-live-by-by-brian-christian-and-tom-griffiths/
  - https://grahammann.net/book-notes/algorithms-to-live-by-brian-christian
review: "check"
---

## In short

Computers constantly face the same kinds of problems we do: limited time, limited space, incomplete information and too many choices. Brian Christian and Tom Griffiths take eleven areas of computer science and show what each one teaches about everyday life, from house hunting to tidying a wardrobe. The recurring message is comforting: many hard problems have no perfect answer, and a good process is the best anyone, human or machine, can do.

## Summary

The first chapter is about optimal stopping. Say you are hiring and must accept or reject each candidate on the spot. The mathematically best strategy is to look at the first 37 percent of candidates without committing, then take the first one who is better than everyone you have seen. The same rule applies to flat hunting or, loosely, to dating: the operations researcher Michael Trick applied it to his love life and worked out that he should start committing at about age 26. The rule still fails most of the time. Its success rate is also about 37 percent, which is simply the best available.

Chapter 2 covers the trade-off between exploring new options and exploiting known good ones, known as the multi-armed bandit problem after a row of slot machines. The key is how much time you have left. Early on, try new restaurants; near the end of your stay in a city, go back to your favourite. This explains why children explore so wildly and why older people, as the psychologist Laura Carstensen found, deliberately narrow their social lives to the people who matter most.

Chapter 3 is about sorting. Computer scientists know that sorting gets costly quickly as a pile grows, which means that sometimes it is better not to sort at all. Searching an unsorted email inbox is often quicker than filing everything. Sports tournaments are sorting algorithms too, and some, like single elimination, are poor at identifying anyone but the winner.

Chapter 4, on caching, covers what to keep close at hand. Computers do well by evicting whatever was used least recently. A filing system invented by the Japanese economist Yukio Noguchi does the same, by always putting the file you just used at the front of the box. The authors conclude that the messy pile on your desk may be well organised. They also suggest that older people's slower recall may partly reflect having more stored in memory to search through.

Chapter 5, on scheduling, shows that there is no single best method; it depends on what you want. To minimise lateness, do the task with the earliest deadline first. To clear the most tasks, do the shortest first. The chapter warns about thrashing, when a system spends all its time switching between tasks and gets nothing done, and recommends batching interruptions, such as checking email at fixed times.

Chapter 6 brings in Bayes's rule for predicting from little data. When the astrophysicist J. Richard Gott visited the Berlin Wall in 1969, he reasoned that he was probably seeing it somewhere in the middle of its life, so it would likely last roughly as long again. The authors show how the right prediction depends on the kind of prior distribution: add a bit to the average for things like lifespans, multiply for things like film earnings.

Chapter 7 warns against overfitting, building a model or plan so detailed that it captures noise rather than signal. Charles Darwin's list of pros and cons about marriage stopped when he ran out of page, a form of early stopping the authors approve of. Sometimes thinking less leads to better decisions.

The next chapters give tools for hard problems. Relaxation means solving an easier version first, such as ignoring a constraint and then adding it back. Randomness helps too: sampling, the Monte Carlo methods that grew out of Stanislaw Ulam playing solitaire, and simulated annealing, which starts with random moves and gradually settles down.

Chapter 10, on networking, looks at how the internet handles overload. Exponential backoff, waiting longer after each failed attempt, is a sensible way to deal with an unreliable friend. Senders ease off sharply when data is lost and build speed back slowly.

Chapter 11 covers game theory. Individually rational choices can lead to bad collective outcomes, and the authors give unlimited vacation policies as an example where people take less time off. The fix is to change the rules of the game rather than the players.

The conclusion introduces computational kindness. When you ask a friend "What do you want to do tonight?" you hand them a hard problem. Proposing two options makes life easier for everyone.

## Key ideas

**The 37 percent rule.** When choosing from a sequence of options you can't return to, spend the first 37 percent looking, then take the next one that beats everything so far.

**Explore early, exploit late.** How much you should try new things depends on how much time remains to enjoy what you find.

**Don't sort what you won't search.** Organising has a cost. If you rarely need to find something, a messy pile can be the efficient choice.

**Least recently used.** Keep what you used most recently closest to hand and move the rest further away.

**Avoid thrashing.** Constant switching between tasks can eat all your time. Batch small tasks and interruptions.

**Bayesian predictions.** Combine small amounts of evidence with sensible expectations about how the thing you are predicting usually behaves.

**Overfitting.** Too much detail and too many factors can make a decision worse. Simpler rules often generalise better.

**Computational kindness.** Make things easy for others by limiting the choices and calculations you hand them.

## If you read one chapter

Chapter 1, "Optimal Stopping," because the 37 percent rule is simple, surprising and useful the next time you look for a flat or a hire.
