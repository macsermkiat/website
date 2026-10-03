---
title: "The Pragmatic Programmer"
author: "David Thomas and Andrew Hunt"
category: craft
year: 1999
one_line: "Two experienced developers' collection of practical habits and principles for writing software that is easy to change and for taking charge of your own career."
sources:
  - https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/
  - https://pragprog.com/tips/
  - https://changelog.com/podcast/352
  - https://www.ahalbert.com/technology/2023/12/19/the_pragmatic_programmer.html
  - https://github.com/HugoMatilla/The-Pragmatic-Programmer
  - https://sgeb.io/bookshelf/the-pragmatic-programmer/
review: "check"
---

## In short

Dave Thomas and Andy Hunt wrote this book in 1999 after years of working as consultants on other companies' software projects, and rewrote most of it for the 20th anniversary edition in 2019. It is a collection of short, self-contained topics and 100 numbered tips about how a good programmer thinks and works. The common thread is that you are responsible for your code and your career, and that good design is whatever makes the code easier to change later.

## Summary

Chapter 1 opens with attitude rather than technique. In "It's Your Life" the authors remind readers that if their job or their tools are bad, they can change them. "The Cat Ate My Source Code" asks you to own your mistakes: when something goes wrong, come to your boss with options for fixing it, not excuses. "Software Entropy" borrows the broken windows idea from urban research. One neglected hack or ugly module signals that nobody cares, and the rot spreads, so fix small problems when you see them. "Stone Soup and Boiled Frogs" uses two fables. Like the soldiers who got villagers to add ingredients to a pot of "stone soup," you can start something small and let people join a visible success. Like the frog in slowly heating water, you can miss a project drifting into trouble unless you keep watching the big picture. The chapter ends with treating your knowledge as an investment portfolio (learn a new language every year, read regularly, diversify) and with the reminder that communication is part of the job.

Chapter 2 sets out the design principles the rest of the book leans on. The first is ETC, "Easier to Change": when choosing between two designs, pick the one that will be easier to change. DRY (Don't Repeat Yourself) is about knowledge, not just copied code; every fact about the system should live in one place. Orthogonality means parts that don't affect each other, so a change in one doesn't ripple through the others. Reversibility warns against decisions you can't undo, since requirements, vendors and platforms all shift. Tracer bullets are a thin, working path through the whole system, from interface to database, that you build early and then flesh out; they differ from prototypes, which you write to explore one risky question and then throw away. The chapter closes with how to estimate: understand what's being asked, build a rough model, and give answers in units that show how precise you really are.

Chapter 3 covers everyday tools. Keep knowledge in plain text, get fluent with the shell and one editor, put everything in version control, and keep an engineering daybook. The debugging advice is famous: fix the problem, not the blame; explain the bug out loud to someone, even a rubber duck; and assume the fault is in your code before blaming the compiler or the operating system ("select isn't broken").

Chapter 4, "Pragmatic Paranoia," starts from the premise that nobody writes perfect software, including you. Design by contract states what a routine expects and what it promises. Crash early, because a dead program does less damage than one limping on with bad data. Use assertions for things that "can't happen," and take small steps so you never outrun your headlights.

Chapters 5 and 6 are about flexibility and concurrency. The authors warn against "train wrecks" of chained method calls, against deep inheritance hierarchies (the "inheritance tax"), and against shared mutable state, and they suggest thinking of programs as pipelines that transform data. They also recommend keeping configuration outside the code.

Chapter 7 turns to the act of coding. Listen to the uneasy feeling that something is wrong. Don't program by coincidence, meaning code that works for reasons you don't understand. Refactor early and often, write tests as a way of thinking about design, and pick names with care. Security gets its own topic, which the first edition barely touched.

The last two chapters step up to projects and teams. Requirements rarely sit on the surface waiting to be collected; you discover them through feedback, by showing people working software. Agility is a habit of taking small steps and adjusting, not a process you buy. "Coconuts Don't Cut It" mocks cargo-cult imitation of other companies' practices. The book ends by asking you to delight users and to sign your work with pride.

## Key ideas

**Take responsibility.** Own your mistakes and your career. When something breaks, offer ways to fix it instead of reasons it isn't your fault.

**Easier to Change (ETC).** Good design is design that is easy to change. Most of the other principles in the book are ways of achieving that.

**DRY.** Each piece of knowledge in a system should have one authoritative home. When the same knowledge lives in two places, in code, comments or data, one copy eventually gets updated and the other doesn't.

**Broken windows.** Small signs of neglect in a codebase invite more neglect. Fixing or at least boarding up problems early keeps quality from sliding.

**Tracer bullets.** Build a thin, end-to-end version of the system early so you can see whether the pieces connect and get feedback, then fill it in.

**Crash early.** When something impossible happens, stop the program rather than let it carry on with corrupted state. Contracts and assertions make those failures loud and early.

**Don't program by coincidence.** Know why your code works. Code that passes by luck will fail by luck later.

**Your knowledge portfolio.** Skills lose value as technology moves, so invest regularly and widely: new languages, books, and fields outside computing.

## If you read one chapter

Chapter 2, "A Pragmatic Approach," because ETC, DRY, orthogonality and tracer bullets are the ideas the whole book builds on.
