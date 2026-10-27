# What we need to do (plain-language guide)

Last updated: 2026-10-27. Final submission deadline: **2026-11-17**.

## 1. The goal in one paragraph

A **knowledge graph** (KG) is a big network of facts. The dots are things (a protein, a disease, a drug) and the lines between them are relationships ("this protein interacts with that protein", "this protein is linked to this disease"). Pharos, a database from the US National Institutes of Health, already has such a graph. It is useful but it has mistakes, missing links, and it is hard for non-experts to use.

Our job is to build an **AI agent** (a program that uses a language model, "an LLM", to decide what to do) that:
1. takes the Pharos graph,
2. adds useful facts from other public sources,
3. removes facts that look wrong,
4. lets ordinary people ask questions and see why each fact is in the graph.

The organizers then check whether our graph is better than plain Pharos.

## 2. How we are judged

| What | Weight | In plain words |
|---|---|---|
| Usability | 40% | Can a person who is not a graph expert run it and get value? Can they ask a question in normal language and get the relevant piece of the graph? |
| Accuracy and pruning | 30% | Did we remove wrong or irrelevant facts without throwing away correct ones? For Pharos facts, the organizers have a **gold set** (a list of known right/wrong answers) and will compare. For facts we add, human judges decide. |
| Explainability | 20% | For any fact, can we show where it came from and why it is there? |
| Standards | 10% | Do we use the standard scientific vocabularies (Biolink, OBO ontologies), with as few, and as specific, categories as possible? |

The organizers also test the graph by hiding some links and checking whether a machine-learning model (a **GNN**, a neural network that learns from graphs) can predict them. A better graph means better predictions. They said it would be helpful if the graph can be loaded with PyTorch Geometric (a common graph ML library).

## 3. What the final submission must contain

1. **A public GitHub repository** with an **MIT or Apache-2.0 license** (open-source track; prize is USD 5,000 in AWS credits).
2. **Two graphs**: the pruned graph and the whole graph. Every Pharos fact in the whole graph must carry a **keep or prune verdict**, a **confidence** and the **evidence** behind it. The organizers said: "We'll compare subgraphs to whole graph. Ideally send both."
3. **The agent code**, and a **simple way to run it** (ideally one command).
4. **A write-up** or the organizers' final template (they said one is coming), and any demo.

## 4. Where we are now

**Done**
- We downloaded the **full Pharos graph**: 397,636 things, 3,091,048 relationships, each with its source. The scores Pharos gives (for example how confident a protein-protein link is) are now stored on each link.
- We built a **fair test**: we hide some links, and make sure no hidden link, or its reverse, can leak into what the model sees. We also test with **hard negatives** (fake links chosen to look realistic), because easy fake links make any model look much better than it is.
- We measured the **baseline to beat** (a standard GNN on plain Pharos). Under the hard test, the scores (AUROC; 0.5 means guessing, 1.0 means perfect) are: protein-disease 0.525, protein-GO term 0.590, ligand-protein 0.626, protein-protein 0.686.
- We built the **agent harness**: the loop where an LLM chooses tools, the tools fetch real data, and every fact is checked and logged. It is tested with a pretend LLM and has one real tool (Pharos).
- We downloaded the **extra sources** (3.2 GB): GO, MONDO, UniProt, Monarch, Open Targets and OptimusKG, stored in `/scratch/hamza95/bio_kg_data/`.

**Not done yet**
- The agent has never run with a real LLM.
- Pruning, enrichment, explanations, the question-to-graph feature, and the easy-to-run package.

## 5. What we do next (in priority order)

### A. Pruning: a verdict for every Pharos fact (highest value, starts now)
- **What:** For each of the 3 million facts, decide **keep** or **prune**, give a **confidence** between 0 and 1, and write down **why**.
- **How, in two stages:**
  1. *Cheap rules first (no LLM).*
     - Protein-protein facts: Pharos gives a score. Low-scoring ones are suspects.
     - Protein-disease facts: only 15% have a score, and 88% are backed by a single database. These are the main suspects. Cross-check them against Open Targets, which gives independent evidence.
     - Ligand-protein and protein-GO facts: no scores exist. Check consistency against UniProt and GO instead.
  2. *LLM for the uncertain ones only.* There are too many facts to send everything to an LLM, so we send only the unclear cases, together with retrieved evidence.
- **Done when:** every fact has a verdict, confidence and reason, and a manual check of a sample shows the verdicts make sense.

### B. Run the agent with a real LLM
- **What:** Run the harness against an actual model on a small task, to prove the whole loop works.
- **Needs:** a model and API access. Options: Claude (API key), or open models on Vulcan (Alliance) or NRP. We asked the organizers which they recommend. Keep keys in your own terminal; never put them in the repo.
- **Done when:** the agent builds a small graph on its own and its log shows every step.

