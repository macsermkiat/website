---
title: "Clean Code"
author: "Robert C. Martin"
category: craft
year: 2008
one_line: "A handbook on writing code that other people can read and change, built from small rules about names, functions, comments, tests and classes, plus long worked examples of cleaning up messy code."
sources:
  - https://www.oreilly.com/library/view/clean-code-a/9780136083238
  - https://catdir.loc.gov/catdir/toc/ecip0820/2008024750.html
  - https://ptgmedia.pearsoncmg.com/images/9780132350884/samplepages/9780132350884.pdf
  - https://github.com/jbarroso/clean-code
  - https://www.informit.com/store/clean-code-a-handbook-of-agile-software-craftsmanship-9780135398579
  - https://github.com/johnousterhout/aposd-vs-clean-code
review: "check"
---

## In short

Robert C. Martin, known to programmers as "Uncle Bob," argues that messy code slowly strangles software teams and that keeping code clean is a professional duty, not a luxury. The book gives concrete rules for names, functions, comments, formatting, error handling, tests and classes, then shows them at work on real Java code. It ends with a long checklist of "smells" that tell you something needs fixing. A second edition came out in 2025; this summary follows the 2008 original.

## Summary

The introduction shows a cartoon of two code reviews, one calm and one full of people swearing, and says the only honest measure of code quality is "WTFs per minute." Martin says learning the craft takes two things: knowing the principles, and grinding them in through practice. So the book comes in three parts: principles in the first thirteen chapters, case studies next, and a catalogue of heuristics at the end.

Chapter 1 makes the case for caring. Martin describes a company that rushed a product out with sloppy code and eventually went under because nobody could change it. In his account, every mess follows the same arc. A team starts fast, slows as the tangle grows, and management adds people who don't know the design and make it worse. Finally someone proposes a total rewrite, the "Grand Redesign in the Sky," which takes years and ends up just as messy. His answer is attitude: programmers should defend the code the way a doctor refuses a patient's request to skip hand-washing. The chapter collects definitions of clean code from well-known programmers. Bjarne Stroustrup wants it elegant and efficient, Grady Booch says it should read like good prose, and Michael Feathers says it looks as if someone cared. Martin adds that we read code far more than we write it, by a ratio of more than ten to one, so readable code is also faster to write. He closes with the Boy Scout Rule: leave the code a little cleaner than you found it.

The next chapters get specific. Names should reveal intent (`elapsedTimeInDays`, not `d`), be pronounceable and searchable, and not lie; don't call something `accountList` unless it really is a list. Functions should be small, do one thing, and stay at one level of abstraction. Fewer arguments is better, flag arguments are a sign the function does two things, and a function should either do something or answer something, not both. Comments are mostly a failure to express yourself in code. Martin keeps a place for legal notices, explanations of intent and warnings, but wants commented-out code and changelog comments deleted. Formatting should follow the newspaper model, with the headline and big picture at the top of a file and the details lower down.

Chapter 6 separates objects, which hide data behind behaviour, from data structures, which expose data and have no behaviour. It introduces the Law of Demeter: a method should talk to its immediate collaborators, not reach through chains like `a.getB().getC().doThing()`. Error handling should use exceptions rather than return codes, never return or pass null, and keep the error logic apart from the main logic. Code that depends on third-party libraries should be wrapped at the boundary, with small "learning tests" to check how the library behaves.

Chapter 9 covers testing. Martin lays out the three laws of test-driven development: write a failing test before any production code, write no more test than it takes to fail, and write no more code than it takes to pass. Test code deserves the same care as production code, and good tests are fast, independent, repeatable, self-validating and timely (F.I.R.S.T.). Classes should be small in the sense of having one reason to change, the Single Responsibility Principle. Chapters on systems, emergent design and concurrency round out the first part. Kent Beck's four rules of simple design appear here: runs all the tests, contains no duplication, expresses intent, and has as few classes and methods as possible.

The case studies are the hardest part of the book to read. Martin refactors a command-line argument parser step by step, then cleans up part of JUnit, then works through the SerialDate class from an open-source Java library. You watch each small change and the test run that confirms it. Chapter 17 then lists dozens of numbered smells and heuristics, from obsolete comments and flag arguments to magic numbers and feature envy.

The advice is firm and sometimes dogmatic, and later writers such as John Ousterhout have argued that very short functions can make code harder to follow. The core message holds either way: code is written for human readers, and it stays healthy only if you keep tidying it.

## Key ideas

**Code is read far more than it is written.** Most programming time goes into reading existing code, so readability is the thing to optimise.

**The Boy Scout Rule.** Leave every file a bit cleaner than you found it. Small, steady improvements stop the rot without a big rewrite.

**Intention-revealing names.** A good name tells you why a thing exists and how it's used, so you don't need a comment to explain it.

**Small functions that do one thing.** Each function should do a single job at a single level of abstraction, with as few arguments as possible.

**Comments as a last resort.** Try to make the code explain itself first. Comments go stale; code that runs cannot.

**Law of Demeter.** An object should only talk to its close collaborators. Long chains of calls couple you to the internals of distant objects.

**Clean tests.** Tests are part of the codebase and need the same care. Write them first, keep them fast and independent, and test one concept each.

**Single Responsibility Principle.** A class should have one reason to change. When a class starts serving several masters, split it.

## If you read one chapter

Chapter 3, "Functions," because its rules about size, arguments and doing one thing are the heart of the book and change how you write code the next day.