### C. Enrichment: add facts from other sources
- **What:** Add useful facts from Open Targets, GO and MONDO (hierarchies), UniProt (identifiers) and optionally Monarch and OptimusKG.
- **Rules:** Every new source passes the **leak check** (it must not carry the hidden test links). Keep a source only if it **improves the hard-negative score**. Test one source at a time.
- **Done when:** at least one source is added and we know, with numbers, whether it helped.

### D. Explanations: "why does A connect to B?"
- **What:** Given any two things, show the facts that connect them, where each came from, the evidence and the verdict.
- **Done when:** a person can ask about any link and get a readable answer.

### E. Standards
- **What:** Map our things and relationships to Biolink categories and OBO identifiers (for example a protein-coding gene is `SO:0001217`), use specific classes rather than generic ones, and keep the number of classes small. Check with the `kgx validate` tool.
- **Done when:** the validator passes and we can list the classes we use.

### F. Usability
- **What:** A one-command way to run everything, a clear README, a short demo, and the **question-to-graph** feature (a user asks in plain language and gets the relevant part of the graph).
- **Why it matters:** this is 40% of the score, the biggest single part.
- **Done when:** someone who has never seen the project can run it from the README in a few minutes.

### G. Outputs
- **What:** Export the pruned and whole graphs in formats the organizers can use: our Parquet files, a PyTorch Geometric file, and the KGX format.

### H. Admin
- Add the **license** (MIT or Apache-2.0; team to choose).
- Send the **progress report** (due Oct 27).
- Make the repo **public** before submitting, after checking it contains no passwords or keys.
- Fill in the organizers' final template when it arrives.
- Ask the organizers the open questions in section 8.

## 6. Calendar

| Dates | Focus |
|---|---|
| Now to Nov 3 | Pruning rules (A), license, first real-LLM run (B) |
| Nov 4 to Nov 10 | One enrichment source with leak check and measurement (C), explanations (D), exports (G) |
| Nov 11 to Nov 17 | Question-to-graph and one-command run (F), final measurements, README and demo, **submit by Nov 17** |

## 7. Rules we follow

1. **No cheating on the test.** A hidden link, or its reverse, must never reach the model or the agent. Every new source goes through the leak check.
2. **Trust the hard test.** Easy fake links inflate scores. Report the hard-negative numbers and use several random seeds.
3. **Every fact has a source.** The LLM may propose or judge, but a fact must come from a real source with evidence. The LLM never invents facts from memory.
4. **Everything is logged.** Each fact stores its source, evidence, confidence, method and time.
5. **Use the cluster properly.** Heavy work goes through Slurm jobs (account `def-nahee_cpu`), not the login node. Run `. env.sh` first.
6. **Secrets stay out of the repo.** No API keys, tokens or passwords.
7. **Respect data licenses.** Do not commit downloaded data. Some sources (for example OptimusKG) carry non-commercial terms from their origins.

## 8. Open questions and decisions

**Decisions for the team**
- Which license: MIT or Apache-2.0?
- Which LLM and how will we access it (Claude API, or Vulcan/NRP open models)?
- Who works on which part (A to H above)?

**Questions for the organizers** (some already asked)
- Which LLM do they recommend, and are credits available for it?
- Does the gold set cover all of Pharos, or only some diseases? Does it contain injected errors?
- Do all teams use the same baseline Pharos graph?
- Which links are hidden for the link-prediction test, and who runs the model?
- What exactly goes in the final submission?

## 9. Glossary

- **Knowledge graph (KG):** a network of things and the relationships between them.
- **Node / edge:** a thing / a relationship (a dot / a line).
- **Pharos:** the NIH database of drug targets we start from.
- **Agent:** a program where an LLM decides which tools to call and what to do with the results.
- **LLM:** a large language model, such as Claude.
- **Pruning:** removing facts that look wrong or irrelevant.
- **Evidence / provenance:** where a fact came from and why we believe it.
- **GNN:** graph neural network, a model that learns from graph structure.
- **Link prediction:** guessing which links are missing, by hiding some and seeing if the model can find them.
- **AUROC:** a score of how well the model separates real links from fake ones. 0.5 is guessing, 1.0 is perfect.
- **Hard negatives:** fake links chosen to look realistic, which makes the test fair.
- **Leakage:** accidentally letting the test answers into the training data. It makes results look better than they are.
- **Biolink / OBO / ontology:** standard vocabularies and identifiers used across biomedical databases.
- **Slurm:** the cluster's job system. Heavy work runs as jobs, not on the login node.
